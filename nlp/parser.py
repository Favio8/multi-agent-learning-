"""
Document parsing utilities.

Supports stable built-in parsing for PDF/HTML/plain text and
MarkItDown-backed conversion for Office and structured text formats.
"""

from html.parser import HTMLParser
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from markitdown import MarkItDown


class HTMLTextExtractor(HTMLParser):
    """Simple fallback HTML text extractor."""

    def __init__(self) -> None:
        super().__init__()
        self.text_parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.text_parts.append(data)


class DocumentParser:
    """Parse various document formats."""

    TYPE_BY_EXTENSION = {
        ".pdf": "pdf",
        ".html": "html",
        ".htm": "html",
        ".txt": "text",
        ".docx": "docx",
        ".pptx": "pptx",
        ".xlsx": "xlsx",
        ".xls": "xls",
        ".md": "markdown",
        ".markdown": "markdown",
        ".csv": "csv",
        ".json": "json",
        ".xml": "xml",
    }
    MARKITDOWN_REQUIRED_TYPES = {"docx", "pptx", "xlsx", "xls"}
    MARKITDOWN_TYPES = MARKITDOWN_REQUIRED_TYPES | {
        "markdown",
        "csv",
        "json",
        "xml",
    }
    TEXT_ENCODINGS = ("utf-8", "utf-8-sig", "gbk", "gb2312", "latin-1")

    def __init__(self):
        self.logger = logging.getLogger("nlp.DocumentParser")
        self._markitdown = self._create_markitdown()
        self.logger.info("MarkItDown support enabled")

    def detect_type(self, file_path: str | Path) -> str:
        """Public wrapper for file type detection."""
        return self._detect_type(Path(file_path))

    def parse(self, file_path: str, source_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Parse a document file.

        Args:
            file_path: Path to document file
            source_type: Stored type hint. Auto-detect if None.

        Returns:
            {
                "text": str,
                "metadata": {...}
            }
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        detected_type = self._detect_type(file_path)
        normalized_type = (source_type or "").strip().lower()

        if not normalized_type:
            normalized_type = detected_type
        elif normalized_type == "text" and detected_type != "text":
            # Older uploads were stored as "text" for every unknown extension.
            normalized_type = detected_type

        if normalized_type == "pdf":
            return self._parse_pdf(file_path)
        if normalized_type == "html":
            return self._parse_html(file_path)
        if normalized_type in self.MARKITDOWN_TYPES:
            return self._parse_markitdown(file_path, normalized_type)
        return self._parse_text(file_path, source_type=normalized_type or "text")

    def _detect_type(self, file_path: Path) -> str:
        """Detect document type from extension."""
        return self.TYPE_BY_EXTENSION.get(file_path.suffix.lower(), "text")

    def _create_markitdown(self) -> MarkItDown:
        """Initialize the shared MarkItDown converter."""
        try:
            return MarkItDown(enable_plugins=False)
        except TypeError:
            return MarkItDown()

    def _parse_pdf(self, file_path: Path) -> Dict[str, Any]:
        """Parse PDF file."""
        try:
            import fitz  # PyMuPDF

            doc = fitz.open(str(file_path))
            text_parts = []

            for page_num in range(len(doc)):
                page = doc[page_num]
                text_parts.append(page.get_text())

            full_text = "\n\n".join(text_parts)
            metadata = {
                "num_pages": len(doc),
                "source_type": "pdf",
                "parser": "pymupdf",
            }
            doc.close()

            return {
                "text": full_text,
                "metadata": metadata,
            }
        except ImportError:
            self.logger.warning("PyMuPDF not installed, falling back to text mode")
            return self._parse_text(file_path, source_type="pdf", parser_name="text-fallback")
        except Exception as exc:
            self.logger.error("Failed to parse PDF: %s", exc)
            raise

    def _parse_html(self, file_path: Path) -> Dict[str, Any]:
        """Parse HTML file."""
        html_content, encoding = self._read_text_file(file_path)

        text = None
        parser_name = "basic-html"
        try:
            import trafilatura

            text = trafilatura.extract(html_content)
            if text:
                parser_name = "trafilatura"
        except ImportError:
            self.logger.warning("trafilatura not installed, using basic HTML extraction")
        except Exception as exc:
            self.logger.warning("trafilatura extraction failed for %s: %s", file_path, exc)

        if not text:
            extractor = HTMLTextExtractor()
            extractor.feed(html_content)
            text = " ".join(part.strip() for part in extractor.text_parts if part.strip())

        return {
            "text": text,
            "metadata": {
                "source_type": "html",
                "encoding": encoding,
                "parser": parser_name,
            },
        }

    def _parse_markitdown(self, file_path: Path, source_type: str) -> Dict[str, Any]:
        """Parse supported files with MarkItDown."""
        try:
            result = self._markitdown.convert(str(file_path))
            text = getattr(result, "text_content", "") or ""
            metadata = {
                "source_type": source_type,
                "parser": "markitdown",
            }

            title = getattr(result, "title", None)
            if title:
                metadata["title"] = title

            return {
                "text": text,
                "metadata": metadata,
            }
        except Exception as exc:
            if source_type in self.MARKITDOWN_REQUIRED_TYPES:
                self.logger.error("MarkItDown failed to parse %s: %s", file_path, exc)
                raise

            self.logger.warning(
                "MarkItDown failed for %s, falling back to plain text: %s",
                file_path.name,
                exc,
            )
            return self._parse_text(file_path, source_type=source_type, parser_name="text-fallback")

    def _parse_text(
        self,
        file_path: Path,
        source_type: str = "text",
        parser_name: str = "plain-text",
    ) -> Dict[str, Any]:
        """Parse plain or text-like files."""
        text, encoding = self._read_text_file(file_path)
        return {
            "text": text,
            "metadata": {
                "source_type": source_type,
                "encoding": encoding,
                "parser": parser_name,
            },
        }

    def _read_text_file(self, file_path: Path) -> Tuple[str, str]:
        """Read text content with a small set of encoding fallbacks."""
        last_error: Optional[UnicodeDecodeError] = None
        for encoding in self.TEXT_ENCODINGS:
            try:
                with open(file_path, "r", encoding=encoding) as file_handle:
                    return file_handle.read(), encoding
            except UnicodeDecodeError as exc:
                last_error = exc

        raise ValueError(
            f"Unable to decode file with common encodings: {file_path}"
        ) from last_error

