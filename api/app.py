"""
FastAPI Application
Main entry point for the backend API
"""

from copy import deepcopy
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
import logging
from pathlib import Path
import uuid
from datetime import datetime, timedelta

# Import project modules
import sys
sys.path.append(str(Path(__file__).parent.parent))

from agents.orchestrator import Orchestrator
from storage.db import get_database
from storage.models import Document, Section, Concept, Card, Review
from configs import get_config
from nlp.parser import DocumentParser

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("api.app")
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Initialize FastAPI app
app = FastAPI(
    title="Multi-Agent Learning System",
    description="智能学习卡片生成系统",
    version="0.1.0"
)

# Load configuration
config = get_config()
config.ensure_directories()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.get("api.cors_origins", ["*"]),
    allow_origin_regex=config.get(
        "api.cors_origin_regex",
        r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize global components
try:
    db = get_database(config.get("database.sqlite_path"))
    logger.info("Database initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize database: {e}")
    raise

orchestrator = None

try:
    parser = DocumentParser()
    logger.info("DocumentParser initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize parser: {e}")
    raise


# Pydantic models for request/response
class IngestRequest(BaseModel):
    """Request model for document ingestion"""
    url: Optional[str] = None
    title: Optional[str] = None


class IngestResponse(BaseModel):
    """Response model for document ingestion"""
    doc_id: str
    title: str
    status: str
    message: str


class BuildRequest(BaseModel):
    """Request model for pipeline build"""
    enable_kg: bool = True
    enable_consistency_check: bool = True
    target_card_count: int = Field(default=12, ge=4, le=60)
    build_strategy: Literal["balanced", "memory", "challenge"] = "balanced"
    card_types: List[Literal["knowledge", "cloze", "mcq", "short"]] = Field(
        default_factory=lambda: ["knowledge", "cloze", "mcq", "short"]
    )
    difficulty: Literal["mixed", "L", "M", "H"] = "mixed"


class BuildResponse(BaseModel):
    """Response model for pipeline build"""
    doc_id: str
    status: str
    summary: dict
    message: str


class AnswerRequest(BaseModel):
    """Request model for answer submission"""
    user_id: str
    card_id: str
    response: str
    latency_ms: int = 0


class AnswerResponse(BaseModel):
    """Response model for answer evaluation"""
    status: str
    evaluation: dict
    schedule: dict


class ReviewPlanResponse(BaseModel):
    """Response model for review plan"""
    user_id: str
    due_today: int
    overdue: int
    cards: List[dict]


def create_orchestrator_config(build_request: Optional[BuildRequest] = None) -> dict:
    """Create orchestrator config, optionally overriding quiz/build settings."""
    request = build_request or BuildRequest()
    orchestrator_config = {
        "content": deepcopy(config.get("agents.content", {})),
        "concept": deepcopy(config.get("agents.concept", {})),
        "quiz": deepcopy(config.get("agents.quiz", {})),
        "eval": deepcopy(config.get("agents.eval", {})),
        "schedule": deepcopy(config.get("agents.schedule", {})),
        "enable_kg": request.enable_kg,
        "enable_consistency_check": request.enable_consistency_check,
        "max_retries": config.get("orchestrator.max_retries", 3),
    }

    quiz_config = orchestrator_config["quiz"]
    requested_types = request.card_types or ["knowledge", "cloze", "mcq", "short"]
    quiz_config["card_types"] = requested_types
    quiz_config["target_card_count"] = request.target_card_count
    quiz_config["build_strategy"] = request.build_strategy
    quiz_config["difficulty_mode"] = request.difficulty

    if request.target_card_count <= 10:
        quiz_config["cards_per_concept"] = 1
    elif request.target_card_count <= 24:
        quiz_config["cards_per_concept"] = 2
    else:
        quiz_config["cards_per_concept"] = 3

    return orchestrator_config


def build_card_summary(cards_data: List[dict], build_request: BuildRequest) -> dict:
    """Build a frontend-friendly card summary payload."""
    by_difficulty = {"L": 0, "M": 0, "H": 0}
    for card in cards_data:
        difficulty = card.get("difficulty")
        if difficulty in by_difficulty:
            by_difficulty[difficulty] += 1

    return {
        "by_difficulty": by_difficulty,
        "build_options": build_request.model_dump(),
    }


try:
    orchestrator = Orchestrator(create_orchestrator_config())
    logger.info("Orchestrator initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize orchestrator: {e}")
    import traceback
    traceback.print_exc()
    raise


# API Endpoints

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Multi-Agent Learning System API",
        "version": "0.1.0",
        "status": "running"
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/debug/{doc_id}")
async def debug_document(doc_id: str):
    """Debug endpoint to check document status"""
    try:
        doc = db.get_document(doc_id)
        if not doc:
            return {"error": "Document not found", "doc_id": doc_id}
        
        sections = db.get_sections(doc_id)
        concepts = db.get_concepts(doc_id)
        cards = db.get_cards(doc_id=doc_id)
        
        return {
            "doc_id": doc_id,
            "document": doc.dict() if doc else None,
            "sections_count": len(sections),
            "concepts_count": len(concepts),
            "cards_count": len(cards),
            "source": doc.source if doc else None,
            "source_type": doc.source_type if doc else None
        }
    except Exception as e:
        import traceback
        return {
            "error": str(e),
            "traceback": traceback.format_exc()
        }


@app.post("/ingest", response_model=IngestResponse)
async def ingest_document(
    background_tasks: BackgroundTasks,
    file: Optional[UploadFile] = File(None),
    request: Optional[IngestRequest] = None
):
    """
    Ingest a document (upload file or provide URL)
    
    Returns document ID for further processing
    """
    try:
        doc_id = str(uuid.uuid4())
        
        if file:
            # Handle file upload
            uploads_dir = Path(config.get("paths.uploads_dir", "data/uploads"))
            uploads_dir.mkdir(parents=True, exist_ok=True)
            
            file_path = uploads_dir / f"{doc_id}_{file.filename}"
            
            # Save uploaded file
            with open(file_path, "wb") as f:
                content = await file.read()
                f.write(content)
            
            title = file.filename
            source = str(file_path)
            
            # Detect source type from the saved file path so backend parsing
            # and upload ingestion always use the same extension mapping.
            source_type = parser.detect_type(file_path)
            
            logger.info(f"File uploaded: {file_path}, type: {source_type}")
            
        elif request and request.url:
            # Handle URL (TODO: implement URL fetching)
            title = request.title or request.url
            source = request.url
            logger.info(f"URL provided: {source}")
            
            return JSONResponse(
                status_code=501,
                content={"error": "URL ingestion not yet implemented"}
            )
        else:
            raise HTTPException(status_code=400, detail="No file or URL provided")
        
        # Create document record
        doc = Document(
            doc_id=doc_id,
            title=title,
            source=source,
            source_type=source_type,
            lang="zh",
            created_at=datetime.now().isoformat()
        )
        
        # Save to database
        if not db.insert_document(doc):
            raise HTTPException(status_code=500, detail="Failed to save document")
        
        return IngestResponse(
            doc_id=doc_id,
            title=title,
            status="success",
            message=f"Document ingested successfully. Use /build/{doc_id} to process."
        )
        
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/build/{doc_id}", response_model=BuildResponse)
async def build_pipeline(
    doc_id: str,
    request: Optional[BuildRequest] = None,
    background_tasks: BackgroundTasks = None,
):
    """
    Trigger the full pipeline for a document
    Content -> Concept -> Quiz generation
    """
    try:
        # Get document from database
        doc = db.get_document(doc_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        
        build_request = request or BuildRequest()
        if not build_request.card_types:
            raise HTTPException(status_code=400, detail="At least one card type must be selected")
        logger.info(
            "Starting pipeline for doc_id=%s, source=%s, type=%s, options=%s",
            doc_id,
            doc.source,
            doc.source_type,
            build_request.model_dump(),
        )
        
        # Check if source file exists
        from pathlib import Path
        source_path = Path(doc.source)
        if not source_path.exists():
            error_msg = f"Source file not found: {doc.source}"
            logger.error(error_msg)
            raise HTTPException(status_code=404, detail=error_msg)
        
        logger.info(f"Source file exists: {doc.source} ({source_path.stat().st_size} bytes)")
        
        # Parse document
        try:
            parsed = parser.parse(doc.source, doc.source_type)
            text_length = len(parsed.get('text', ''))
            logger.info(f"Document parsed successfully, text length: {text_length}")
            
            if text_length == 0:
                logger.warning("Parsed text is empty!")
                raise HTTPException(status_code=400, detail="Parsed document is empty")
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to parse document: {e}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Document parsing failed: {str(e)}")
        
        # Prepare input for orchestrator
        pipeline_input = {
            "doc_id": doc_id,
            "content": parsed["text"],
            "source": doc.source_type,
            "language": doc.lang,
            "build_options": build_request.model_dump(),
        }
        
        # Run pipeline
        try:
            build_orchestrator = Orchestrator(create_orchestrator_config(build_request))
            result = build_orchestrator.run_full_pipeline(pipeline_input)
            logger.info(f"Pipeline execution completed with status: {result.get('status')}")
        except Exception as e:
            logger.error(f"Pipeline execution failed: {e}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Pipeline execution failed: {str(e)}")
        
        if result.get("status") != "success":
            raise HTTPException(status_code=500, detail="Pipeline execution failed")
        
        # Save results to database
        try:
            sections_data = result["stages"]["content"]["sections"]
            sections = [Section(**s) for s in sections_data]
            
            concepts = []
            if "concepts" in result["stages"] and not result["stages"]["concepts"].get("skipped"):
                concepts_data = result["stages"]["concepts"]["concepts"]
                concepts = [Concept(**c) for c in concepts_data]
            
            cards_data = result["stages"]["quiz"]["cards"]
            cards = [Card(**c) for c in cards_data]

            if not db.replace_generated_content(doc_id, sections, concepts, cards):
                raise HTTPException(status_code=500, detail="Failed to replace generated content")

            db.sync_learning_progress_totals(doc_id, len(cards))
            logger.info(
                "Saved generated content for doc_id=%s (%s sections, %s concepts, %s cards)",
                doc_id,
                len(sections),
                len(concepts),
                len(cards),
            )
        except Exception as e:
            logger.error(f"Failed to save results to database: {e}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Database save failed: {str(e)}")
        
        logger.info(f"Pipeline completed successfully for doc_id={doc_id}")
        summary = {
            **result["summary"],
            "by_type": result["stages"]["quiz"].get("metadata", {}).get("by_type", {}),
            **build_card_summary(cards_data, build_request),
        }
        
        return BuildResponse(
            doc_id=doc_id,
            status="success",
            summary=summary,
            message="Pipeline completed successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Build failed with unexpected error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Build failed: {str(e)}")


@app.get("/cards")
async def get_cards(doc_id: Optional[str] = None, limit: int = 20, offset: int = 0):
    """
    Get quiz cards
    Optionally filter by document ID
    """
    try:
        cards = db.get_cards(doc_id=doc_id, limit=limit, offset=offset)
        total = db.count_cards(doc_id=doc_id)
        
        return {
            "total": total,
            "cards": [card.dict() for card in cards]
        }
        
    except Exception as e:
        logger.error(f"Failed to get cards: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/answer", response_model=AnswerResponse)
async def submit_answer(request: AnswerRequest):
    """
    Submit an answer for evaluation
    Returns evaluation result and next review schedule
    """
    try:
        # Get card
        card = db.get_card(request.card_id)
        if not card:
            raise HTTPException(status_code=404, detail="Card not found")
        
        # Get user's history for this card
        reviews = db.get_reviews(request.user_id, request.card_id)
        
        # Prepare history data
        history = {}
        if reviews:
            last_review = reviews[0]  # Most recent
            history = {
                "ef": last_review.ef,
                "interval_days": last_review.interval_days,
                "repetitions": last_review.repetitions
            }
        
        # Prepare evaluation input
        eval_input = {
            "user_id": request.user_id,
            "card_id": request.card_id,
            "card": card.dict(),
            "response": request.response,
            "latency_ms": request.latency_ms,
            "history": history
        }
        
        # Run evaluation and scheduling
        result = orchestrator.run_answer_evaluation(eval_input)
        
        if result["status"] != "success":
            raise HTTPException(status_code=500, detail="Evaluation failed")
        
        # Save review record
        review = Review(
            id=str(uuid.uuid4()),
            user_id=request.user_id,
            card_id=request.card_id,
            ts=datetime.now().isoformat(),
            response=request.response,
            score=result["evaluation"]["score"],
            is_correct=result["evaluation"]["is_correct"],
            error_type=result["evaluation"].get("error_type"),
            latency_ms=request.latency_ms,
            next_due=result["schedule"]["next_due"],
            ef=result["schedule"]["ef"],
            interval_days=result["schedule"]["interval_days"],
            repetitions=result["schedule"]["repetitions"]
        )
        
        db.insert_review(review)
        
        return AnswerResponse(
            status="success",
            evaluation=result["evaluation"],
            schedule=result["schedule"]
        )
        
    except Exception as e:
        logger.error(f"Answer submission failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/review_plan", response_model=ReviewPlanResponse)
async def get_review_plan(user_id: str):
    """
    Get today's review plan for a user
    Returns cards that are due for review
    """
    try:
        due_records = db.get_due_review_records(user_id)
        due_card_ids = [record["card_id"] for record in due_records]
        
        # Get full card data
        cards = []
        for card_id in due_card_ids[:50]:  # Limit to 50 cards
            card = db.get_card(card_id)
            if card:
                cards.append(card.dict())
        
        overdue_cutoff = datetime.now() - timedelta(days=1)
        overdue = sum(
            1
            for record in due_records
            if datetime.fromisoformat(record["next_due"]) < overdue_cutoff
        )
        
        return ReviewPlanResponse(
            user_id=user_id,
            due_today=len(due_card_ids),
            overdue=overdue,
            cards=cards
        )
        
    except Exception as e:
        logger.error(f"Failed to get review plan: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/report")
async def get_report(user_id: str):
    """
    Get learning report for a user
    Shows statistics, error distribution, mastery levels
    """
    try:
        # Get all reviews for user
        reviews = db.get_reviews(user_id)
        
        if not reviews:
            return {
                "user_id": user_id,
                "total_reviews": 0,
                "message": "No review data available"
            }
        
        # Calculate statistics
        total_reviews = len(reviews)
        correct_count = sum(1 for r in reviews if r.is_correct)
        accuracy = correct_count / total_reviews if total_reviews > 0 else 0
        
        # Error type distribution
        error_types = {}
        for review in reviews:
            if review.error_type:
                error_types[review.error_type] = error_types.get(review.error_type, 0) + 1
        
        # Average latency
        avg_latency = sum(r.latency_ms for r in reviews) / total_reviews
        
        return {
            "user_id": user_id,
            "total_reviews": total_reviews,
            "accuracy": accuracy,
            "correct_count": correct_count,
            "incorrect_count": total_reviews - correct_count,
            "avg_latency_ms": avg_latency,
            "error_distribution": error_types
        }
        
    except Exception as e:
        logger.error(f"Failed to generate report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/documents")
async def list_documents():
    """List all documents"""
    try:
        return db.list_documents()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/progress/save")
async def save_progress(request: dict):
    """保存学习进度"""
    try:
        user_id = request.get('user_id')
        doc_id = request.get('doc_id')
        current_idx = request.get('current_card_idx', 0)
        total_cards = request.get('total_cards', 0)
        
        if not user_id or not doc_id:
            raise HTTPException(status_code=400, detail="Missing user_id or doc_id")
        
        success = db.save_learning_progress(user_id, doc_id, current_idx, total_cards)
        
        if success:
            return {"status": "success", "message": "Progress saved"}
        else:
            raise HTTPException(status_code=500, detail="Failed to save progress")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Save progress failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/progress/{user_id}")
async def get_progress(user_id: str, doc_id: str = None):
    """获取学习进度"""
    try:
        progress = db.get_learning_progress(user_id, doc_id)
        
        if progress:
            return progress
        else:
            return {"message": "No progress found"}
            
    except Exception as e:
        logger.error(f"Get progress failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/progress/{user_id}/all")
async def get_all_progress(user_id: str):
    """获取用户所有学习进度"""
    try:
        progress_list = db.get_all_progress(user_id)
        
        return {
            "total": len(progress_list),
            "progress": progress_list
        }
            
    except Exception as e:
        logger.error(f"Get all progress failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    
    host = config.get("api.host", "0.0.0.0")
    port = config.get("api.port", 8000)
    reload_enabled = config.get("api.reload", True)
    reload_dirs = [
        str((PROJECT_ROOT / folder).resolve())
        for folder in ["api", "agents", "configs", "nlp", "storage"]
        if (PROJECT_ROOT / folder).exists()
    ]
    reload_excludes = [
        str((PROJECT_ROOT / folder).resolve())
        for folder in ["data", "logs", "frontend/node_modules", "frontend/dist"]
        if (PROJECT_ROOT / folder).exists()
    ]
    
    logger.info(f"Starting API server on {host}:{port}")
    
    uvicorn.run(
        "api.app:app",
        host=host,
        port=port,
        reload=reload_enabled,
        reload_dirs=reload_dirs if reload_enabled else None,
        reload_excludes=reload_excludes if reload_enabled else None,
    )

