import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
try:
    import pymupdf as fitz
except ImportError:
    import fitz

from app.models.quotation import RawPageContent, ExtractionResult

logger = logging.getLogger(__name__)


class PDFExtractionService:
    """Extracts text, blocks, tables, and layout coordinates from supplier PDF quotations."""

    def extract_content(self, pdf_path: str | Path) -> ExtractionResult:
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        logger.info(f"Starting PDF extraction for {pdf_path.name}")
        pages: list[RawPageContent] = []
        full_text_list: list[str] = []
        is_scanned = False
        total_extracted_chars = 0

        # Step 1: Extract with PyMuPDF
        try:
            doc = fitz.open(str(pdf_path))
            total_pages = len(doc)
            
            for page_idx in range(total_pages):
                page = doc[page_idx]
                page_text = page.get_text("text")
                clean_text = page_text.strip()
                char_count = len(clean_text)
                total_extracted_chars += char_count

                # Extract table structures using fitz
                tables = []
                try:
                    tabs = page.find_tables()
                    if tabs and tabs.tables:
                        for t in tabs.tables:
                            tables.append(t.extract())
                except Exception as table_err:
                    logger.debug(f"fitz table extraction note for page {page_idx+1}: {table_err}")

                pages.append(
                    RawPageContent(
                        page_number=page_idx + 1,
                        text=clean_text,
                        source="pdf_text",
                        tables=tables,
                        has_text=char_count > 30
                    )
                )
                full_text_list.append(f"--- PAGE {page_idx + 1} ---\n{clean_text}")

            doc.close()
        except Exception as e:
            logger.error(f"PyMuPDF extraction failed for {pdf_path}: {e}")
            raise

        # Check if the PDF appears scanned (less than 30 chars per page on average)
        if total_pages > 0 and (total_extracted_chars / total_pages) < 30:
            is_scanned = True
            logger.warning(f"PDF {pdf_path.name} appears to be scanned ({total_extracted_chars} chars across {total_pages} pages)")

        full_text = "\n\n".join(full_text_list)
        logger.info(f"Extracted {len(pages)} pages ({total_extracted_chars} total characters) from {pdf_path.name}")

        return ExtractionResult(
            pages=pages,
            full_text=full_text,
            is_scanned=is_scanned,
            metadata={"filename": pdf_path.name, "page_count": len(pages)}
        )


pdf_service = PDFExtractionService()

