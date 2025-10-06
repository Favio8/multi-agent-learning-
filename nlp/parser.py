"""
Document parsing utilities
Supports PDF, HTML, and plain text
"""

from typing import Optional, Dict, Any
from pathlib import Path
import logging


class DocumentParser:
    """Parse various document formats"""
    
    def __init__(self):
        self.logger = logging.getLogger("nlp.DocumentParser")
    
    def parse(self, file_path: str, source_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Parse a document file
        
        Args:
            file_path: Path to document file
            source_type: Type of document (pdf, html, text). Auto-detect if None
            
        Returns:
            {
                "text": str,
                "metadata": {...}
            }
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Auto-detect source type
        if source_type is None:
            source_type = self._detect_type(file_path)
        
        # Parse based on type
        if source_type == "pdf":
            return self._parse_pdf(file_path)
        elif source_type == "html":
            return self._parse_html(file_path)
        else:
            return self._parse_text(file_path)
    
    def _detect_type(self, file_path: Path) -> str:
        """Detect document type from extension"""
        ext = file_path.suffix.lower()
        
        if ext == ".pdf":
            return "pdf"
        elif ext in [".html", ".htm"]:
            return "html"
        else:
            return "text"
    
    def _parse_pdf(self, file_path: Path) -> Dict[str, Any]:
        """Parse PDF file"""
        try:
            import fitz  # PyMuPDF
            
            doc = fitz.open(str(file_path))
            text_parts = []
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                text_parts.append(text)
            
            full_text = "\n\n".join(text_parts)
            
            metadata = {
                "num_pages": len(doc),
                "source_type": "pdf"
            }
            
            doc.close()
            
            return {
                "text": full_text,
                "metadata": metadata
            }
            
        except ImportError:
            self.logger.warning("PyMuPDF not installed, falling back to text mode")
            return self._parse_text(file_path)
        except Exception as e:
            self.logger.error(f"Failed to parse PDF: {e}")
            raise
    
    def _parse_html(self, file_path: Path) -> Dict[str, Any]:
        """Parse HTML file"""
        try:
            import trafilatura
            
            with open(file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            text = trafilatura.extract(html_content)
            
            if text is None:
                # Fallback to simple HTML stripping
                from html.parser import HTMLParser
                
                class HTMLTextExtractor(HTMLParser):
                    def __init__(self):
                        super().__init__()
                        self.text_parts = []
                    
                    def handle_data(self, data):
                        self.text_parts.append(data)
                
                parser = HTMLTextExtractor()
                parser.feed(html_content)
                text = " ".join(parser.text_parts)
            
            return {
                "text": text,
                "metadata": {"source_type": "html"}
            }
            
        except ImportError:
            self.logger.warning("trafilatura not installed, using basic parsing")
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return {
                "text": content,
                "metadata": {"source_type": "html"}
            }
        except Exception as e:
            self.logger.error(f"Failed to parse HTML: {e}")
            raise
    
    def _parse_text(self, file_path: Path) -> Dict[str, Any]:
        """Parse plain text file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            
            return {
                "text": text,
                "metadata": {"source_type": "text"}
            }
        except UnicodeDecodeError:
            # Try different encodings
            for encoding in ['gbk', 'gb2312', 'latin-1']:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        text = f.read()
                    
                    return {
                        "text": text,
                        "metadata": {
                            "source_type": "text",
                            "encoding": encoding
                        }
                    }
                except UnicodeDecodeError:
                    continue
            
            raise ValueError(f"Unable to decode file with common encodings: {file_path}")

