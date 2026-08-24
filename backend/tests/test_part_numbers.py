"""Tests for strict Part Number preservation and leading zeros retention."""
import pytest
from app.schemas.quotation import QuoteItem, QuotationData
from app.utils.text_utils import clean_part_number
from app.services.excel_service import excel_service
from app.config import SAMPLE_DIR, TEMPLATE_DIR, OUTPUT_DIR
import openpyxl


def test_part_number_schema_preserves_leading_zeros():
    """Verify that Pydantic models strictly keep leading zeros as string."""
    sample_part_numbers = [
        "00138737",
        "02174072",
        "02174084",
        "02305474",
        "02305314",
    ]

    for pn in sample_part_numbers:
        item = QuoteItem(
            line_number=1,
            part_number=pn,
            description="Test Part",
            quantity=2.0,
            unit_price=10.0,
        )
        assert isinstance(item.part_number, str)
        assert item.part_number == pn
        assert not item.part_number.startswith(pn.lstrip("0")) or pn == "0"


def test_clean_part_number_preserves_zeros():
    """Verify clean_part_number does not trim leading zeros."""
    assert clean_part_number("00138737") == "00138737"
    assert clean_part_number("  02174072  ") == "02174072"
    assert clean_part_number('"02305474"') == "02305474"


def test_excel_writes_part_numbers_as_text_with_leading_zeros():
    """Verify openpyxl writes part numbers as text format '@' and retains leading zeros."""
    template_path = TEMPLATE_DIR / "ENQ-2026-07-2549.xlsx"
    out_path = OUTPUT_DIR / "test_part_numbers_output.xlsx"

    items = [
        QuoteItem(line_number=1, part_number="00138737", description="Bolt", quantity=4.0, unit_price=0.32),
        QuoteItem(line_number=2, part_number="02174072", description="Packing", quantity=2.0, unit_price=42.0),
    ]

    quote = QuotationData(
        quote_number="41260607",
        customer="PT. Flow Force Indonesia",
        items=items,
    )

    excel_service.generate_quotation_excel(
        template_path=template_path,
        output_path=out_path,
        quotation=quote,
    )

    # Read back workbook and inspect raw cell values and data types
    wb = openpyxl.load_workbook(str(out_path), data_only=False)
    sheet = wb.active

    found_00138737 = False
    found_02174072 = False

    for row in range(1, sheet.max_row + 1):
        for col in ["B", "A", "C"]:
            val = sheet[f"{col}{row}"].value
            num_fmt = sheet[f"{col}{row}"].number_format
            if val == "00138737":
                found_00138737 = True
                assert isinstance(val, str), "00138737 was stored as non-string"
                assert num_fmt == "@", f"Expected '@' format, got {num_fmt}"
            elif val == "02174072":
                found_02174072 = True
                assert isinstance(val, str), "02174072 was stored as non-string"
                assert num_fmt == "@", f"Expected '@' format, got {num_fmt}"

    wb.close()
    assert found_00138737, "Part number '00138737' was not found or was normalized"
    assert found_02174072, "Part number '02174072' was not found or was normalized"

