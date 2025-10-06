"""
Data models for the system
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class Document(BaseModel):
    """Document model"""
    doc_id: str
    title: str
    source: str
    source_type: str = "text"  # pdf, html, text
    lang: str = "zh"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class Section(BaseModel):
    """Section model"""
    sec_id: str
    doc_id: str
    idx: int
    title: str
    text: str
    topic_tags: List[str] = Field(default_factory=list)
    created_at: Optional[str] = None


class Concept(BaseModel):
    """Concept model (knowledge graph node)"""
    cid: str
    doc_id: str
    term: str
    aliases: List[str] = Field(default_factory=list)
    definition: str = ""
    refs: List[str] = Field(default_factory=list)  # section ids
    created_at: Optional[str] = None


class Relation(BaseModel):
    """Relation model (knowledge graph edge)"""
    id: str
    src: str  # source concept id
    rel: str  # relation type
    dst: str  # destination concept id
    weight: float = 1.0
    created_at: Optional[str] = None


class Card(BaseModel):
    """Quiz card model"""
    card_id: str
    doc_id: str
    type: str  # cloze, mcq, short
    stem: str
    choices: List[str] = Field(default_factory=list)
    answer: str
    explanation: str = ""
    source_ref: str = ""
    concept_refs: List[str] = Field(default_factory=list)
    difficulty: str = "M"  # L, M, H
    created_at: Optional[str] = None


class Review(BaseModel):
    """Review record model"""
    id: str
    user_id: str
    card_id: str
    ts: str  # timestamp
    response: str
    score: float
    is_correct: bool
    error_type: Optional[str] = None
    latency_ms: int = 0
    next_due: str
    ef: float = 2.5  # easiness factor
    interval_days: int = 1
    repetitions: int = 0


class UserProfile(BaseModel):
    """User profile model"""
    user_id: str
    username: str
    email: Optional[str] = None
    mastery: Dict[str, float] = Field(default_factory=dict)  # concept_id -> score
    prefs: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

