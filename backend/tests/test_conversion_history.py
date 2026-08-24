"""Automated test suite for Conversion History persistence, retrieval, filtering, and actions."""
import pytest
from pathlib import Path
from app.services.pdf_service import pdf_service
from app.services.ai_service import DeterministicFallbackProvider
from app.services.quotation_service import quotation_orchestrator
from app.services.history_service import history_service
from app.schemas.quotation import GenerateExcelRequest
from app.config import SAMPLE_DIR, OUTPUT_DIR


def test_conversion_history_end_to_end():
    """Verify that end-to-end processing of multiple quotes creates actionable history records."""
    # Clear prior test records for deterministic testing
    history_service.clear_all()

    # 1. Process Quote 41260607 (DMN)
    dmn_pdf = SAMPLE_DIR / "Quote_Form_41260607.pdf"
    if not dmn_pdf.exists():
        dmn_pdf = Path(__file__).resolve().parents[2] / "sample_data" / "Quote_Form_41260607.pdf"

    dmn_ext = pdf_service.extract_content(dmn_pdf)
    dmn_quote = DeterministicFallbackProvider().extract_quotation_sync(dmn_ext.full_text, filename="Quote_Form_41260607.pdf")
    dmn_quote.source_pdf_id = "test_dmn_pdf_id"

    # Save extraction record
    history_service.create_or_update_record(
        quotation=dmn_quote,
        source_pdf_filename="Quote_Form_41260607.pdf",
        source_pdf_id="test_dmn_pdf_id",
        template_id="ENQ-2026-07-2549.xlsx",
        status="verified",
    )

    # Generate Excel
    req1 = GenerateExcelRequest(
        quotation=dmn_quote,
        template_id="ENQ-2026-07-2549.xlsx",
        pricing_mode="quoted_price",
        margin_percent=0.0,
        supplier_discount_percent=0.0,
    )
    res1 = quotation_orchestrator.generate_excel_quotation(req1)
    assert res1.success is True

    # 2. Process Quote 11009223 (Fitzpatrick)
    fitz_pdf = SAMPLE_DIR / "Fitzpatrick_11009223_PT_Flow_Force_Indonesia_.pdf"
    if not fitz_pdf.exists():
        fitz_pdf = Path(__file__).resolve().parents[2] / "sample_data" / "Fitzpatrick_11009223_PT_Flow_Force_Indonesia_.pdf"

    fitz_ext = pdf_service.extract_content(fitz_pdf)
    fitz_quote = DeterministicFallbackProvider().extract_quotation_sync(fitz_ext.full_text, filename="Fitzpatrick_11009223.pdf")
    fitz_quote.source_pdf_id = "test_fitz_pdf_id"

    # Generate Excel directly
    req2 = GenerateExcelRequest(
        quotation=fitz_quote,
        template_id="ENQ-2026-07-2549.xlsx",
        pricing_mode="quoted_price",
        margin_percent=0.0,
        supplier_discount_percent=0.0,
    )
    res2 = quotation_orchestrator.generate_excel_quotation(req2)
    assert res2.success is True

    # 3. Verify History Records List
    records, total_count, total_pages = history_service.list_records(page=1, limit=10)
    assert total_count >= 2
    assert total_pages >= 1

    quote_numbers = [r["quote_number"] for r in records]
    assert "41260607" in quote_numbers
    assert "11009223" in quote_numbers

    # Find DMN record
    dmn_rec = next(r for r in records if r["quote_number"] == "41260607")
    assert dmn_rec["status"] == "generated"
    assert dmn_rec["items_count"] == 11
    assert dmn_rec["excel_file_id"] == res1.file_id
    assert dmn_rec["excel_filename"] == "41260607_Quotation.xlsx"

    # Find Fitzpatrick record
    fitz_rec = next(r for r in records if r["quote_number"] == "11009223")
    assert fitz_rec["status"] == "generated"
    assert fitz_rec["items_count"] == 2
    assert fitz_rec["excel_file_id"] == res2.file_id
    assert fitz_rec["grand_total"] == 7860.0

    # 4. Search and Filter
    search_records, search_total, _ = history_service.list_records(search="11009223")
    assert search_total == 1
    assert search_records[0]["quote_number"] == "11009223"

    gen_records, gen_total, _ = history_service.list_records(status="generated")
    assert gen_total >= 2

    # 5. Full Record Retrieval for Reopening
    full_dmn = history_service.get_record(dmn_rec["id"])
    assert full_dmn is not None
    assert full_dmn["quotation_data"]["quote_number"] == "41260607"
    assert len(full_dmn["quotation_data"]["items"]) == 11

    # 6. Delete Record
    deleted = history_service.delete_record(dmn_rec["id"])
    assert deleted is True
    remaining, rem_total, _ = history_service.list_records()
    assert rem_total == total_count - 1
