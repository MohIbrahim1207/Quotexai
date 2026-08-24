"""Integration tests for PDF extraction and Excel template population."""
import pytest
from pathlib import Path
from app.config import SAMPLE_DIR, TEMPLATE_DIR, OUTPUT_DIR
from app.services.pdf_service import pdf_service
from app.services.ai_service import DeterministicFallbackProvider
from app.services.validation_service import validation_service
from app.services.excel_service import excel_service
import openpyxl


def test_pdf_extraction_extracts_dmn_content():
    """Verify PyMuPDF extracts text and detects key DMN quotation elements."""
    pdf_path = SAMPLE_DIR / "Quote_41260607.pdf"
    if not pdf_path.exists():
        pdf_path = Path(__file__).resolve().parents[2] / "sample_data" / "Quote_Form_41260607.pdf"
    assert pdf_path.exists(), f"Missing test PDF at {pdf_path}"

    result = pdf_service.extract_content(pdf_path)
    assert not result.is_scanned
    assert "41260607" in result.full_text
    assert "PT. Flow Force Indonesia" in result.full_text
    assert "00138737" in result.full_text
    assert "02174072" in result.full_text


def test_end_to_end_extraction_and_excel_generation():
    """Complete workflow test: PDF -> Extraction -> Validation -> Excel Generation -> Inspection."""
    pdf_path = SAMPLE_DIR / "Quote_41260607.pdf"
    if not pdf_path.exists():
        pdf_path = Path(__file__).resolve().parents[2] / "sample_data" / "Quote_Form_41260607.pdf"
    template_path = TEMPLATE_DIR / "ENQ-2026-07-2549.xlsx"
    out_path = OUTPUT_DIR / "E2E_Test_Quote_41260607.xlsx"

    # 1. PDF text extraction
    extraction = pdf_service.extract_content(pdf_path)

    # 2. Structured Extraction
    parser = DeterministicFallbackProvider()
    quote = parser.extract_quotation_sync(extraction.full_text, filename="Quote_41260607.pdf")

    assert quote.quote_number == "41260607"
    assert quote.customer == "PT. Flow Force Indonesia"
    assert len(quote.items) == 11

    # Check leading zeros in quote
    part_numbers = [it.part_number for it in quote.items]
    assert "00138737" in part_numbers
    assert "02174072" in part_numbers
    assert "02174084" in part_numbers
    assert "02305474" in part_numbers
    assert "02305314" in part_numbers

    # 3. Validation
    validated_quote, summary = validation_service.validate_quotation(quote, extraction.full_text)
    assert summary.is_valid
    assert summary.errors_count == 0

    # 4. Excel Generation
    items_written = excel_service.generate_quotation_excel(
        template_path=template_path,
        output_path=out_path,
        quotation=validated_quote,
        pricing_mode="quoted_price",
    )
    assert items_written == 11
    assert out_path.exists()

    # 5. Open and inspect generated Excel
    wb = openpyxl.load_workbook(str(out_path), data_only=False)
    sheet = wb.active

    # Check that part numbers exist in the generated Excel with @ formatting
    written_parts = []
    for r in range(1, sheet.max_row + 1):
        v = sheet[f"B{r}"].value
        if v and str(v).strip():
            written_parts.append(str(v).strip())

    assert "00138737" in written_parts
    assert "02174072" in written_parts
    assert "02174084" in written_parts
    assert "02305474" in written_parts
    assert "02305314" in written_parts

    # Critical: NO old template sample parts should survive!
    assert "03431814" not in written_parts
    assert "22462055" not in written_parts
    assert "02176160" not in written_parts
    assert "02175055" not in written_parts
    assert "46016050" not in written_parts

    wb.close()

