"""
Text splitting utilities for semantic segmentation
"""

from typing import List, Optional, Dict, Any
import re
import logging


class TextSplitter:
    """Split text into semantic sections"""
    
    def __init__(self, min_length: int = 150, max_length: int = 300):
        """
        Initialize text splitter
        
        Args:
            min_length: Minimum words per section
            max_length: Maximum words per section
        """
        self.min_length = min_length
        self.max_length = max_length
        self.logger = logging.getLogger("nlp.TextSplitter")
    
    def split(self, text: str, language: str = "zh") -> List[Dict[str, str]]:
        """
        Split text into sections
        
        Args:
            text: Text to split
            language: Language code (zh or en)
            
        Returns:
            List of sections with title and text
        """
        # First, try to detect headings
        sections = self._split_by_headings(text)
        
        # If no clear headings, split by paragraphs and length
        if len(sections) <= 1:
            sections = self._split_by_length(text, language)
        
        return sections
    
    def _split_by_headings(self, text: str) -> List[Dict[str, str]]:
        """Split text by detecting headings"""
        sections = []
        
        # Patterns for common heading formats
        # 1. Numbered headings: "1.", "1.1", "第一章", etc.
        # 2. Markdown-style: "# ", "## ", etc.
        heading_patterns = [
            r'^#+\s+(.+)$',  # Markdown headings
            r'^(\d+\.(?:\d+\.)*)\s+(.+)$',  # Numbered headings
            r'^第[一二三四五六七八九十\d]+[章节部分]\s*(.*)$',  # Chinese chapter headings
            r'^[A-Z][^a-z]{0,20}$',  # All caps headings (English)
        ]
        
        lines = text.split('\n')
        current_section = {"title": "", "content": []}
        
        for line in lines:
            line = line.strip()
            
            if not line:
                continue
            
            is_heading = False
            heading_text = line
            
            # Check if line matches any heading pattern
            for pattern in heading_patterns:
                match = re.match(pattern, line)
                if match:
                    is_heading = True
                    # Extract heading text (last group or full match)
                    groups = match.groups()
                    heading_text = groups[-1] if groups else line
                    break
            
            if is_heading:
                # Save previous section if it has content
                if current_section["content"]:
                    sections.append({
                        "title": current_section["title"],
                        "text": "\n".join(current_section["content"])
                    })
                
                # Start new section
                current_section = {
                    "title": heading_text,
                    "content": []
                }
            else:
                current_section["content"].append(line)
        
        # Add last section
        if current_section["content"]:
            sections.append({
                "title": current_section["title"],
                "text": "\n".join(current_section["content"])
            })
        
        return sections
    
    def _split_by_length(self, text: str, language: str) -> List[Dict[str, str]]:
        """Split text by length when no clear structure"""
        sections = []
        
        # Split into sentences first
        if language == "zh":
            # Chinese: split by periods, exclamations, questions
            sentences = re.split(r'([。！？]+)', text)
            # Merge punctuation back
            paragraphs = []
            for i in range(0, len(sentences)-1, 2):
                if i+1 < len(sentences):
                    paragraphs.append(sentences[i] + sentences[i+1])
                else:
                    paragraphs.append(sentences[i])
            if len(sentences) % 2 == 1:
                paragraphs.append(sentences[-1])
        else:
            # English: split by periods
            paragraphs = re.split(r'\.(?:\s+|$)', text)
        
        current_section = []
        current_length = 0
        section_idx = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # Count words/characters
            if language == "zh":
                # For Chinese, count characters (excluding spaces)
                word_count = len(para.replace(' ', ''))
            else:
                word_count = len(para.split())
            
            # Check if adding this paragraph exceeds max length
            if current_length + word_count > self.max_length and current_section:
                # Save current section
                section_text = "".join(current_section) if language == "zh" else " ".join(current_section)
                # Relax the minimum length requirement for short texts
                min_required = min(self.min_length, len(text) // 2)
                if current_length >= min_required or len(current_section) > 0:
                    sections.append({
                        "title": f"Section {section_idx + 1}",
                        "text": section_text
                    })
                    section_idx += 1
                    current_section = []
                    current_length = 0
            
            current_section.append(para)
            current_length += word_count
        
        # Add last section - always add if there's content
        if current_section:
            section_text = "".join(current_section) if language == "zh" else " ".join(current_section)
            sections.append({
                "title": f"Section {section_idx + 1}",
                "text": section_text
            })
        
        # Fallback: if still no sections, return the whole text as one section
        if not sections and text.strip():
            return [{"title": "Section 1", "text": text.strip()}]
        
        return sections

