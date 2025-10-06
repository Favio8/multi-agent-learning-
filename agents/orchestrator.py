"""
Orchestrator - Coordinates all agents and manages the workflow
"""

from typing import Dict, Any, Optional, List
from .base_agent import BaseAgent
from .content_agent import ContentAgent
from .concept_agent import ConceptAgent
from .quiz_agent import QuizAgent
from .eval_agent import EvalAgent
from .schedule_agent import ScheduleAgent
import json
from datetime import datetime


class Orchestrator(BaseAgent):
    """
    Orchestrator coordinates all agents:
    - Pipeline management
    - Error handling and retry logic
    - Audit logging
    - A/B testing switches
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(agent_id="Orchestrator", config=config)
        
        # Initialize all agents
        self.content_agent = ContentAgent(config.get("content", {}) if config else {})
        self.concept_agent = ConceptAgent(config.get("concept", {}) if config else {})
        self.quiz_agent = QuizAgent(config.get("quiz", {}) if config else {})
        self.eval_agent = EvalAgent(config.get("eval", {}) if config else {})
        self.schedule_agent = ScheduleAgent(config.get("schedule", {}) if config else {})
        
        # Configuration flags
        self.enable_kg = config.get("enable_kg", True) if config else True
        self.enable_consistency_check = config.get("enable_consistency_check", True) if config else True
        self.max_retries = config.get("max_retries", 3) if config else 3
        
        # Audit trail
        self.audit_trail = []
        
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main orchestration process - not typically used directly
        Use specific workflows instead
        """
        workflow = input_data.get("workflow", "full_pipeline")
        
        if workflow == "full_pipeline":
            return self.run_full_pipeline(input_data)
        elif workflow == "answer_evaluation":
            return self.run_answer_evaluation(input_data)
        else:
            raise ValueError(f"Unknown workflow: {workflow}")
    
    def run_full_pipeline(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run the full document processing pipeline:
        Document -> Content -> Concept -> Quiz
        
        Args:
            input_data: {
                "doc_id": str,
                "file_path" or "content": str,
                "source": str
            }
            
        Returns:
            Complete pipeline results
        """
        self.logger.info(f"Starting full pipeline for doc_id={input_data.get('doc_id')}")
        
        doc_id = input_data["doc_id"]
        results = {"doc_id": doc_id, "stages": {}}
        
        try:
            # Stage 1: Content extraction and segmentation
            self.logger.info("Stage 1: Content extraction")
            content_result = self._run_with_retry(
                self.content_agent.process,
                input_data,
                "ContentAgent"
            )
            results["stages"]["content"] = content_result
            self._log_audit("content_extraction", input_data, content_result)
            
            # Stage 2: Concept extraction (if enabled)
            concepts_result = None
            if self.enable_kg:
                self.logger.info("Stage 2: Concept extraction")
                concept_input = {
                    "doc_id": doc_id,
                    "sections": content_result["sections"],
                    "language": content_result.get("language", "zh")
                }
                concepts_result = self._run_with_retry(
                    self.concept_agent.process,
                    concept_input,
                    "ConceptAgent"
                )
                results["stages"]["concepts"] = concepts_result
                self._log_audit("concept_extraction", concept_input, concepts_result)
            else:
                self.logger.info("Stage 2: Skipping concept extraction (disabled)")
                concepts_result = {"doc_id": doc_id, "concepts": [], "relations": []}
                results["stages"]["concepts"] = {"skipped": True}
            
            # Stage 3: Quiz card generation
            self.logger.info("Stage 3: Quiz card generation")
            quiz_input = {
                "doc_id": doc_id,
                "concepts": concepts_result.get("concepts", []),
                "relations": concepts_result.get("relations", []),
                "sections": content_result["sections"]
            }
            quiz_result = self._run_with_retry(
                self.quiz_agent.process,
                quiz_input,
                "QuizAgent"
            )
            results["stages"]["quiz"] = quiz_result
            self._log_audit("quiz_generation", quiz_input, quiz_result)
            
            # Summary
            results["summary"] = {
                "total_sections": len(content_result.get("sections", [])),
                "total_concepts": len(concepts_result.get("concepts", [])),
                "total_cards": len(quiz_result.get("cards", [])),
                "timestamp": datetime.now().isoformat()
            }
            
            self.logger.info(f"Pipeline completed successfully: {results['summary']}")
            
        except Exception as e:
            self.logger.error(f"Pipeline failed: {str(e)}")
            results["error"] = str(e)
            results["status"] = "failed"
            raise
        
        results["status"] = "success"
        return results
    
    def run_answer_evaluation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run answer evaluation and scheduling workflow
        
        Args:
            input_data: {
                "user_id": str,
                "card_id": str,
                "card": {...},
                "response": str,
                "history": {...}
            }
            
        Returns:
            Evaluation and scheduling results
        """
        self.logger.info(f"Evaluating answer for user={input_data.get('user_id')}, card={input_data.get('card_id')}")
        
        results = {}
        
        try:
            # Stage 1: Evaluate answer
            eval_result = self._run_with_retry(
                self.eval_agent.process,
                input_data,
                "EvalAgent"
            )
            results["evaluation"] = eval_result
            self._log_audit("answer_evaluation", input_data, eval_result)
            
            # Stage 2: Schedule next review
            schedule_input = {
                "card_id": input_data["card_id"],
                "user_id": input_data["user_id"],
                "score": eval_result["score"],
                "difficulty": eval_result["difficulty"],
                "history": input_data.get("history", {})
            }
            schedule_result = self._run_with_retry(
                self.schedule_agent.process,
                schedule_input,
                "ScheduleAgent"
            )
            results["schedule"] = schedule_result
            self._log_audit("review_scheduling", schedule_input, schedule_result)
            
            results["status"] = "success"
            
        except Exception as e:
            self.logger.error(f"Evaluation workflow failed: {str(e)}")
            results["error"] = str(e)
            results["status"] = "failed"
            raise
        
        return results
    
    def _run_with_retry(self, func, input_data: Dict[str, Any], 
                       agent_name: str) -> Dict[str, Any]:
        """Run agent function with retry logic"""
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                result = func(input_data)
                return result
            except Exception as e:
                last_error = e
                self.logger.warning(
                    f"{agent_name} failed (attempt {attempt + 1}/{self.max_retries}): {str(e)}"
                )
                
                if attempt < self.max_retries - 1:
                    continue
        
        # All retries failed
        self.logger.error(f"{agent_name} failed after {self.max_retries} attempts")
        raise last_error
    
    def _log_audit(self, stage: str, input_data: Dict[str, Any], 
                   output_data: Dict[str, Any]):
        """Log audit trail"""
        audit_entry = {
            "timestamp": datetime.now().isoformat(),
            "stage": stage,
            "input_summary": self._summarize_data(input_data),
            "output_summary": self._summarize_data(output_data)
        }
        self.audit_trail.append(audit_entry)
    
    def _summarize_data(self, data: Dict[str, Any]) -> str:
        """Create a brief summary of data for logging"""
        summary_parts = []
        
        if "doc_id" in data:
            summary_parts.append(f"doc_id={data['doc_id']}")
        if "user_id" in data:
            summary_parts.append(f"user_id={data['user_id']}")
        if "sections" in data:
            summary_parts.append(f"sections={len(data['sections'])}")
        if "concepts" in data:
            summary_parts.append(f"concepts={len(data['concepts'])}")
        if "cards" in data:
            summary_parts.append(f"cards={len(data['cards'])}")
        if "score" in data:
            summary_parts.append(f"score={data['score']:.2f}")
        
        return ", ".join(summary_parts) if summary_parts else "no_summary"
    
    def get_audit_trail(self) -> List[Dict[str, Any]]:
        """Get the complete audit trail"""
        return self.audit_trail
    
    def save_audit_trail(self, file_path: str):
        """Save audit trail to file"""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self.audit_trail, f, ensure_ascii=False, indent=2)

