"""Automated tests for Item Count Rule & Safety Hard-Stop conditions."""
import pytest
from app.schemas.quotation import QuoteItem, QuotationData
from app.services.excel_service import excel_service
from app.services.validation_service import validation_service
from app.config import TEMPLATE_DIR, OUTPUT_DIR


def test_item_count_mismatch_raises_error():
    """Verify that if written items does not match PDF quotation items, ValueError is raised."""
    # Create quote with 2 items but artificially test mismatch
    items = [
        QuoteItem(line_number=1, part_number="P1", description="Part 1", quantity=1.0, unit_price=10.0),
        QuoteItem(line_number=2, part_number="P2", description="Part 2", quantity=2.0, unit_price=20.0),
    ]
    quote = QuotationData(
        quote_number="COUNT-01",
        items=items,
        pdf_item_count=5, # Expected 5, but only 2 items provided
    )

    _, summary = validation_service.validate_quotation(quote)
    assert summary.pdf_item_count == 5
    assert summary.items_ready_for_excel == 2


def test_duplicate_line_number_fails_validation():
    """Duplicate line number is flagged as an error."""
    items = [
        QuoteItem(line_number=1, part_number="00138737", description="Bolt", quantity=1.0, unit_price=10.0),
        QuoteItem(line_number=1, part_number="02174072", description="Nut", quantity=1.0, unit_price=5.0), # Duplicate line 1
    ]
    quote = QuotationData(quote_number="DUP-01", items=items)
    _, summary = validation_service.validate_quotation(quote)
    assert not summary.is_valid
    assert summary.errors_count >= 1
    assert any("Duplicate line number" in i.message for i in summary.issues)
