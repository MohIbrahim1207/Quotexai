"""Domain models for internal quotation processing."""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class RawPageContent:
    page_number: int
    text: str
    source: str = "pdf_text"  # "pdf_text" or "ocr"
    tables: List[List[List[str]]] = field(default_factory=list)
    has_text: bool = True


@dataclass
class ExtractionResult:
    pages: List[RawPageContent]
    full_text: str
    is_scanned: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
