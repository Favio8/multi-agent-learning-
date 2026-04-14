"""
Database operations and management
"""

import sqlite3
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from .models import Document, Section, Concept, Relation, Card, Review, UserProfile


class Database:
    """SQLite database manager"""
    
    def __init__(self, db_path: str = "data/mas.db"):
        """
        Initialize database connection
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger("storage.Database")
        self.conn = None
        
        self._connect()
        self._initialize_schema()
    
    def _connect(self):
        """Connect to database"""
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # Enable column access by name
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.logger.info(f"Connected to database: {self.db_path}")
    
    def _initialize_schema(self):
        """Initialize database schema"""
        schema_path = Path(__file__).parent / "schema.sql"
        
        if not schema_path.exists():
            self.logger.warning("Schema file not found, skipping initialization")
            return
        
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        
        cursor = self.conn.cursor()
        cursor.executescript(schema_sql)
        self.conn.commit()
        self.logger.info("Database schema initialized")
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.logger.info("Database connection closed")
    
    # Document operations
    def insert_document(self, doc: Document) -> bool:
        """Insert a document"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO docs (doc_id, title, source, source_type, lang, created_at, updated_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                doc.doc_id,
                doc.title,
                doc.source,
                doc.source_type,
                doc.lang,
                doc.created_at or datetime.now().isoformat(),
                doc.updated_at or datetime.now().isoformat(),
                json.dumps(doc.metadata) if doc.metadata else None
            ))
            self.conn.commit()
            return True
        except Exception as e:
            self.logger.error(f"Failed to insert document: {e}")
            return False
    
    def get_document(self, doc_id: str) -> Optional[Document]:
        """Get a document by ID"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM docs WHERE doc_id = ?", (doc_id,))
        row = cursor.fetchone()
        
        if row:
            return Document(
                doc_id=row['doc_id'],
                title=row['title'],
                source=row['source'],
                source_type=row['source_type'],
                lang=row['lang'],
                created_at=row['created_at'],
                updated_at=row['updated_at'],
                metadata=json.loads(row['metadata']) if row['metadata'] else None
            )
        return None

    def list_documents(self) -> List[Dict[str, Any]]:
        """List documents with aggregate counts for UI views."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT
                d.*,
                (SELECT COUNT(*) FROM sections s WHERE s.doc_id = d.doc_id) AS sections_count,
                (SELECT COUNT(*) FROM concepts c WHERE c.doc_id = d.doc_id) AS concepts_count,
                (SELECT COUNT(*) FROM cards cd WHERE cd.doc_id = d.doc_id) AS cards_count
            FROM docs d
            ORDER BY COALESCE(d.updated_at, d.created_at) DESC
        """)
        rows = cursor.fetchall()

        return [
            {
                "doc_id": row["doc_id"],
                "title": row["title"],
                "source": row["source"],
                "source_type": row["source_type"],
                "lang": row["lang"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "sections_count": row["sections_count"],
                "concepts_count": row["concepts_count"],
                "cards_count": row["cards_count"],
            }
            for row in rows
        ]
    
    # Section operations
    def insert_sections(self, sections: List[Section]) -> bool:
        """Insert multiple sections"""
        try:
            cursor = self.conn.cursor()
            for section in sections:
                cursor.execute("""
                    INSERT INTO sections (sec_id, doc_id, idx, title, text, topic_tags, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    section.sec_id,
                    section.doc_id,
                    section.idx,
                    section.title,
                    section.text,
                    json.dumps(section.topic_tags),
                    section.created_at or datetime.now().isoformat()
                ))
            self.conn.commit()
            return True
        except Exception as e:
            self.logger.error(f"Failed to insert sections: {e}")
            return False
    
    def get_sections(self, doc_id: str) -> List[Section]:
        """Get all sections for a document"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM sections WHERE doc_id = ? ORDER BY idx", (doc_id,))
        rows = cursor.fetchall()
        
        sections = []
        for row in rows:
            sections.append(Section(
                sec_id=row['sec_id'],
                doc_id=row['doc_id'],
                idx=row['idx'],
                title=row['title'],
                text=row['text'],
                topic_tags=json.loads(row['topic_tags']) if row['topic_tags'] else [],
                created_at=row['created_at']
            ))
        return sections
    
    # Concept operations
    def insert_concepts(self, concepts: List[Concept]) -> bool:
        """Insert multiple concepts"""
        try:
            cursor = self.conn.cursor()
            for concept in concepts:
                cursor.execute("""
                    INSERT INTO concepts (cid, doc_id, term, aliases, definition, refs, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    concept.cid,
                    concept.doc_id,
                    concept.term,
                    json.dumps(concept.aliases),
                    concept.definition,
                    json.dumps(concept.refs),
                    concept.created_at or datetime.now().isoformat()
                ))
            self.conn.commit()
            return True
        except Exception as e:
            self.logger.error(f"Failed to insert concepts: {e}")
            return False
    
    def get_concepts(self, doc_id: str) -> List[Concept]:
        """Get all concepts for a document"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM concepts WHERE doc_id = ?", (doc_id,))
        rows = cursor.fetchall()
        
        concepts = []
        for row in rows:
            concepts.append(Concept(
                cid=row['cid'],
                doc_id=row['doc_id'],
                term=row['term'],
                aliases=json.loads(row['aliases']) if row['aliases'] else [],
                definition=row['definition'] or "",
                refs=json.loads(row['refs']) if row['refs'] else [],
                created_at=row['created_at']
            ))
        return concepts
    
    # Card operations
    def insert_cards(self, cards: List[Card]) -> bool:
        """Insert multiple cards"""
        try:
            cursor = self.conn.cursor()
            for card in cards:
                cursor.execute("""
                    INSERT INTO cards (card_id, doc_id, type, stem, choices, answer, explanation, 
                                      source_ref, concept_refs, difficulty, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    card.card_id,
                    card.doc_id,
                    card.type,
                    card.stem,
                    json.dumps(card.choices),
                    card.answer,
                    card.explanation,
                    card.source_ref,
                    json.dumps(card.concept_refs),
                    card.difficulty,
                    card.created_at or datetime.now().isoformat()
                ))
            self.conn.commit()
            return True
        except Exception as e:
            self.logger.error(f"Failed to insert cards: {e}")
            return False

    def replace_generated_content(
        self,
        doc_id: str,
        sections: List[Section],
        concepts: List[Concept],
        cards: List[Card],
    ) -> bool:
        """Replace generated sections, concepts and cards for a document."""
        try:
            cursor = self.conn.cursor()
            now = datetime.now().isoformat()

            cursor.execute("DELETE FROM cards WHERE doc_id = ?", (doc_id,))
            cursor.execute("DELETE FROM concepts WHERE doc_id = ?", (doc_id,))
            cursor.execute("DELETE FROM sections WHERE doc_id = ?", (doc_id,))

            for section in sections:
                cursor.execute(
                    """
                    INSERT INTO sections (sec_id, doc_id, idx, title, text, topic_tags, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        section.sec_id,
                        section.doc_id,
                        section.idx,
                        section.title,
                        section.text,
                        json.dumps(section.topic_tags),
                        section.created_at or now,
                    ),
                )

            for concept in concepts:
                cursor.execute(
                    """
                    INSERT INTO concepts (cid, doc_id, term, aliases, definition, refs, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        concept.cid,
                        concept.doc_id,
                        concept.term,
                        json.dumps(concept.aliases),
                        concept.definition,
                        json.dumps(concept.refs),
                        concept.created_at or now,
                    ),
                )

            for card in cards:
                cursor.execute(
                    """
                    INSERT INTO cards (card_id, doc_id, type, stem, choices, answer, explanation,
                                      source_ref, concept_refs, difficulty, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        card.card_id,
                        card.doc_id,
                        card.type,
                        card.stem,
                        json.dumps(card.choices),
                        card.answer,
                        card.explanation,
                        card.source_ref,
                        json.dumps(card.concept_refs),
                        card.difficulty,
                        card.created_at or now,
                    ),
                )

            cursor.execute(
                "UPDATE docs SET updated_at = ? WHERE doc_id = ?",
                (now, doc_id),
            )
            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            self.logger.error(f"Failed to replace generated content: {e}")
            return False
    
    def get_cards(self, doc_id: Optional[str] = None, limit: int = 100, offset: int = 0) -> List[Card]:
        """Get cards, optionally filtered by document"""
        cursor = self.conn.cursor()
        
        if doc_id:
            cursor.execute("""
                SELECT * FROM cards WHERE doc_id = ? 
                ORDER BY created_at DESC LIMIT ? OFFSET ?
            """, (doc_id, limit, offset))
        else:
            cursor.execute("""
                SELECT * FROM cards 
                ORDER BY created_at DESC LIMIT ? OFFSET ?
            """, (limit, offset))
        
        rows = cursor.fetchall()
        
        cards = []
        for row in rows:
            cards.append(Card(
                card_id=row['card_id'],
                doc_id=row['doc_id'],
                type=row['type'],
                stem=row['stem'],
                choices=json.loads(row['choices']) if row['choices'] else [],
                answer=row['answer'],
                explanation=row['explanation'] or "",
                source_ref=row['source_ref'] or "",
                concept_refs=json.loads(row['concept_refs']) if row['concept_refs'] else [],
                difficulty=row['difficulty'],
                created_at=row['created_at']
            ))
        return cards

    def count_cards(self, doc_id: Optional[str] = None) -> int:
        """Count cards, optionally filtered by document."""
        cursor = self.conn.cursor()

        if doc_id:
            cursor.execute("SELECT COUNT(*) AS total FROM cards WHERE doc_id = ?", (doc_id,))
        else:
            cursor.execute("SELECT COUNT(*) AS total FROM cards")

        row = cursor.fetchone()
        return int(row["total"]) if row else 0
    
    def get_card(self, card_id: str) -> Optional[Card]:
        """Get a single card by ID"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM cards WHERE card_id = ?", (card_id,))
        row = cursor.fetchone()
        
        if row:
            return Card(
                card_id=row['card_id'],
                doc_id=row['doc_id'],
                type=row['type'],
                stem=row['stem'],
                choices=json.loads(row['choices']) if row['choices'] else [],
                answer=row['answer'],
                explanation=row['explanation'] or "",
                source_ref=row['source_ref'] or "",
                concept_refs=json.loads(row['concept_refs']) if row['concept_refs'] else [],
                difficulty=row['difficulty'],
                created_at=row['created_at']
            )
        return None
    
    # Review operations
    def insert_review(self, review: Review) -> bool:
        """Insert a review record"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO reviews (id, user_id, card_id, ts, response, score, is_correct,
                                   error_type, latency_ms, next_due, ef, interval_days, repetitions)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                review.id,
                review.user_id,
                review.card_id,
                review.ts,
                review.response,
                review.score,
                1 if review.is_correct else 0,
                review.error_type,
                review.latency_ms,
                review.next_due,
                review.ef,
                review.interval_days,
                review.repetitions
            ))
            self.conn.commit()
            return True
        except Exception as e:
            self.logger.error(f"Failed to insert review: {e}")
            return False
    
    def get_reviews(self, user_id: str, card_id: Optional[str] = None) -> List[Review]:
        """Get review records for a user"""
        cursor = self.conn.cursor()
        
        if card_id:
            cursor.execute("""
                SELECT * FROM reviews 
                WHERE user_id = ? AND card_id = ?
                ORDER BY ts DESC
            """, (user_id, card_id))
        else:
            cursor.execute("""
                SELECT * FROM reviews 
                WHERE user_id = ?
                ORDER BY ts DESC
            """, (user_id,))
        
        rows = cursor.fetchall()
        
        reviews = []
        for row in rows:
            reviews.append(Review(
                id=row['id'],
                user_id=row['user_id'],
                card_id=row['card_id'],
                ts=row['ts'],
                response=row['response'],
                score=row['score'],
                is_correct=bool(row['is_correct']),
                error_type=row['error_type'],
                latency_ms=row['latency_ms'],
                next_due=row['next_due'],
                ef=row['ef'],
                interval_days=row['interval_days'],
                repetitions=row['repetitions']
            ))
        return reviews
    
    def get_due_cards(self, user_id: str) -> List[str]:
        """Get card IDs that are due for review"""
        return [record["card_id"] for record in self.get_due_review_records(user_id)]

    def get_due_review_records(self, user_id: str) -> List[Dict[str, Any]]:
        """Get the latest due review record per card for a user."""
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()
        
        cursor.execute("""
            SELECT r.card_id, r.next_due
            FROM reviews r
            JOIN (
                SELECT card_id, MAX(ts) AS latest_ts
                FROM reviews
                WHERE user_id = ?
                GROUP BY card_id
            ) latest
              ON r.card_id = latest.card_id
             AND r.ts = latest.latest_ts
            WHERE r.user_id = ? AND r.next_due <= ?
            ORDER BY r.next_due
        """, (user_id, user_id, now))
        
        rows = cursor.fetchall()
        return [{"card_id": row["card_id"], "next_due": row["next_due"]} for row in rows]
    
    # Learning progress operations
    def save_learning_progress(self, user_id: str, doc_id: str, current_idx: int, total_cards: int) -> bool:
        """保存学习进度"""
        try:
            cursor = self.conn.cursor()
            now = datetime.now().isoformat()
            safe_total = max(0, total_cards)
            safe_index = min(max(0, current_idx), safe_total)
            
            cursor.execute("""
                INSERT OR REPLACE INTO learning_progress 
                (user_id, doc_id, current_card_idx, total_cards, last_updated)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, doc_id, safe_index, safe_total, now))
            
            self.conn.commit()
            return True
        except Exception as e:
            self.logger.error(f"Failed to save learning progress: {e}")
            return False

    def sync_learning_progress_totals(self, doc_id: str, total_cards: int) -> bool:
        """Keep progress totals aligned with rebuilt card counts for the document."""
        try:
            cursor = self.conn.cursor()
            now = datetime.now().isoformat()
            safe_total = max(0, total_cards)
            cursor.execute(
                """
                UPDATE learning_progress
                SET total_cards = ?,
                    current_card_idx = CASE
                        WHEN current_card_idx > ? THEN ?
                        ELSE current_card_idx
                    END,
                    last_updated = ?
                WHERE doc_id = ?
                """,
                (safe_total, safe_total, safe_total, now, doc_id),
            )
            self.conn.commit()
            return True
        except Exception as e:
            self.logger.error(f"Failed to sync learning progress totals: {e}")
            return False

    def get_learning_progress(self, user_id: str, doc_id: str = None) -> Optional[Dict[str, Any]]:
        """获取学习进度"""
        cursor = self.conn.cursor()
        
        if doc_id:
            # 获取特定文档的进度
            cursor.execute("""
                SELECT p.*, d.title, d.source_type
                FROM learning_progress p
                JOIN docs d ON p.doc_id = d.doc_id
                WHERE p.user_id = ? AND p.doc_id = ?
            """, (user_id, doc_id))
        else:
            # 获取最近学习的文档进度
            cursor.execute("""
                SELECT p.*, d.title, d.source_type
                FROM learning_progress p
                JOIN docs d ON p.doc_id = d.doc_id
                WHERE p.user_id = ?
                ORDER BY p.last_updated DESC
                LIMIT 1
            """, (user_id,))
        
        row = cursor.fetchone()
        
        if row:
            return {
                'user_id': row['user_id'],
                'doc_id': row['doc_id'],
                'current_card_idx': row['current_card_idx'],
                'total_cards': row['total_cards'],
                'last_updated': row['last_updated'],
                'doc_title': row['title'],
                'doc_type': row['source_type']
            }
        return None
    
    def get_all_progress(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户所有学习进度"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT p.*, d.title, d.source_type
            FROM learning_progress p
            JOIN docs d ON p.doc_id = d.doc_id
            WHERE p.user_id = ?
            ORDER BY p.last_updated DESC
        """, (user_id,))
        
        rows = cursor.fetchall()
        
        progress_list = []
        for row in rows:
            progress_list.append({
                'user_id': row['user_id'],
                'doc_id': row['doc_id'],
                'current_card_idx': row['current_card_idx'],
                'total_cards': row['total_cards'],
                'last_updated': row['last_updated'],
                'doc_title': row['title'],
                'doc_type': row['source_type']
            })
        
        return progress_list


# Global database instance
_db_instance = None


def get_database(db_path: Optional[str] = None) -> Database:
    """
    Get global database instance
    
    Args:
        db_path: Database path (only used on first call)
        
    Returns:
        Database instance
    """
    global _db_instance
    
    if _db_instance is None:
        _db_instance = Database(db_path or "data/mas.db")
    
    return _db_instance

