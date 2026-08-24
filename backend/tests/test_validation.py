"""Tests for deterministic validation engine."""
import pytest
from app.schemas.quotation import QuotationData, QuoteItem
from app.services.validation_service import validation_service


def test_validation_flags_calculation_mismatch():
    """Verify that arithmetic discrepancies (e.g. qty*price != total) are flagged as warnings."""
    items = [
        QuoteItem(
            line_number=1,
            part_number="00138737",
            description="Hexagonal bolt",
            quantity=4.0,
            unit_price=10.0,
            discount_percent=0.0,
            total_price=999.0,  # Deliberately wrong total (should be 40.0)
        )
    ]
    quote = QuotationData(
        quote_number="41260607",
        customer="PT. Flow Force Indonesia",
        items=items,
        raw_pdf_text="00138737 Hexagonal bolt 4 10.00",
    )

    validated_quote, summary = validation_service.validate_quotation(quote)
    
    assert summary.warnings_count >= 1
    assert any("Calculation mismatch" in issue.message for issue in summary.issues)
    assert validated_quote.items[0].status == "warning"


def test_validation_detects_missing_part_number_in_source():
    """Verify that hallucinated part numbers not in raw PDF text are flagged."""
    items = [
        QuoteItem(
            line_number=1,
            part_number="99999999",  # Not in text
            description="Imaginary Part",
            quantity=1.0,
            unit_price=50.0,
            total_price=50.0,
        )
    ]
    quote = QuotationData(
        quote_number="41260607",
        items=items,
        raw_pdf_text="Quote for DMN valves with part 00138737 only.",
    )

    _, summary = validation_service.validate_quotation(quote)
    assert any("not explicitly found in raw PDF text" in issue.message for issue in summary.issues)


def test_validation_passes_for_clean_quotation():
    """Verify valid quotation gets status verified with high confidence."""
    items = [
        QuoteItem(
            line_number=1,
            part_number="00138737",
            description="Hexagonal bolt M8x20",
            quantity=4.0,
            unit_price=0.32,
            discount_percent=0.0,
            total_price=1.28,
        )
    ]
    quote = QuotationData(
        quote_number="41260607",
        customer="PT. Flow Force Indonesia",
        items=items,
        lines_total=1.28,
        grand_total=1.28,
        raw_pdf_text="Quote 41260607 PT. Flow Force Indonesia 00138737 Hexagonal bolt M8x20 4 0.32 1.28",
    )

    validated_quote, summary = validation_service.validate_quotation(quote)
    assert summary.is_valid
    assert summary.errors_count == 0
    assert validated_quote.items[0].status == "verified"
    assert summary.overall_confidence >= 0.95
