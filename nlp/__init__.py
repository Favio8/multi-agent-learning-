"""
NLP utilities module
"""

from .parser import DocumentParser
from .embedding import EmbeddingManager
from .splitter import TextSplitter

__all__ = [
    "DocumentParser",
    "EmbeddingManager",
    "TextSplitter",
]

