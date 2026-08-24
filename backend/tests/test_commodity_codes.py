"""Automated tests for Commodity Code Rule (metadata attachment, never a separate quotation item)."""
import pytest
from app.schemas.quotation import QuoteItem, QuotationData
from app.services.validation_service import validation_service
from app.services.ai_service import DeterministicFallbackProvider


def test_commodity_code_attached_to_parent_item():
    """Verify that Commodity Code 84819090 is stored in commodity_code and not as a part number."""
    item = QuoteItem(
        line_number=2,
        part_number="00138737",
        description="Hexagonal bolt with thread up to the head",
        quantity=4.0,
        unit="NOS",
        unit_price=0.32,
        discount_percent=30.0,
        total_price=0.90,
        commodity_code="84819090",
    )
    assert item.part_number == "00138737"
    assert item.commodity_code == "84819090"
    assert item.part_number != "84819090"


def test_validation_flags_commodity_code_if_mistaken_as_item():
    """Validation should raise error if a commodity code is mistakenly placed as a part number."""
    item = QuoteItem(
        line_number=3,
        part_number="84819090",
        description="Commodity code",
        quantity=1.0,
        unit_price=0.0,
    )
    quote = QuotationData(
        quote_number="41260607",
        items=[item],
    )
    _, summary = validation_service.validate_quotation(quote)
    assert not summary.is_valid
    assert any("Commodity code was mistakenly extracted as a line item" in i.message for i in summary.issues)


def test_deterministic_parser_attaches_commodity_code_to_parent():
    """Parser should attach Commodity Code from subsequent text line to previous line item."""
    sample_text = """
1
23254164
Lantern ring AL/BL 300-350
2 NOS
€ 562.00
€ 786.80
30.00%
Commodity Code: 84819090
2
00138737
Hexagonal bolt M10x16
4 NOS
€ 0.32
€ 0.90
30.00%
Commodity Code: 84819090
"""
    parser = DeterministicFallbackProvider()
    quote = parser.extract_quotation_sync(sample_text)
    assert len(quote.items) == 2
    assert quote.items[0].part_number == "23254164"
    assert quote.items[0].commodity_code == "84819090"
    assert quote.items[1].part_number == "00138737"
    assert quote.items[1].commodity_code == "84819090"
    assert all(it.part_number != "84819090" for it in quote.items)
