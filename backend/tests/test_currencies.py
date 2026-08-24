"""Automated tests for Multi-Currency support (EUR, USD, INR, GBP, IDR, etc.)."""
import pytest
from app.utils.text_utils import extract_currency, get_currency_symbol, normalize_price
from app.schemas.quotation import QuoteItem, QuotationData, PriceDetail
from app.services.validation_service import validation_service
from app.services.excel_service import excel_service
from app.config import TEMPLATE_DIR, OUTPUT_DIR
import openpyxl


def test_currency_detection_symbols_and_codes():
    """Verify robust currency detector identifies EUR, USD, INR, GBP, IDR, JPY, CNY."""
    assert extract_currency("Unit Price: € 562.00 Total: € 786.80") == "EUR"
    assert extract_currency("Unit Price: $ 1,250.00 Total: $ 2,500.00") == "USD"
    assert extract_currency("Unit Price: ₹ 85,000.00 Total: ₹ 170,000.00") == "INR"
    assert extract_currency("Unit Price: £ 450.00 Total: £ 900.00") == "GBP"
    assert extract_currency("Total: Rp 15.000.000 IDR") == "IDR"
    assert extract_currency("Quotation in USD currency for export") == "USD"
    assert extract_currency("Amount payable in INR via NEFT") == "INR"


def test_currency_symbols():
    """Verify correct currency symbols are resolved."""
    assert get_currency_symbol("EUR") == "€"
    assert get_currency_symbol("USD") == "$"
    assert get_currency_symbol("INR") == "₹"
    assert get_currency_symbol("GBP") == "£"
    assert get_currency_symbol("IDR") == "Rp"


def test_usd_quotation_preserves_usd_without_conversion():
    """Verify USD quotation preserves USD prices and currency metadata without conversion."""
    items = [
        QuoteItem(
            line_number=1,
            part_number="US-P100",
            description="High pressure valve",
            quantity=2.0,
            unit="EA",
            unit_price=1250.00,
            unit_price_detail=PriceDetail(amount=1250.00, currency="USD", symbol="$"),
            currency="USD",
            currency_symbol="$",
            discount_percent=0.0,
            total_price=2500.00,
            total_price_detail=PriceDetail(amount=2500.00, currency="USD", symbol="$"),
        )
    ]
    quote = QuotationData(
        quote_number="US-QUOTE-99",
        customer="Acme Corp USA",
        currency="USD",
        currency_symbol="$",
        items=items,
        lines_total=2500.00,
        grand_total=2500.00,
    )

    validated_quote, summary = validation_service.validate_quotation(quote)
    assert validated_quote.currency == "USD"
    assert validated_quote.items[0].unit_price == 1250.00
    assert validated_quote.items[0].currency == "USD"

    template_path = TEMPLATE_DIR / "ENQ-2026-07-2549.xlsx"
    out_path = OUTPUT_DIR / "test_usd_quote_out.xlsx"
    count = excel_service.generate_quotation_excel(
        template_path=template_path,
        output_path=out_path,
        quotation=validated_quote,
    )
    assert count == 1


def test_inr_quotation_preserves_inr_without_conversion():
    """Verify INR quotation preserves INR values without EUR assumption."""
    items = [
        QuoteItem(
            line_number=1,
            part_number="IN-P200",
            description="Industrial Gasket",
            quantity=10.0,
            unit="NOS",
            unit_price=8500.00,
            unit_price_detail=PriceDetail(amount=8500.00, currency="INR", symbol="₹"),
            currency="INR",
            currency_symbol="₹",
            discount_percent=10.0,
            total_price=76500.00,
            total_price_detail=PriceDetail(amount=76500.00, currency="INR", symbol="₹"),
        )
    ]
    quote = QuotationData(
        quote_number="IN-QUOTE-44",
        customer="Bharat Heavy Industries",
        currency="INR",
        currency_symbol="₹",
        items=items,
        lines_total=76500.00,
        grand_total=76500.00,
    )

    validated_quote, summary = validation_service.validate_quotation(quote)
    assert summary.is_valid
    assert validated_quote.currency == "INR"
    assert validated_quote.items[0].unit_price == 8500.00
