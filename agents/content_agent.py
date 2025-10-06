"""
ContentAgent - Document parsing, cleaning, segmentation and topic tagging
"""

from typing import Dict, Any, List, Optional
from .base_agent import BaseAgent
import json


class ContentAgent(BaseAgent):
    """
    ContentAgent handles document ingestion and processing:
    - Parse PDF/HTML/plain text documents
    - Clean and normalize text
    - Split into semantic sections
    - Tag sections with topics
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(agent_id="ContentAgent", config=config)
        
        # Configuration parameters
        self.min_section_length = config.get("min_section_length", 150) if config else 150
        self.max_section_length = config.get("max_section_length", 300) if config else 300
        self.language = config.get("language", "zh") if config else "zh"
        
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process document and extract sections
        
        Args:
            input_data: {
                "doc_id": str,
                "file_path": str or "content": str,
                "source": str (pdf/html/text),
                "language": str (optional)
            }
            
        Returns:
            {
                "doc_id": str,
                "sections": [
                    {
                        "sec_id": str,
                        "title": str,
                        "text": str,
                        "topic_tags": [str]
                    }
                ],
                "metadata": {
                    "total_sections": int,
                    "language": str,
                    "source_type": str
                }
            }
        """
        self.validate_input(input_data, ["doc_id"])
        
        doc_id = input_data["doc_id"]
        source_type = input_data.get("source", "text")
        language = input_data.get("language", self.language)
        
        self.logger.info(f"Processing document {doc_id} (type: {source_type})")
        
        # Parse document based on source type
        raw_content = self._parse_document(input_data)
        
        # Clean and normalize
        cleaned_content = self._clean_content(raw_content)
        
        # Split into sections
        sections = self._split_sections(cleaned_content, doc_id)
        
        # Tag topics for each section
        sections = self._tag_topics(sections)
        
        result = {
            "doc_id": doc_id,
            "sections": sections,
            "language": language,
            "metadata": {
                "total_sections": len(sections),
                "language": language,
                "source_type": source_type
            }
        }
        
        self.log_audit(
            action="parse_and_segment",
            input_summary=f"doc_id={doc_id}, type={source_type}",
            output_summary=f"{len(sections)} sections extracted"
        )
        
        return result
    
    def _parse_document(self, input_data: Dict[str, Any]) -> str:
        """Parse document based on source type"""
        # TODO: Implement actual parsing logic with pymupdf, trafilatura, etc.
        # For now, return mock content or direct content
        if "content" in input_data:
            return input_data["content"]
        
        file_path = input_data.get("file_path")
        if file_path:
            # Will implement actual file reading
            self.logger.warning("File parsing not yet implemented, returning placeholder")
            return f"Content from {file_path}"
        
        return ""
    
    def _clean_content(self, content: str) -> str:
        """Clean and normalize text content"""
        if not content:
            return ""
        
        import re
        # Remove excessive whitespace within lines, but preserve sentence structure
        lines = content.split('\n')
        cleaned_lines = []
        for line in lines:
            # Remove excessive spaces within a line
            cleaned_line = re.sub(r'[ \t]+', ' ', line)
            cleaned_line = cleaned_line.strip()
            if cleaned_line:
                cleaned_lines.append(cleaned_line)
        
        # Join lines back, preserving paragraph structure
        content = '\n'.join(cleaned_lines)
        return content
    
    def _split_sections(self, content: str, doc_id: str) -> List[Dict[str, Any]]:
        """Split content into sections based on length and structure"""
        if not content or not content.strip():
            return []
        
        # Use TextSplitter for better segmentation
        try:
            from nlp.splitter import TextSplitter
            splitter = TextSplitter(
                min_length=self.min_section_length,
                max_length=self.max_section_length
            )
            raw_sections = splitter.split(content, self.language)
        except Exception as e:
            self.logger.warning(f"TextSplitter failed: {e}, using simple split")
            # Fallback to simple split
            raw_sections = [{"title": "Section 1", "text": content}]
        
        # Convert to proper format with IDs
        sections = []
        for idx, section in enumerate(raw_sections):
            sections.append({
                "sec_id": f"{doc_id}_s{idx}",
                "doc_id": doc_id,
                "idx": idx,
                "title": section.get("title", f"Section {idx + 1}"),
                "text": section.get("text", ""),
                "topic_tags": []
            })
        
        return sections
    
    def _tag_topics(self, sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Tag each section with topics"""
        # TODO: Implement topic tagging using:
        # - Zero-shot classification
        # - Keyword extraction (TextRank)
        # - LLM-based tagging
        
        for section in sections:
            # Placeholder: extract simple keywords
            text = section["text"].lower()
            # Mock topic extraction
            section["topic_tags"] = ["general"]
        
        return sections

