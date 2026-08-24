"""Regression tests for the real DMN India quotation (Quote 41260607)."""
import pytest
from pathlib import Path
from app.config import SAMPLE_DIR, TEMPLATE_DIR, OUTPUT_DIR
from app.services.pdf_service import pdf_service
from app.services.ai_service import DeterministicFallbackProvider
from app.services.validation_service import validation_service
from app.services.excel_service import excel_service
import openpyxl


def test_dmn_exact_11_items_and_metadata():
    """Verify that exactly 11 line items are extracted from Quote 41260607, with 0 commodity-code phantom items."""
    pdf_path = SAMPLE_DIR / "Quote_Form_41260607.pdf"
    if not pdf_path.exists():
        pdf_path = SAMPLE_DIR / "Quote_41260607.pdf"
    if not pdf_path.exists():
        pdf_path = Path(__file__).resolve().parents[2] / "sample_data" / "Quote_Form_41260607.pdf"
    assert pdf_path.exists(), f"PDF not found at {pdf_path}"

    extraction = pdf_service.extract_content(pdf_path)
    parser = DeterministicFallbackProvider()
    quotation = parser.extract_quotation_sync(extraction.full_text, filename="Quote_Form_41260607.pdf")

    # 1. Total items must be exactly 11 (NOT 19)
    assert len(quotation.items) == 11, f"Expected 11 items, got {len(quotation.items)}"

    # 2. Check Part Numbers & Leading Zero preservation
    assert quotation.items[0].part_number == "23254164"
    assert quotation.items[1].part_number == "00138737"
    assert quotation.items[2].part_number == "23254165"
    assert quotation.items[3].part_number == "22210826"
    assert quotation.items[4].part_number == "02174072"
    assert quotation.items[5].part_number == "02174084"
    assert quotation.items[6].part_number == "02305474"
    assert quotation.items[7].part_number == "02305314"
    assert quotation.items[8].part_number == "23072410"
    assert quotation.items[9].part_number == "23084110"
    assert quotation.items[10].part_number == "22171642"

    # Commodity code must NEVER be an item part number
    assert all(item.part_number != "84819090" for item in quotation.items)

    # 3. Check Quantities
    assert quotation.items[0].quantity == 2.0
    assert quotation.items[1].quantity == 4.0
    assert quotation.items[2].quantity == 2.0
    assert quotation.items[3].quantity == 2.0
    assert quotation.items[4].quantity == 0.0
    assert quotation.items[5].quantity == 2.0
    assert quotation.items[6].quantity == 2.0
    assert quotation.items[7].quantity == 2.0
    assert quotation.items[8].quantity == 4.0
    assert quotation.items[9].quantity == 4.0
    assert quotation.items[10].quantity == 4.0

    # 4. Check Units
    assert quotation.items[0].unit == "NOS"
    assert quotation.items[1].unit == "NOS"
    assert quotation.items[4].unit == "EA"
    assert quotation.items[10].unit == "EA"

    # 5. Check Unit Prices
    assert quotation.items[0].unit_price == 562.00
    assert quotation.items[1].unit_price == 0.32
    assert quotation.items[2].unit_price == 28.40
    assert quotation.items[3].unit_price == 4.13
    assert quotation.items[4].unit_price == 18.40
    assert quotation.items[5].unit_price == 13.13
    assert quotation.items[6].unit_price == 6.45
    assert quotation.items[7].unit_price == 3.83
    assert quotation.items[8].unit_price == 71.54
    assert quotation.items[9].unit_price == 31.84
    assert quotation.items[10].unit_price == 30.40

    # 6. Check Discounts (30% on all items)
    assert all(item.discount_percent == 30.0 for item in quotation.items)

    # 7. Check Total Prices
    assert quotation.items[0].total_price == 786.80
    assert quotation.items[1].total_price == 0.90
    assert quotation.items[2].total_price == 39.76
    assert quotation.items[3].total_price == 5.78
    assert quotation.items[4].total_price == 0.00
    assert quotation.items[5].total_price == 18.38
    assert quotation.items[6].total_price == 9.03
    assert quotation.items[7].total_price == 5.36
    assert quotation.items[8].total_price == 200.31
    assert quotation.items[9].total_price == 89.15
    assert quotation.items[10].total_price == 85.12

    # 8. Check Commodity Codes attached to parent items
    assert quotation.items[0].commodity_code == "84819090"
    assert quotation.items[1].commodity_code == "84819090"
    assert quotation.items[2].commodity_code == "84819090"
    assert quotation.items[3].commodity_code == "84819090"
    assert quotation.items[4].commodity_code is None
    assert quotation.items[5].commodity_code is None
    assert quotation.items[6].commodity_code == "84819090"
    assert quotation.items[7].commodity_code == "84819090"
    assert quotation.items[8].commodity_code == "84819090"
    assert quotation.items[9].commodity_code == "84819090"
    assert quotation.items[10].commodity_code is None

    # 9. Check Equipment Groups
    assert len(quotation.equipment_groups) >= 2
    eq1 = quotation.equipment_groups[0]
    assert "BL-300" in eq1.name
    assert "RVNL170001" in eq1.serial_numbers
    assert eq1.line_numbers == [1, 2, 3, 4, 5, 6, 7, 8]

    eq2 = quotation.equipment_groups[1]
    assert "BXL-300" in eq2.name
    assert "RVNL154115" in eq2.serial_numbers
    assert "RVNL154116" in eq2.serial_numbers
    assert eq2.line_numbers == [9, 10, 11]

    # 10. Check Quotation Totals
    assert quotation.packaging_cost == 16.00
    assert quotation.lines_total == 1240.59
    assert quotation.miscellaneous_charges == 16.00
    assert quotation.grand_total == 1256.59

    # 11. Run Validation
    validated_quote, val_summary = validation_service.validate_quotation(quotation, extraction.full_text)
    assert val_summary.is_valid
    assert val_summary.errors_count == 0
