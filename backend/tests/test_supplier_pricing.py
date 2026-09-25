import io
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app
from app.config import SAMPLE_DIR
from app.schemas.supplier_pricing import (
    SupplierQuotationData,
    SupplierQuoteItem,
    PricingConfigParameters,
    SupplierPricingCalculationRequest,
)
from app.services.supplier_pricing_service import supplier_pricing_service

client = TestClient(app)


def test_supplier_pricing_workflow_stages_api():
    """Verify that workflow stages endpoint returns all 4 stages with proper placeholders."""
    response = client.get("/api/supplier-pricing/stages")
    assert response.status_code == 200
    data = response.json()
    assert "stages" in data
    assert len(data["stages"]) == 4

    stage_ids = [s["id"] for s in data["stages"]]
    assert "stage_1_extraction" in stage_ids
    assert "stage_2_pricing" in stage_ids
    assert "stage_3_approval" in stage_ids
    assert "stage_4_zoho_books" in stage_ids

    # All 4 stages are now active and unlocked
    assert data["stages"][0]["is_placeholder"] is False
    assert data["stages"][1]["is_placeholder"] is False
    assert data["stages"][2]["is_placeholder"] is False
    assert data["stages"][3]["is_placeholder"] is False


def test_supplier_pricing_validation_detects_missing_and_math_errors():
    """Verify validation detects missing required fields and math discrepancies."""
    # Test quotation with missing supplier, missing quote number, and invalid item
    quote = SupplierQuotationData(
        supplier_name="",
        quote_number="",
        quote_date="2026-09-15",
        currency="USD",
        packing_charges=50.0,
        freight_charges=100.0,
        other_charges=0.0,
        grand_total=1000.0,  # Intentional discrepancy
        items=[
            SupplierQuoteItem(
                line_number=1,
                part_number="",  # Missing
                description="Test Widget",
                quantity=None,  # Missing
                unit="PCS",
                currency="USD",
                unit_price=None,  # Missing
                discount=0.0,
                total=0.0,
            ),
            SupplierQuoteItem(
                line_number=2,
                part_number="WDG-999",
                description="Precision Valve",
                quantity=10.0,
                unit="PCS",
                currency="USD",
                unit_price=50.0,
                discount=10.0,  # 10% discount -> expected subtotal: 450.00
                total=300.0,  # Discrepancy with 450.00
            )
        ]
    )

    summary = supplier_pricing_service.validate_quotation(quote)
    assert summary.is_valid is False
    assert summary.errors_count > 0
    assert "supplier_name" in summary.missing_fields
    assert "quote_number" in summary.missing_fields
    assert summary.field_status.get("supplier_name") == "missing"
    assert summary.field_status.get("quote_number") == "missing"

    # Math discrepancy on line 2 total and grand_total
    assert any("differs from sum" in iss.message or "does not match Qty" in iss.message for iss in summary.issues)


def test_supplier_pricing_validation_api():
    """Verify POST /api/supplier-pricing/validate works seamlessly."""
    payload = {
        "supplier_name": "Atlas Fasteners Corp",
        "quote_number": "QU-2026-8871",
        "quote_date": "2026-09-15",
        "delivery_lead_time": "2-3 Weeks",
        "currency": "USD",
        "packing_charges": 25.0,
        "freight_charges": 75.0,
        "other_charges": 0.0,
        "lines_total": 500.0,
        "grand_total": 600.0,
        "items": [
            {
                "line_number": 1,
                "part_number": "0028912",
                "description": "Hex Bolt M8x40 Stainless Steel",
                "quantity": 100.0,
                "unit": "PCS",
                "currency": "USD",
                "unit_price": 5.0,
                "discount": 0.0,
                "packing_charges": 0.0,
                "freight_charges": 0.0,
                "total": 500.0,
                "delivery_lead_time": "2-3 Weeks",
                "validation_status": "valid",
                "validation_notes": [],
                "confidence": {}
            }
        ]
    }

    res = client.post("/api/supplier-pricing/validate", json=payload)
    assert res.status_code == 200
    val_data = res.json()
    assert val_data["is_valid"] is True
    assert val_data["errors_count"] == 0
    assert val_data["field_status"]["supplier_name"] == "valid"
    assert val_data["field_status"]["quote_number"] == "valid"


def test_supplier_pdf_upload_and_extraction():
    """Verify supplier PDF upload and extraction endpoint on real sample PDF."""
    pdf_path = SAMPLE_DIR / "Quote_41260607.pdf"
    if not pdf_path.exists():
        pdf_path = SAMPLE_DIR / "Quote_Form_41260607.pdf"

    assert pdf_path.exists(), f"Sample PDF missing at {pdf_path}"

    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    # Test upload
    upload_res = client.post(
        "/api/supplier-pricing/upload-pdf",
        files={"file": ("test_supplier_quote.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    )
    assert upload_res.status_code == 200
    upload_data = upload_res.json()
    assert upload_data["success"] is True
    file_id = upload_data["file_id"]

    # Test extraction
    extract_res = client.post(
        "/api/supplier-pricing/extract",
        data={"pdf_id": file_id}
    )
    assert extract_res.status_code == 200
    extract_data = extract_res.json()
    assert extract_data["success"] is True
    quotation = extract_data["quotation"]
    assert quotation["quote_number"] is not None
    assert len(quotation["items"]) > 0
    assert extract_data["validation"] is not None


def test_dmn_quote_41260509_exact_extraction():
    """Verify DMN Quote 41260509 extracts exactly 2 items from Page 1 without spec-sheet phantom items."""
    pdf_path = SAMPLE_DIR / "DMN_Quote_41260509_Rev0.pdf"
    if not pdf_path.exists():
        pdf_path = Path("c:/Quotexai/sample_data/DMN_Quote_41260509_Rev0.pdf")

    assert pdf_path.exists(), f"DMN 41260509 sample PDF missing at {pdf_path}"

    res = supplier_pricing_service.extract_from_pdf(pdf_path, "test_41260509")
    assert res.success is True
    quote = res.quotation

    # Header fields verification
    assert quote.supplier_name == "DMN INDIA PRIVATE LIMITED"
    assert quote.customer == "PT. Flow Force Indonesia"
    assert quote.quote_number == "41260509"
    assert quote.quote_date == "29/06/2026"
    assert quote.currency == "EUR"
    assert "100% Upfront before Dispatch" in (quote.payment_terms or "")
    assert "FCA Noordwijkerhout Incoterms" in (quote.delivery_lead_time or "")

    # Item count: must be exactly 2 items from page 1, zero from technical spec pages 2-7
    assert len(quote.items) == 2

    # Line 1 verification
    item1 = quote.items[0]
    assert item1.line_number == 1
    assert item1.part_number == "RV BL 200 4TS"
    assert item1.description == "BL 200 4TS : BL - Rotary valve"
    assert item1.option == "1"
    assert item1.quantity == 1.0
    assert item1.unit == "NOS"
    assert item1.unit_price == 10923.00
    assert item1.discount == 30.0
    assert item1.total == 7646.10
    assert item1.packing_charges == 125.00
    assert "20 weeks" in (item1.delivery_lead_time or "")

    # Line 2 verification
    item2 = quote.items[1]
    assert item2.line_number == 2
    assert item2.part_number == "RV BL 200 2"
    assert item2.description == "BL 200 2 : BL - Rotary valve"
    assert item2.option == "2"
    assert item2.quantity == 1.0
    assert item2.unit == "NOS"
    assert item2.unit_price == 15088.00
    assert item2.discount == 30.0
    assert item2.total == 10561.60
    assert item2.packing_charges == 125.00
    assert "20 weeks" in (item2.delivery_lead_time or "")

    # Summary totals verification
    assert quote.lines_total == 18207.70
    assert quote.other_charges == 250.00
    assert quote.grand_total == 18457.70

    # Validation summary
    assert res.validation.is_valid is True
    assert res.validation.errors_count == 0


def test_stage_2_pricing_calculation_deterministic():
    """Verify deterministic pricing calculation using DMN 41260509 extracted quotation."""
    pdf_path = SAMPLE_DIR / "DMN_Quote_41260509_Rev0.pdf"
    if not pdf_path.exists():
        pdf_path = Path("c:/Quotexai/sample_data/DMN_Quote_41260509_Rev0.pdf")

    extract_res = supplier_pricing_service.extract_from_pdf(pdf_path, "test_41260509")
    quotation = extract_res.quotation

    # Standard enterprise default: EUR -> EUR, 10% margin on selling
    req = SupplierPricingCalculationRequest(
        quotation=quotation,
        config=PricingConfigParameters(
            exchange_rate=1.0,
            target_currency="EUR",
            default_margin_percent=10.0,
            margin_method="margin_on_selling",
            freight_total=0.0,
            customs_duty_percent=0.0,
            local_handling_charge=0.0,
        ),
    )

    resp = supplier_pricing_service.calculate_pricing(req)
    assert resp.success is True
    assert len(resp.items) == 2

    item1 = resp.items[0]
    # Line 1: 10923.00 with 30% discount = 7646.10 net.
    assert item1.supplier_unit_price == 10923.00
    assert item1.discount_percent == 30.0
    assert item1.discount_amount_unit == 3276.90
    assert item1.net_supplier_unit_price == 7646.10
    assert item1.net_supplier_total == 7646.10
    assert item1.packing_charge_unit == 125.00
    # Landed cost = 7646.10 + 125.00 = 7771.10
    assert item1.landed_cost_unit == 7771.10
    assert item1.landed_cost_total == 7771.10
    # Final selling price: 7771.10 / (1 - 0.10) = 8634.56
    assert item1.final_unit_selling_price == 8634.56
    assert item1.final_total_selling_price == 8634.56
    assert item1.margin_amount_unit == 863.46
    assert len(item1.step_formula_breakdown) >= 8

    item2 = resp.items[1]
    # Line 2: 15088.00 with 30% discount = 10561.60 net.
    assert item2.supplier_unit_price == 15088.00
    assert item2.discount_percent == 30.0
    assert item2.discount_amount_unit == 4526.40
    assert item2.net_supplier_unit_price == 10561.60
    assert item2.packing_charge_unit == 125.00
    # Landed cost = 10561.60 + 125.00 = 10686.60
    assert item2.landed_cost_unit == 10686.60
    # Final selling price: 10686.60 / (1 - 0.10) = 11874.00
    assert item2.final_unit_selling_price == 11874.00
    assert item2.margin_amount_unit == 1187.40

    # Summary checks
    assert resp.summary.total_supplier_net == 18207.70
    assert resp.summary.total_landed_cost == 18457.70
    assert resp.summary.total_selling_price == round(8634.56 + 11874.00, 2)
    assert resp.summary.total_gross_profit == round((8634.56 + 11874.00) - 18457.70, 2)
    assert resp.summary.overall_margin_percent == 10.0


def test_stage_2_pricing_api_with_fx_and_line_overrides():
    """Verify POST /api/supplier-pricing/calculate-pricing with currency conversion and per-line margin overrides."""
    quote_data = {
        "supplier_name": "DMN Westinghouse",
        "quote_number": "DMN-9901",
        "currency": "EUR",
        "items": [
            {
                "line_number": 1,
                "part_number": "VALVE-01",
                "description": "Rotary Valve 200mm",
                "quantity": 2.0,
                "unit": "NOS",
                "currency": "EUR",
                "unit_price": 5000.00,
                "discount": 20.0,
                "packing_charges": 100.00,
                "freight_charges": 0.0,
                "total": 8000.00,
            }
        ]
    }

    # Net per unit = 5000 * 0.80 = 4000.00 EUR
    # FX = 1.10 -> converted unit price = 4400.00 USD
    # Packing per unit = (100 / 2) * 1.10 = 55.00 USD
    # Landed cost unit = 4400.00 + 55.00 = 4455.00 USD
    # Line override margin = 15% on selling -> 4455.00 / 0.85 = 5241.18 USD
    payload = {
        "quotation": quote_data,
        "config": {
            "exchange_rate": 1.10,
            "target_currency": "USD",
            "default_margin_percent": 10.0,
            "margin_method": "margin_on_selling",
            "freight_total": 0.0,
            "customs_duty_percent": 0.0,
            "local_handling_charge": 0.0,
        },
        "line_overrides": {
            "1": {
                "margin_percent": 15.0,
            }
        }
    }

    resp = client.post("/api/supplier-pricing/calculate-pricing", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert len(data["items"]) == 1

    item = data["items"][0]
    assert item["supplier_unit_price"] == 5000.00
    assert item["discount_percent"] == 20.0
    assert item["net_supplier_unit_price"] == 4000.00
    assert item["exchange_rate"] == 1.10
    assert item["converted_unit_price"] == 4400.00
    assert item["packing_charge_unit"] == 55.00
    assert item["landed_cost_unit"] == 4455.00
    assert item["margin_percent"] == 15.0
    assert item["final_unit_selling_price"] == 5241.18
    assert item["final_total_selling_price"] == round(5241.18 * 2, 2)
    assert data["summary"]["target_currency"] == "USD"


def test_currency_conversion_eur_to_eur():
    """Verify EUR -> EUR conversion uses FX rate 1.0."""
    quote = SupplierQuotationData(
        supplier_name="DMN Test",
        quote_number="EUR-001",
        currency="EUR",
        items=[
            SupplierQuoteItem(
                line_number=1,
                part_number="TEST-EUR",
                description="EUR Test Item",
                quantity=1.0,
                unit="NOS",
                currency="EUR",
                unit_price=100.0,
                discount=0.0,
                packing_charges=0.0,
                total=100.0,
            )
        ]
    )
    req = SupplierPricingCalculationRequest(
        quotation=quote,
        config=PricingConfigParameters(
            exchange_rate=1.0,
            target_currency="EUR",
            default_margin_percent=10.0,
            margin_method="margin_on_selling",
        )
    )
    res = supplier_pricing_service.calculate_pricing(req)
    assert res.success is True
    item = res.items[0]
    assert item.exchange_rate == 1.0
    assert item.converted_unit_price == 100.0
    assert item.landed_cost_unit == 100.0
    # 100 / 0.9 = 111.11
    assert item.final_unit_selling_price == 111.11


def test_currency_conversion_eur_to_idr_exact_spec_and_recalculation():
    """Verify EUR -> IDR at 17,500 matches spec: EUR 634.86 * 17,500 = IDR 11,110,050.
    Also verify dynamic FX rate change recalculates all pricing steps.
    """
    # Specific test requirement from user:
    # EUR 634.86 x 17,500 = IDR 11,110,050.
    quote = SupplierQuotationData(
        supplier_name="DMN Test",
        quote_number="DMN-IDR-TEST",
        currency="EUR",
        freight_charges=40.0,  # 40 EUR freight
        items=[
            SupplierQuoteItem(
                line_number=1,
                part_number="SPEC-VALVE-01",
                description="Precision Valve Specification Item",
                quantity=1.0,
                unit="NOS",
                currency="EUR",
                unit_price=634.86,
                discount=0.0,
                packing_charges=10.0,  # 10 EUR packing
                total=634.86,
            )
        ]
    )

    # 1. Calculate at FX 17,500
    req_17500 = SupplierPricingCalculationRequest(
        quotation=quote,
        config=PricingConfigParameters(
            exchange_rate=17500.0,
            target_currency="IDR",
            default_margin_percent=10.0,
            margin_method="margin_on_selling",
            freight_total=40.0,  # 40 EUR
            customs_duty_percent=5.0,  # 5% tariff
            local_handling_charge=50000.0,  # 50,000 IDR local handling
        )
    )

    res_17500 = supplier_pricing_service.calculate_pricing(req_17500)
    assert res_17500.success is True
    item = res_17500.items[0]

    # Required formula verification: 634.86 * 17500 = 11110050.00
    assert item.supplier_unit_price == 634.86
    assert item.net_supplier_unit_price == 634.86
    assert item.exchange_rate == 17500.0
    assert item.converted_unit_price == 11110050.0
    assert item.converted_net_total == 11110050.0

    # Packing converted: 10 EUR * 17500 = 175,000 IDR
    assert item.packing_charge_unit == 175000.0

    # Freight converted: 40 EUR * 17500 = 700,000 IDR
    assert item.freight_charge_unit == 700000.0

    # Customs: (11,110,050 + 175,000) * 0.05 = 564,252.50 IDR
    assert item.customs_duty_unit == 564252.5

    # Local handling: 50,000 IDR
    assert item.local_handling_unit == 50000.0

    # Total landed cost: 11,110,050 + 175,000 + 700,000 + 564,252.50 + 50,000 = 12,599,302.50 IDR
    expected_landed = 11110050.0 + 175000.0 + 700000.0 + 564252.5 + 50000.0
    assert item.landed_cost_unit == expected_landed

    # Final selling price at 10% margin on selling: landed / 0.90
    expected_selling = round(expected_landed / 0.90, 2)
    assert item.final_unit_selling_price == expected_selling
    assert item.final_total_selling_price == expected_selling

    # Summary checks in target currency (IDR)
    assert res_17500.summary.target_currency == "IDR"
    assert res_17500.summary.total_supplier_net == 634.86  # supplier currency
    assert res_17500.summary.total_supplier_net_converted == 11110050.0  # target currency
    assert res_17500.summary.total_selling_price == expected_selling
    assert res_17500.summary.overall_margin_percent == 10.0

    # 2. Verify changing FX rate (e.g. from 17,500 to 18,000) recalculates all pricing immediately
    req_18000 = SupplierPricingCalculationRequest(
        quotation=quote,
        config=PricingConfigParameters(
            exchange_rate=18000.0,
            target_currency="IDR",
            default_margin_percent=10.0,
            margin_method="margin_on_selling",
            freight_total=40.0,
            customs_duty_percent=5.0,
            local_handling_charge=50000.0,
        )
    )
    res_18000 = supplier_pricing_service.calculate_pricing(req_18000)
    item_18000 = res_18000.items[0]
    expected_converted_18000 = round(634.86 * 18000.0, 2)
    assert item_18000.converted_unit_price == expected_converted_18000
    # Must be higher than the 17,500 calculation because FX increased
    assert item_18000.final_unit_selling_price > item.final_unit_selling_price
    assert item_18000.landed_cost_unit > item.landed_cost_unit


def test_procurement_approval_api_workflow():
    """Verify Stage 3 Procurement Approval submission for Pending, Approved, and Rejected statuses."""
    # Test Approved
    payload_approve = {
        "quote_number": "41260509",
        "supplier_name": "DMN Westinghouse",
        "total_selling_price": 350000000.0,
        "currency": "IDR",
        "effective_margin_percent": 12.5,
        "status": "approved",
        "approver_name": "Chief Procurement Officer",
        "approval_notes": "Approved with negotiated 12.5% gross margin."
    }
    res = client.post("/api/supplier-pricing/approval", json=payload_approve)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["status"] == "approved"
    assert "APPROVED by Chief Procurement Officer" in data["message"]
    assert data["decision_timestamp"] is not None

    # Test Rejected
    payload_reject = {
        "quote_number": "41260509",
        "supplier_name": "DMN Westinghouse",
        "total_selling_price": 350000000.0,
        "currency": "IDR",
        "effective_margin_percent": 5.0,
        "status": "rejected",
        "approver_name": "Procurement Lead",
        "approval_notes": "Margin below minimum 10% threshold."
    }
    res_rej = client.post("/api/supplier-pricing/approval", json=payload_reject)
    assert res_rej.status_code == 200
    data_rej = res_rej.json()
    assert data_rej["status"] == "rejected"
    assert "REJECTED by Procurement Lead" in data_rej["message"]


def test_zoho_books_preview_and_confirmed_sync_guardrail(monkeypatch):
    """Verify Stage 4 Zoho Books preview classifies SKUs and never silently syncs without user confirmation."""
    from app.services.zoho_books_service import zoho_books_service

    monkeypatch.setattr(zoho_books_service.token_manager, "get_valid_access_token", lambda: "mock_token")

    # Mock real Zoho Books API item search
    class MockZohoSearchResp:
        status_code = 200
        def json(self):
            return {
                "code": 0,
                "message": "success",
                "items": [
                    {
                        "item_id": "2552396000020392002",
                        "sku": "TEST-AUTOMATION-NATIVE-001",
                        "name": "QuotexAI Native Update Test",
                        "rate": 1250.0,
                    }
                ]
            }

    import httpx
    orig_get = httpx.Client.get
    def mock_get(self, url, *args, **kwargs):
        if "zohoapis" in str(url):
            params = kwargs.get("params", {})
            search_text = params.get("search_text", "")
            if search_text == "TEST-AUTOMATION-NATIVE-001":
                return MockZohoSearchResp()
            return MockZohoSearchResp() if False else type("EmptyResp", (), {"status_code": 200, "json": lambda: {"code": 0, "message": "success", "items": []}})()
        return orig_get(self, url, *args, **kwargs)

    monkeypatch.setattr(httpx.Client, "get", mock_get)

    monkeypatch.setattr(
        zoho_books_service,
        "create_item",
        lambda payload, organization_id=None: {
            "code": 0,
            "message": "Item created successfully.",
            "item": {
                "item_id": "2552396000099999001",
                "name": payload.get("name"),
                "sku": payload.get("sku"),
                "rate": payload.get("rate"),
            }
        }
    )
    monkeypatch.setattr(
        zoho_books_service,
        "update_item",
        lambda item_id, payload, organization_id=None: {
            "code": 0,
            "message": "Item updated successfully.",
            "item": {
                "item_id": item_id,
                "name": payload.get("name"),
                "sku": payload.get("sku"),
                "rate": payload.get("rate"),
            }
        }
    )
    monkeypatch.setattr(
        zoho_books_service,
        "get_item",
        lambda item_id, organization_id=None: {
            "code": 0,
            "message": "success",
            "item": {
                "item_id": item_id,
                "name": "QuotexAI Native Update Test",
                "sku": "TEST-AUTOMATION-NATIVE-001",
            }
        }
    )

    preview_payload = {
        "quotation": {
            "supplier_name": "DMN Westinghouse",
            "quote_number": "41260509",
            "currency": "EUR",
            "items": [
                {
                    "line_number": 1,
                    "part_number": "TEST-AUTOMATION-NATIVE-001",  # Known in Zoho Books -> should be UPDATE
                    "description": "QuotexAI Native Update Test",
                    "quantity": 1.0,
                    "unit": "NOS",
                    "currency": "EUR",
                    "unit_price": 10923.0,
                    "discount": 30.0,
                    "total": 7646.10,
                },
                {
                    "line_number": 2,
                    "part_number": "NEW-VALVE-999",  # Not in Zoho Books -> should be CREATE
                    "description": "Brand New Valve",
                    "quantity": 2.0,
                    "unit": "NOS",
                    "currency": "EUR",
                    "unit_price": 5000.0,
                    "discount": 0.0,
                    "total": 10000.0,
                }
            ]
        },
        "pricing_summary": {
            "total_supplier_net": 17646.10,
            "total_landed_cost": 20000.0,
            "total_selling_price": 22222.0,
            "total_gross_profit": 2222.0,
            "overall_margin_percent": 10.0,
            "supplier_currency": "EUR",
            "target_currency": "EUR",
            "items_count": 2
        },
        "calculated_items": [
            {
                "line_number": 1,
                "part_number": "TEST-AUTOMATION-NATIVE-001",
                "description": "QuotexAI Native Update Test",
                "quantity": 1.0,
                "unit": "NOS",
                "supplier_currency": "EUR",
                "target_currency": "EUR",
                "supplier_unit_price": 10923.0,
                "discount_percent": 30.0,
                "discount_amount_unit": 3276.90,
                "net_supplier_unit_price": 7646.10,
                "net_supplier_total": 7646.10,
                "exchange_rate": 1.0,
                "converted_unit_price": 7646.10,
                "converted_net_total": 7646.10,
                "packing_charge_unit": 0.0,
                "freight_charge_unit": 0.0,
                "customs_duty_unit": 0.0,
                "local_handling_unit": 0.0,
                "landed_cost_unit": 7646.10,
                "landed_cost_total": 7646.10,
                "margin_percent": 10.0,
                "margin_method": "margin_on_selling",
                "margin_amount_unit": 849.57,
                "final_unit_selling_price": 8495.67,
                "final_total_selling_price": 8495.67,
                "profit_total": 849.57,
            },
            {
                "line_number": 2,
                "part_number": "NEW-VALVE-999",
                "description": "Brand New Valve",
                "quantity": 2.0,
                "unit": "NOS",
                "supplier_currency": "EUR",
                "target_currency": "EUR",
                "supplier_unit_price": 5000.0,
                "discount_percent": 0.0,
                "discount_amount_unit": 0.0,
                "net_supplier_unit_price": 5000.0,
                "net_supplier_total": 10000.0,
                "exchange_rate": 1.0,
                "converted_unit_price": 5000.0,
                "converted_net_total": 10000.0,
                "packing_charge_unit": 0.0,
                "freight_charge_unit": 0.0,
                "customs_duty_unit": 0.0,
                "local_handling_unit": 0.0,
                "landed_cost_unit": 5000.0,
                "landed_cost_total": 10000.0,
                "margin_percent": 10.0,
                "margin_method": "margin_on_selling",
                "margin_amount_unit": 555.56,
                "final_unit_selling_price": 5555.56,
                "final_total_selling_price": 11111.12,
                "profit_total": 1111.12,
            }
        ],
        "zoho_config": {
            "organization_id": "741367552",
            "environment": "production",
            "sync_mode": "items_only"
        }
    }

    # 1. Test preview
    prev_res = client.post("/api/supplier-pricing/zoho-preview", json=preview_payload)
    assert prev_res.status_code == 200
    prev_data = prev_res.json()
    assert prev_data["success"] is True
    assert prev_data["requires_user_confirmation"] is True
    assert len(prev_data["items_to_update"]) == 1
    assert prev_data["items_to_update"][0]["part_number"] == "TEST-AUTOMATION-NATIVE-001"
    assert prev_data["items_to_update"][0]["action"] == "UPDATE"
    assert prev_data["items_to_update"][0]["existing_item_id"] == "2552396000020392002"
    assert prev_data["items_to_update"][0]["existing_item_id"].isdigit()
    assert len(prev_data["items_to_create"]) == 1
    assert prev_data["items_to_create"][0]["part_number"] == "NEW-VALVE-999"
    assert prev_data["items_to_create"][0]["action"] == "CREATE"
    assert prev_data["items_to_create"][0]["existing_item_id"] is None

    # 2. Test Guardrail: Execute sync without user_confirmed must fail
    items_to_sync = prev_data["items_to_update"] + prev_data["items_to_create"]
    unconfirmed_payload = {
        "zoho_config": prev_data["zoho_config"],
        "items": items_to_sync,
        "user_confirmed": False,  # Not confirmed!
        "confirmed_by_user": None
    }
    unconf_res = client.post("/api/supplier-pricing/zoho-sync", json=unconfirmed_payload)
    assert unconf_res.status_code == 400
    assert "User confirmation required" in unconf_res.json()["detail"]

    # 3. Test execution with explicit user confirmation
    confirmed_payload = {
        "zoho_config": prev_data["zoho_config"],
        "items": items_to_sync,
        "user_confirmed": True,
        "confirmed_by_user": "John Doe (Lead Procurement)"
    }
    conf_res = client.post("/api/supplier-pricing/zoho-sync", json=confirmed_payload)
    assert conf_res.status_code == 200
    conf_data = conf_res.json()
    assert conf_data["success"] is True
    assert conf_data["created_count"] == 1
    assert conf_data["updated_count"] == 1
    assert len(conf_data["audit_log"]) >= 3


def test_zoho_books_read_only_connectivity_and_search():
    """Verify read-only Zoho Books connectivity test targeting TEST-AUTOMATION-001 (Item ID: 2552396000020372001)."""
    # 1. Test connectivity endpoint
    res = client.get("/api/supplier-pricing/zoho/test-connection")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["tested_sku"] == "TEST-AUTOMATION-001"
    assert data["expected_item_id"] == "2552396000020372001"
    assert data["matched_item_id"] == "2552396000020372001"
    assert data["is_match"] is True
    assert data["organization_id"] == "741367552"
    # Ensure no secrets or tokens are exposed
    assert "access_token" not in str(data)
    assert "refresh_token" not in str(data)
    assert "client_secret" not in str(data)

    # 2. Test search items endpoint with organization_id and search_text
    search_res = client.get("/api/supplier-pricing/zoho/items/search?search_text=TEST-AUTOMATION-001&organization_id=741367552")
    assert search_res.status_code == 200
    search_data = search_res.json()
    assert search_data["success"] is True
    assert search_data["count"] >= 1
    found_item = search_data["items"][0]
    assert found_item["sku"] == "TEST-AUTOMATION-001"
    assert found_item["item_id"] == "2552396000020372001"


def test_zoho_oauth_token_exchange_and_auto_refresh(monkeypatch):
    """Verify OAuth authorization_code exchange and refresh_token flow without leaking secrets."""
    from app.services.zoho_books_service import ZohoTokenManager
    import httpx

    # Create isolated token manager
    tm = ZohoTokenManager()
    tm.persist_tokens = False
    tm.client_id = "test_client_id_123"
    tm.client_secret = "test_client_secret_xyz"
    tm.grant_token = "test_grant_code_abc"

    # Mock authorization_code exchange
    class MockResponseAuth:
        status_code = 200
        def json(self):
            return {
                "access_token": "mock_zoho_access_token_111",
                "refresh_token": "mock_zoho_refresh_token_222",
                "api_domain": "https://www.zohoapis.com",
                "expires_in": 3600
            }

    class MockResponseRefresh:
        status_code = 200
        def json(self):
            return {
                "access_token": "mock_zoho_access_token_refreshed_333",
                "expires_in": 3600
            }

    # Test grant token exchange
    monkeypatch.setattr(httpx.Client, "post", lambda self, url, data: MockResponseAuth())
    exchange_res = tm.exchange_grant_token(code="test_grant_code_abc")
    assert exchange_res["success"] is True
    assert exchange_res["has_refresh_token"] is True
    assert tm._access_token == "mock_zoho_access_token_111"
    assert tm._refresh_token == "mock_zoho_refresh_token_222"

    # Test automatic refresh
    monkeypatch.setattr(httpx.Client, "post", lambda self, url, data: MockResponseRefresh())
    refresh_res = tm.refresh_access_token()
    assert refresh_res["success"] is True
    assert tm._access_token == "mock_zoho_access_token_refreshed_333"

    # Check status summary does NOT expose raw token values
    summary = tm.get_status_summary()
    assert summary["is_authenticated"] is True
    assert summary["has_refresh_flow"] is True
    assert "mock_zoho_access_token" not in str(summary)
    assert "mock_zoho_refresh_token" not in str(summary)


def test_strict_live_connectivity_structure(monkeypatch):
    """Verify strict live connectivity endpoint returns exact structure and never leaks tokens."""
    import httpx
    from app.services.zoho_books_service import zoho_books_service

    # Mock token manager valid access token
    monkeypatch.setattr(zoho_books_service.token_manager, "get_valid_access_token", lambda: "mock_test_token_live")
    zoho_books_service.token_manager._expires_at = 9999999999.0

    class MockLiveZohoResp:
        status_code = 200
        def json(self):
            return {
                "code": 0,
                "message": "success",
                "items": [
                    {
                        "item_id": "2552396000020372001",
                        "sku": "TEST-AUTOMATION-001",
                        "name": "TEST-AUTOMATION-001",
                        "rate": 7500.0,
                    }
                ]
            }

    orig_get = httpx.Client.get
    def mock_get(self, url, *args, **kwargs):
        if "zohoapis" in str(url):
            return MockLiveZohoResp()
        return orig_get(self, url, *args, **kwargs)

    monkeypatch.setattr(httpx.Client, "get", mock_get)

    res = client.get("/api/supplier-pricing/zoho/live-connectivity-test")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["real_zoho_api_request"] == "PASS"
    assert data["real_oauth_token"] == "PASS"
    assert data["real_sku_search"] == "PASS"
    assert data["fallback_mock_used"] == "NO"
    assert data["matched_sku"] == "TEST-AUTOMATION-001"
    assert data["matched_item_id"] == "2552396000020372001"
    assert data["http_status"] == 200
    assert data["zoho_code"] == 0
    # Strict secret protection
    assert "mock_test_token_live" not in str(data)
    assert "Authorization" not in str(data)


def test_stage_4_req_9a_sku_exists_in_real_zoho_update_with_numeric_id(monkeypatch):
    """Requirement 9A: SKU exists in real Zoho response -> UPDATE preview with real numeric item_id."""
    import httpx
    from app.services.zoho_books_service import zoho_books_service

    monkeypatch.setattr(zoho_books_service.token_manager, "get_valid_access_token", lambda: "mock_token")

    class MockZohoFoundResp:
        status_code = 200
        def json(self):
            return {
                "code": 0,
                "message": "success",
                "items": [
                    {
                        "item_id": "2552396000020392002",
                        "sku": "TEST-AUTOMATION-NATIVE-001",
                        "name": "QuotexAI Native Update Test",
                        "rate": 1250.0,
                    }
                ]
            }

    monkeypatch.setattr(httpx.Client, "get", lambda self, url, *args, **kwargs: MockZohoFoundResp())

    payload = {
        "quotation": {
            "supplier_name": "DMN",
            "quote_number": "Q-001",
            "currency": "EUR",
            "items": [
                {
                    "line_number": 1,
                    "part_number": "TEST-AUTOMATION-NATIVE-001",
                    "description": "QuotexAI Native Update Test",
                    "quantity": 1.0,
                    "unit": "NOS",
                    "currency": "EUR",
                    "unit_price": 1000.0,
                    "discount": 0.0,
                    "total": 1000.0,
                }
            ]
        },
        "pricing_summary": {
            "total_supplier_net": 1000.0,
            "total_landed_cost": 1000.0,
            "total_selling_price": 1250.0,
            "total_gross_profit": 250.0,
            "overall_margin_percent": 20.0,
            "supplier_currency": "EUR",
            "target_currency": "EUR",
            "items_count": 1,
        },
        "calculated_items": [
            {
                "line_number": 1,
                "part_number": "TEST-AUTOMATION-NATIVE-001",
                "description": "QuotexAI Native Update Test",
                "quantity": 1.0,
                "unit": "NOS",
                "supplier_currency": "EUR",
                "target_currency": "EUR",
                "supplier_unit_price": 1000.0,
                "discount_percent": 0.0,
                "discount_amount_unit": 0.0,
                "net_supplier_unit_price": 1000.0,
                "net_supplier_total": 1000.0,
                "exchange_rate": 1.0,
                "converted_unit_price": 1000.0,
                "converted_net_total": 1000.0,
                "packing_charge_unit": 0.0,
                "freight_charge_unit": 0.0,
                "customs_duty_unit": 0.0,
                "local_handling_unit": 0.0,
                "landed_cost_unit": 1000.0,
                "landed_cost_total": 1000.0,
                "margin_percent": 20.0,
                "margin_method": "margin_on_selling",
                "margin_amount_unit": 250.0,
                "final_unit_selling_price": 1250.0,
                "final_total_selling_price": 1250.0,
                "profit_total": 250.0,
            }
        ],
        "zoho_config": {
            "organization_id": "741367552",
            "environment": "production",
            "sync_mode": "items_only"
        }
    }

    res = client.post("/api/supplier-pricing/zoho-preview", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert len(data["items_to_update"]) == 1
    assert len(data["items_to_create"]) == 0
    rec = data["items_to_update"][0]
    assert rec["part_number"] == "TEST-AUTOMATION-NATIVE-001"
    assert rec["action"] == "UPDATE"
    assert rec["existing_item_id"] == "2552396000020392002"
    assert rec["existing_item_id"].isdigit()


def test_stage_4_req_9b_sku_not_found_causes_create_preview(monkeypatch):
    """Requirement 9B: SKU does not exist in Zoho Books (e.g. RV BL 200 4TS) -> CREATE preview."""
    import httpx
    from app.services.zoho_books_service import zoho_books_service

    monkeypatch.setattr(zoho_books_service.token_manager, "get_valid_access_token", lambda: "mock_token")

    class MockZohoNotFoundResp:
        status_code = 200
        def json(self):
            return {
                "code": 0,
                "message": "success",
                "items": []
            }

    monkeypatch.setattr(httpx.Client, "get", lambda self, url, *args, **kwargs: MockZohoNotFoundResp())

    payload = {
        "quotation": {
            "supplier_name": "DMN",
            "quote_number": "Q-002",
            "currency": "EUR",
            "items": [
                {
                    "line_number": 1,
                    "part_number": "RV BL 200 4TS",
                    "description": "BL 200 4TS : BL - Rotary valve",
                    "quantity": 1.0,
                    "unit": "NOS",
                    "currency": "EUR",
                    "unit_price": 7646.10,
                    "discount": 0.0,
                    "total": 7646.10,
                }
            ]
        },
        "pricing_summary": {
            "total_supplier_net": 7646.10,
            "total_landed_cost": 7646.10,
            "total_selling_price": 8495.67,
            "total_gross_profit": 849.57,
            "overall_margin_percent": 10.0,
            "supplier_currency": "EUR",
            "target_currency": "EUR",
            "items_count": 1,
        },
        "calculated_items": [
            {
                "line_number": 1,
                "part_number": "RV BL 200 4TS",
                "description": "BL 200 4TS : BL - Rotary valve",
                "quantity": 1.0,
                "unit": "NOS",
                "supplier_currency": "EUR",
                "target_currency": "EUR",
                "supplier_unit_price": 7646.10,
                "discount_percent": 0.0,
                "discount_amount_unit": 0.0,
                "net_supplier_unit_price": 7646.10,
                "net_supplier_total": 7646.10,
                "exchange_rate": 1.0,
                "converted_unit_price": 7646.10,
                "converted_net_total": 7646.10,
                "packing_charge_unit": 0.0,
                "freight_charge_unit": 0.0,
                "customs_duty_unit": 0.0,
                "local_handling_unit": 0.0,
                "landed_cost_unit": 7646.10,
                "landed_cost_total": 7646.10,
                "margin_percent": 10.0,
                "margin_method": "margin_on_selling",
                "margin_amount_unit": 849.57,
                "final_unit_selling_price": 8495.67,
                "final_total_selling_price": 8495.67,
                "profit_total": 849.57,
            }
        ],
        "zoho_config": {
            "organization_id": "741367552",
            "environment": "production",
            "sync_mode": "items_only"
        }
    }

    res = client.post("/api/supplier-pricing/zoho-preview", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert len(data["items_to_update"]) == 0
    assert len(data["items_to_create"]) == 1
    rec = data["items_to_create"][0]
    assert rec["part_number"] == "RV BL 200 4TS"
    assert rec["action"] == "CREATE"
    assert rec["existing_item_id"] is None


def test_stage_4_req_9c_fake_catalog_entry_must_not_cause_update(monkeypatch):
    """Requirement 9C: Fake or local catalog entry (e.g. ZB-ITEM-10089) must NOT cause UPDATE and is blocked on sync."""
    import httpx
    from app.services.zoho_books_service import zoho_books_service

    monkeypatch.setattr(zoho_books_service.token_manager, "get_valid_access_token", lambda: "mock_token")

    # API returns empty list
    class MockZohoEmpty:
        status_code = 200
        def json(self):
            return {"code": 0, "message": "success", "items": []}

    monkeypatch.setattr(httpx.Client, "get", lambda self, url, *args, **kwargs: MockZohoEmpty())

    payload = {
        "quotation": {
            "supplier_name": "DMN",
            "quote_number": "Q-003",
            "currency": "EUR",
            "items": [
                {
                    "line_number": 1,
                    "part_number": "RV BL 200 4TS",  # Old fake ID was ZB-ITEM-10089
                    "description": "BL 200 4TS : BL - Rotary valve",
                    "quantity": 1.0,
                    "unit": "NOS",
                    "currency": "EUR",
                    "unit_price": 1000.0,
                    "discount": 0.0,
                    "total": 1000.0,
                },
                {
                    "line_number": 2,
                    "part_number": "00138737",  # Old fake ID was ZB-ITEM-10023
                    "description": "Sample part 2",
                    "quantity": 1.0,
                    "unit": "NOS",
                    "currency": "EUR",
                    "unit_price": 2000.0,
                    "discount": 0.0,
                    "total": 2000.0,
                }
            ]
        },
        "pricing_summary": {
            "total_supplier_net": 3000.0,
            "total_landed_cost": 3000.0,
            "total_selling_price": 3500.0,
            "total_gross_profit": 500.0,
            "overall_margin_percent": 14.28,
            "supplier_currency": "EUR",
            "target_currency": "EUR",
            "items_count": 2,
        },
        "calculated_items": [
            {
                "line_number": 1,
                "part_number": "RV BL 200 4TS",
                "description": "BL 200 4TS : BL - Rotary valve",
                "quantity": 1.0,
                "unit": "NOS",
                "supplier_currency": "EUR",
                "target_currency": "EUR",
                "supplier_unit_price": 1000.0,
                "discount_percent": 0.0,
                "discount_amount_unit": 0.0,
                "net_supplier_unit_price": 1000.0,
                "net_supplier_total": 1000.0,
                "exchange_rate": 1.0,
                "converted_unit_price": 1000.0,
                "converted_net_total": 1000.0,
                "packing_charge_unit": 0.0,
                "freight_charge_unit": 0.0,
                "customs_duty_unit": 0.0,
                "local_handling_unit": 0.0,
                "landed_cost_unit": 1000.0,
                "landed_cost_total": 1000.0,
                "margin_percent": 10.0,
                "margin_method": "margin_on_selling",
                "margin_amount_unit": 111.11,
                "final_unit_selling_price": 1111.11,
                "final_total_selling_price": 1111.11,
                "profit_total": 111.11,
            },
            {
                "line_number": 2,
                "part_number": "00138737",
                "description": "Sample part 2",
                "quantity": 1.0,
                "unit": "NOS",
                "supplier_currency": "EUR",
                "target_currency": "EUR",
                "supplier_unit_price": 2000.0,
                "discount_percent": 0.0,
                "discount_amount_unit": 0.0,
                "net_supplier_unit_price": 2000.0,
                "net_supplier_total": 2000.0,
                "exchange_rate": 1.0,
                "converted_unit_price": 2000.0,
                "converted_net_total": 2000.0,
                "packing_charge_unit": 0.0,
                "freight_charge_unit": 0.0,
                "customs_duty_unit": 0.0,
                "local_handling_unit": 0.0,
                "landed_cost_unit": 2000.0,
                "landed_cost_total": 2000.0,
                "margin_percent": 10.0,
                "margin_method": "margin_on_selling",
                "margin_amount_unit": 222.22,
                "final_unit_selling_price": 2222.22,
                "final_total_selling_price": 2222.22,
                "profit_total": 222.22,
            }
        ],
        "zoho_config": {
            "organization_id": "741367552",
            "environment": "production",
            "sync_mode": "items_only"
        }
    }

    res = client.post("/api/supplier-pricing/zoho-preview", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert len(data["items_to_update"]) == 0
    assert len(data["items_to_create"]) == 2
    assert "ZB-ITEM-10089" not in str(data)
    assert "ZB-ITEM-10023" not in str(data)

    # Verify that attempting to sync with fake non-numeric ID is rejected
    fake_sync_payload = {
        "zoho_config": {"organization_id": "741367552", "environment": "production", "sync_mode": "items_only"},
        "items": [
            {
                "part_number": "RV BL 200 4TS",
                "description": "BL 200 4TS : BL - Rotary valve",
                "rate": 8495.67,
                "purchase_rate": 7646.10,
                "currency": "EUR",
                "unit": "NOS",
                "action": "UPDATE",
                "existing_item_id": "ZB-ITEM-10089",
                "status": "ready"
            }
        ],
        "user_confirmed": True,
        "confirmed_by_user": "Lead Auditor"
    }
    sync_res = client.post("/api/supplier-pricing/zoho-sync", json=fake_sync_payload)
    assert sync_res.status_code == 400
    assert "Non-numeric Zoho Item ID" in sync_res.json()["detail"]


def test_stage_4_req_9d_description_match_without_exact_sku_must_not_update(monkeypatch):
    """Requirement 9D: Description match without exact SKU must NOT cause UPDATE."""
    import httpx
    from app.services.zoho_books_service import zoho_books_service

    monkeypatch.setattr(zoho_books_service.token_manager, "get_valid_access_token", lambda: "mock_token")

    # Item in Zoho has matching description text but DIFFERENT SKU
    class MockZohoDescOnlyResp:
        status_code = 200
        def json(self):
            return {
                "code": 0,
                "message": "success",
                "items": [
                    {
                        "item_id": "2552396000020379999",
                        "sku": "OTHER-VALVE-SKU",
                        "name": "Different Rotary Valve",
                        "description": "BL 200 4TS : BL - Rotary valve",
                        "rate": 5000.0,
                    }
                ]
            }

    monkeypatch.setattr(httpx.Client, "get", lambda self, url, *args, **kwargs: MockZohoDescOnlyResp())

    payload = {
        "quotation": {
            "supplier_name": "DMN",
            "quote_number": "Q-004",
            "currency": "EUR",
            "items": [
                {
                    "line_number": 1,
                    "part_number": "RV BL 200 4TS",
                    "description": "BL 200 4TS : BL - Rotary valve",
                    "quantity": 1.0,
                    "unit": "NOS",
                    "currency": "EUR",
                    "unit_price": 7646.10,
                    "discount": 0.0,
                    "total": 7646.10,
                }
            ]
        },
        "pricing_summary": {
            "total_supplier_net": 7646.10,
            "total_landed_cost": 7646.10,
            "total_selling_price": 8495.67,
            "total_gross_profit": 849.57,
            "overall_margin_percent": 10.0,
            "supplier_currency": "EUR",
            "target_currency": "EUR",
            "items_count": 1,
        },
        "calculated_items": [
            {
                "line_number": 1,
                "part_number": "RV BL 200 4TS",
                "description": "BL 200 4TS : BL - Rotary valve",
                "quantity": 1.0,
                "unit": "NOS",
                "supplier_currency": "EUR",
                "target_currency": "EUR",
                "supplier_unit_price": 7646.10,
                "discount_percent": 0.0,
                "discount_amount_unit": 0.0,
                "net_supplier_unit_price": 7646.10,
                "net_supplier_total": 7646.10,
                "exchange_rate": 1.0,
                "converted_unit_price": 7646.10,
                "converted_net_total": 7646.10,
                "packing_charge_unit": 0.0,
                "freight_charge_unit": 0.0,
                "customs_duty_unit": 0.0,
                "local_handling_unit": 0.0,
                "landed_cost_unit": 7646.10,
                "landed_cost_total": 7646.10,
                "margin_percent": 10.0,
                "margin_method": "margin_on_selling",
                "margin_amount_unit": 849.57,
                "final_unit_selling_price": 8495.67,
                "final_total_selling_price": 8495.67,
                "profit_total": 849.57,
            }
        ],
        "zoho_config": {
            "organization_id": "741367552",
            "environment": "production",
            "sync_mode": "items_only"
        }
    }

    res = client.post("/api/supplier-pricing/zoho-preview", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert len(data["items_to_update"]) == 0
    assert len(data["items_to_create"]) == 1
    assert data["items_to_create"][0]["part_number"] == "RV BL 200 4TS"
    assert data["items_to_create"][0]["action"] == "CREATE"


def test_stage_4_sync_req_9a_9b_9g_create_calls_service_stores_numeric_id(monkeypatch):
    """Requirements 9A, 9B, 9G: CREATE calls zoho_books_service.create_item(), stores numeric item_id, no fake ZB-NEW- IDs."""
    from app.services.zoho_books_service import zoho_books_service

    captured_create_payloads = []

    def mock_create_item(payload, organization_id=None):
        captured_create_payloads.append(payload)
        return {
            "code": 0,
            "message": "Item created successfully.",
            "item": {
                "item_id": "2552396000030010001",
                "name": payload.get("name"),
                "sku": payload.get("sku"),
                "rate": payload.get("rate"),
            }
        }

    monkeypatch.setattr(zoho_books_service, "create_item", mock_create_item)

    sync_payload = {
        "zoho_config": {"organization_id": "741367552", "environment": "production", "sync_mode": "items_only"},
        "items": [
            {
                "part_number": "RV BL 200 4TS",
                "description": "BL 200 4TS : BL - Rotary valve",
                "rate": 8495.67,
                "purchase_rate": 7646.10,
                "currency": "EUR",
                "unit": "NOS",
                "action": "CREATE",
                "existing_item_id": None,
                "status": "ready"
            }
        ],
        "user_confirmed": True,
        "confirmed_by_user": "Procurement Lead"
    }

    res = client.post("/api/supplier-pricing/zoho-sync", json=sync_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["created_count"] == 1
    assert data["updated_count"] == 0

    # 9A: create_item() called
    assert len(captured_create_payloads) == 1
    assert captured_create_payloads[0]["sku"] == "RV BL 200 4TS"

    # 9B: real numeric item_id stored
    rec = data["records"][0]
    assert rec["status"] == "synced"
    assert rec["existing_item_id"] == "2552396000030010001"
    assert rec["existing_item_id"].isdigit()

    # 9G: no fake ZB-NEW- IDs
    assert "ZB-NEW-" not in str(data)
    assert any("ID: 2552396000030010001" in log for log in data["audit_log"])


def test_stage_4_sync_req_9c_9d_update_calls_service_uses_existing_id(monkeypatch):
    """Requirements 9C, 9D: UPDATE calls zoho_books_service.update_item(), uses existing real numeric ID, preserves SKU."""
    from app.services.zoho_books_service import zoho_books_service

    captured_updates = []

    def mock_get_item(item_id, organization_id=None):
        return {
            "code": 0,
            "message": "success",
            "item": {
                "item_id": item_id,
                "name": "QuotexAI Native Update Test",
                "sku": "TEST-AUTOMATION-NATIVE-001",
                "rate": 1000.0,
            }
        }

    def mock_update_item(item_id, payload, organization_id=None):
        captured_updates.append({"item_id": item_id, "payload": payload})
        return {
            "code": 0,
            "message": "Item updated successfully.",
            "item": {
                "item_id": item_id,
                "name": payload.get("name"),
                "sku": payload.get("sku"),
                "rate": payload.get("rate"),
            }
        }

    monkeypatch.setattr(zoho_books_service, "get_item", mock_get_item)
    monkeypatch.setattr(zoho_books_service, "update_item", mock_update_item)

    sync_payload = {
        "zoho_config": {"organization_id": "741367552", "environment": "production", "sync_mode": "items_only"},
        "items": [
            {
                "part_number": "TEST-AUTOMATION-NATIVE-001",
                "description": "QuotexAI Native Update Test",
                "rate": 1250.0,
                "purchase_rate": 1000.0,
                "currency": "EUR",
                "unit": "NOS",
                "action": "UPDATE",
                "existing_item_id": "2552396000020392002",
                "status": "ready"
            }
        ],
        "user_confirmed": True,
        "confirmed_by_user": "Procurement Lead"
    }

    res = client.post("/api/supplier-pricing/zoho-sync", json=sync_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["updated_count"] == 1
    assert data["created_count"] == 0

    # 9C: update_item() called
    assert len(captured_updates) == 1
    call = captured_updates[0]

    # 9D: uses real existing_item_id and preserves SKU
    assert call["item_id"] == "2552396000020392002"
    assert call["payload"]["sku"] == "TEST-AUTOMATION-NATIVE-001"
    assert call["payload"]["rate"] == 1250.0

    rec = data["records"][0]
    assert rec["status"] == "synced"
    assert rec["existing_item_id"] == "2552396000020392002"
    assert any("UPDATE SUCCESS" in log and "ID: 2552396000020392002" in log for log in data["audit_log"])


def test_stage_4_sync_req_9e_create_failure_reported_as_failed(monkeypatch):
    """Requirement 9E: Zoho CREATE failure is reported as FAILED, never reporting false SUCCESS."""
    from app.services.zoho_books_service import zoho_books_service

    def mock_create_fail(payload, organization_id=None):
        return {
            "code": 3001,
            "message": "Duplicate SKU not allowed in organization.",
        }

    monkeypatch.setattr(zoho_books_service, "create_item", mock_create_fail)

    sync_payload = {
        "zoho_config": {"organization_id": "741367552", "environment": "production", "sync_mode": "items_only"},
        "items": [
            {
                "part_number": "RV BL 200 4TS",
                "description": "Rotary valve",
                "rate": 8495.67,
                "purchase_rate": 7646.10,
                "currency": "EUR",
                "unit": "NOS",
                "action": "CREATE",
                "existing_item_id": None,
                "status": "ready"
            }
        ],
        "user_confirmed": True,
        "confirmed_by_user": "Procurement Lead"
    }

    res = client.post("/api/supplier-pricing/zoho-sync", json=sync_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is False
    assert data["created_count"] == 0
    rec = data["records"][0]
    assert rec["status"] == "failed"
    assert "Duplicate SKU" in rec["notes"]
    assert any("CREATE FAILED" in log and "Duplicate SKU" in log for log in data["audit_log"])


def test_stage_4_sync_req_9f_update_failure_reported_as_failed(monkeypatch):
    """Requirement 9F: Zoho UPDATE failure is reported as FAILED, never reporting false SUCCESS."""
    from app.services.zoho_books_service import zoho_books_service

    monkeypatch.setattr(zoho_books_service, "get_item", lambda item_id, organization_id=None: {"code": 0, "item": {"name": "Old Name", "sku": "SKU-123"}})

    def mock_update_fail(item_id, payload, organization_id=None):
        return {
            "code": 3005,
            "message": "Item is currently inactive and cannot be updated.",
        }

    monkeypatch.setattr(zoho_books_service, "update_item", mock_update_fail)

    sync_payload = {
        "zoho_config": {"organization_id": "741367552", "environment": "production", "sync_mode": "items_only"},
        "items": [
            {
                "part_number": "SKU-123",
                "description": "Inactive Valve",
                "rate": 5000.0,
                "purchase_rate": 4000.0,
                "currency": "EUR",
                "unit": "NOS",
                "action": "UPDATE",
                "existing_item_id": "2552396000020392002",
                "status": "ready"
            }
        ],
        "user_confirmed": True,
        "confirmed_by_user": "Procurement Lead"
    }

    res = client.post("/api/supplier-pricing/zoho-sync", json=sync_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is False
    assert data["updated_count"] == 0
    rec = data["records"][0]
    assert rec["status"] == "failed"
    assert "inactive" in rec["notes"]
    assert any("UPDATE FAILED" in log and "inactive" in log for log in data["audit_log"])


def test_stage_4_sync_partial_failure_handling(monkeypatch):
    """Requirement 8: Partial failure handling accurately reports individual item results."""
    from app.services.zoho_books_service import zoho_books_service

    def mock_create_partial(payload, organization_id=None):
        if payload.get("sku") == "SUCCESS-SKU":
            return {
                "code": 0,
                "message": "success",
                "item": {
                    "item_id": "2552396000088888001",
                    "sku": "SUCCESS-SKU",
                    "name": "Success item",
                    "rate": 100.0,
                }
            }
        else:
            return {
                "code": 4002,
                "message": "Internal Zoho validation error on this item.",
            }

    monkeypatch.setattr(zoho_books_service, "create_item", mock_create_partial)

    sync_payload = {
        "zoho_config": {"organization_id": "741367552", "environment": "production", "sync_mode": "items_only"},
        "items": [
            {
                "part_number": "SUCCESS-SKU",
                "description": "Successful Item",
                "rate": 100.0,
                "purchase_rate": 80.0,
                "currency": "EUR",
                "unit": "NOS",
                "action": "CREATE",
                "existing_item_id": None,
                "status": "ready"
            },
            {
                "part_number": "FAIL-SKU",
                "description": "Failing Item",
                "rate": 200.0,
                "purchase_rate": 160.0,
                "currency": "EUR",
                "unit": "NOS",
                "action": "CREATE",
                "existing_item_id": None,
                "status": "ready"
            }
        ],
        "user_confirmed": True,
        "confirmed_by_user": "Procurement Lead"
    }

    res = client.post("/api/supplier-pricing/zoho-sync", json=sync_payload)
    assert res.status_code == 200
    data = res.json()
    # Partial success
    assert data["success"] is True
    assert data["created_count"] == 1
    assert data["updated_count"] == 0
    assert "Partially synchronized 1 of 2 items" in data["message"]
    assert "1 failed" in data["message"]

    # First record succeeded with real numeric ID
    assert data["records"][0]["status"] == "synced"
    assert data["records"][0]["existing_item_id"] == "2552396000088888001"

    # Second record failed
    assert data["records"][1]["status"] == "failed"
    assert "Internal Zoho validation error" in data["records"][1]["notes"]

    # Audit log reflects both individual outcomes
    logs = data["audit_log"]
    assert any("CREATE SUCCESS: Part #SUCCESS-SKU" in l and "ID: 2552396000088888001" in l for l in logs)
    assert any("CREATE FAILED: Part #FAIL-SKU" in l for l in logs)
    assert any("1 created, 0 updated, 1 failed" in l for l in logs)


def test_stage_4_sync_req_9h_confirmation_guardrail():
    """Requirement 9H: Confirmation checkbox/guardrail blocks execution without user confirmation."""
    unconfirmed_payload = {
        "zoho_config": {"organization_id": "741367552", "environment": "production", "sync_mode": "items_only"},
        "items": [
            {
                "part_number": "TEST-SKU",
                "description": "Test",
                "rate": 100.0,
                "purchase_rate": 80.0,
                "currency": "EUR",
                "unit": "NOS",
                "action": "CREATE",
                "existing_item_id": None,
                "status": "ready"
            }
        ],
        "user_confirmed": False,  # Missing confirmation
        "confirmed_by_user": None
    }

    res = client.post("/api/supplier-pricing/zoho-sync", json=unconfirmed_payload)
    assert res.status_code == 400
    assert "User confirmation required" in res.json()["detail"]


# ============================================================================
# History & Audit Trail Tests
# ============================================================================

def test_history_record_creation_after_successful_sync_with_real_zoho_ids(monkeypatch):
    """Verify history record is created after successful Zoho sync with real numeric IDs for CREATE and UPDATE."""
    from app.services.zoho_books_service import zoho_books_service

    def mock_create(item_payload, organization_id=None):
        return {
            "code": 0,
            "message": "Item created",
            "item": {
                "item_id": "255239600009990001",
                "name": item_payload["name"],
                "sku": item_payload["sku"],
                "rate": item_payload["rate"],
            }
        }

    def mock_update(item_id, item_payload, organization_id=None):
        return {
            "code": 0,
            "message": "Item updated",
            "item": {
                "item_id": item_id,
                "name": item_payload["name"],
                "sku": item_payload["sku"],
                "rate": item_payload["rate"],
            }
        }

    def mock_get(item_id, organization_id=None):
        return {"code": 0, "message": "success", "item": {"item_id": item_id, "sku": "UPDATE-SKU-01", "name": "Existing"}}

    monkeypatch.setattr(zoho_books_service, "create_item", mock_create)
    monkeypatch.setattr(zoho_books_service, "update_item", mock_update)
    monkeypatch.setattr(zoho_books_service, "get_item", mock_get)

    sync_payload = {
        "zoho_config": {"organization_id": "741367552", "environment": "production", "sync_mode": "items_only"},
        "items": [
            {
                "part_number": "CREATE-SKU-01",
                "description": "Item to Create",
                "rate": 1500.0,
                "purchase_rate": 1200.0,
                "currency": "EUR",
                "unit": "NOS",
                "action": "CREATE",
                "existing_item_id": None,
                "status": "ready"
            },
            {
                "part_number": "UPDATE-SKU-01",
                "description": "Item to Update",
                "rate": 2500.0,
                "purchase_rate": 2000.0,
                "currency": "EUR",
                "unit": "NOS",
                "action": "UPDATE",
                "existing_item_id": "255239600009990002",
                "status": "ready"
            }
        ],
        "user_confirmed": True,
        "confirmed_by_user": "Senior Auditor",
        "quotation_number": "QT-AUDIT-TEST-001",
        "supplier_name": "DMN-WESTINGHOUSE",
        "quotation_date": "2026-09-19",
        "source_filename": "dmn_quote_test.pdf",
        "currency": "EUR",
        "pricing_summary": {
            "total_supplier_net": 3200.0,
            "total_supplier_net_converted": 3200.0,
            "total_landed_cost": 3400.0,
            "total_selling_price": 4000.0,
            "total_gross_profit": 600.0,
            "overall_margin_percent": 15.0,
            "supplier_currency": "EUR",
            "target_currency": "EUR",
            "exchange_rate": 1.0,
            "items_count": 2
        }
    }

    res = client.post("/api/supplier-pricing/zoho-sync", json=sync_payload)
    assert res.status_code == 200
    sync_data = res.json()
    assert sync_data["success"] is True
    history_id = sync_data.get("history_id")
    assert history_id is not None

    # Fetch via history detail endpoint
    hist_res = client.get(f"/api/supplier-pricing/history/{history_id}")
    assert hist_res.status_code == 200
    hist_detail = hist_res.json()

    assert hist_detail["id"] == history_id
    assert hist_detail["quotation_number"] == "QT-AUDIT-TEST-001"
    assert hist_detail["supplier_name"] == "DMN-WESTINGHOUSE"
    assert hist_detail["overall_status"] == "SUCCESS"
    assert hist_detail["created_count"] == 1
    assert hist_detail["updated_count"] == 1
    assert hist_detail["failed_count"] == 0
    assert hist_detail["total_items"] == 2
    assert hist_detail["processed_by"] == "Senior Auditor"

    # Verify line items stored with REAL numeric IDs
    items = hist_detail["items"]
    assert len(items) == 2
    create_item = next(i for i in items if i["sku"] == "CREATE-SKU-01")
    assert create_item["action"] == "CREATE"
    assert create_item["zoho_item_id"] == "255239600009990001"
    assert create_item["zoho_item_id"].isdigit()
    assert create_item["zoho_status"] == "synced"

    update_item = next(i for i in items if i["sku"] == "UPDATE-SKU-01")
    assert update_item["action"] == "UPDATE"
    assert update_item["zoho_item_id"] == "255239600009990002"
    assert update_item["zoho_item_id"].isdigit()
    assert update_item["zoho_status"] == "synced"

    # Never contain fake IDs
    assert "ZB-NEW-" not in str(hist_detail)


def test_history_records_partial_success_and_failure(monkeypatch):
    """Verify partial failure sync correctly updates counts and stores error messages."""
    from app.services.zoho_books_service import zoho_books_service

    def mock_create(item_payload, organization_id=None):
        if item_payload["sku"] == "GOOD-SKU":
            return {
                "code": 0,
                "message": "Created",
                "item": {"item_id": "255239600001111111", "sku": "GOOD-SKU", "name": "Good", "rate": 100.0}
            }
        else:
            return {
                "code": 4001,
                "message": "Field 'tax_id' invalid in Zoho organization."
            }

    monkeypatch.setattr(zoho_books_service, "create_item", mock_create)

    sync_payload = {
        "zoho_config": {"organization_id": "741367552", "environment": "production", "sync_mode": "items_only"},
        "items": [
            {
                "part_number": "GOOD-SKU",
                "description": "Will pass",
                "rate": 100.0,
                "purchase_rate": 80.0,
                "currency": "EUR",
                "unit": "NOS",
                "action": "CREATE",
                "existing_item_id": None,
                "status": "ready"
            },
            {
                "part_number": "BAD-SKU",
                "description": "Will fail",
                "rate": 200.0,
                "purchase_rate": 150.0,
                "currency": "EUR",
                "unit": "NOS",
                "action": "CREATE",
                "existing_item_id": None,
                "status": "ready"
            }
        ],
        "user_confirmed": True,
        "confirmed_by_user": "Test Runner",
        "quotation_number": "QT-PARTIAL-TEST-002",
        "supplier_name": "Fitzpatrick Corp",
        "currency": "EUR"
    }

    res = client.post("/api/supplier-pricing/zoho-sync", json=sync_payload)
    assert res.status_code == 200
    history_id = res.json()["history_id"]

    hist_res = client.get(f"/api/supplier-pricing/history/{history_id}")
    assert hist_res.status_code == 200
    hist = hist_res.json()

    assert hist["overall_status"] == "PARTIAL"
    assert hist["created_count"] == 1
    assert hist["failed_count"] == 1

    good = next(i for i in hist["items"] if i["sku"] == "GOOD-SKU")
    assert good["zoho_status"] == "synced"
    assert good["zoho_item_id"] == "255239600001111111"

    bad = next(i for i in hist["items"] if i["sku"] == "BAD-SKU")
    assert bad["zoho_status"] == "failed"
    assert "tax_id" in str(bad["error_message"])


def test_history_list_search_and_filters():
    """Verify history listing, search across fields (quote #, supplier, SKU), status filter, and pagination."""
    # 1. Fetch list
    res = client.get("/api/supplier-pricing/history")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "records" in data
    assert "summary_stats" in data
    assert data["summary_stats"]["total_quotations"] >= 2
    assert data["summary_stats"]["successfully_synced"] >= 1
    assert data["summary_stats"]["partially_failed"] >= 1

    # 2. Search by Quotation Number
    search_quote_res = client.get("/api/supplier-pricing/history?search=QT-AUDIT-TEST-001")
    assert search_quote_res.status_code == 200
    results = search_quote_res.json()["records"]
    assert len(results) >= 1
    assert any(r["quotation_number"] == "QT-AUDIT-TEST-001" for r in results)

    # 3. Search by Supplier Name
    search_supp_res = client.get("/api/supplier-pricing/history?search=Fitzpatrick")
    assert search_supp_res.status_code == 200
    supp_results = search_supp_res.json()["records"]
    assert len(supp_results) >= 1
    assert all("Fitzpatrick" in r["supplier_name"] for r in supp_results)

    # 4. Search by SKU
    search_sku_res = client.get("/api/supplier-pricing/history?search=GOOD-SKU")
    assert search_sku_res.status_code == 200
    sku_results = search_sku_res.json()["records"]
    assert len(sku_results) >= 1
    assert any(r["quotation_number"] == "QT-PARTIAL-TEST-002" for r in sku_results)

    # 5. Filter by Status
    status_filter_res = client.get("/api/supplier-pricing/history?status=PARTIAL")
    assert status_filter_res.status_code == 200
    partial_records = status_filter_res.json()["records"]
    assert all(r["overall_status"] == "PARTIAL" for r in partial_records)

    # 6. Filter by Action
    action_filter_res = client.get("/api/supplier-pricing/history?action=UPDATE")
    assert action_filter_res.status_code == 200
    update_records = action_filter_res.json()["records"]
    assert any(r["quotation_number"] == "QT-AUDIT-TEST-001" for r in update_records)


def test_history_is_strictly_read_only():
    """Verify that history endpoints are strictly read-only and reject any mutation methods."""
    # POST to /history
    post_res = client.post("/api/supplier-pricing/history", json={"title": "hack"})
    assert post_res.status_code in [404, 405]

    # PUT to /history
    put_res = client.put("/api/supplier-pricing/history/some-id", json={"title": "hack"})
    assert put_res.status_code in [404, 405]

    # DELETE to /history
    del_res = client.delete("/api/supplier-pricing/history/some-id")
    assert del_res.status_code in [404, 405]


# ============================================================================
# Zoho Books Composite Items Unit Tests (Mocked HTTP - No Live Writes)
# ============================================================================

def test_composite_item_create_success(monkeypatch):
    """Test successful composite item creation via service and API route with real numeric ID."""
    from app.services.zoho_books_service import zoho_books_service
    import httpx

    captured_posts = []
    orig_post = httpx.Client.post

    def mock_post(self, url, *args, **kwargs):
        if "zohoapis" in str(url):
            captured_posts.append({"url": str(url), "json": kwargs.get("json"), "params": kwargs.get("params")})
            return httpx.Response(
                status_code=200,
                json={
                    "code": 0,
                    "message": "Composite item created successfully",
                    "composite_item": {
                        "composite_item_id": "2552396000099999001",
                        "name": "Ducting Kit Assembly",
                        "sku": "DUCT-KIT-01",
                        "rate": 75000000.0,
                        "combo_type": "kit",
                        "mapped_items": [
                            {"item_id": "2552396000011501084", "quantity": 2.0}
                        ]
                    }
                },
                request=httpx.Request("POST", str(url))
            )
        return orig_post(self, url, *args, **kwargs)

    monkeypatch.setattr(zoho_books_service.token_manager, "get_valid_access_token", lambda: "mock_test_token")
    monkeypatch.setattr(httpx.Client, "post", mock_post)

    payload = {
        "name": "Ducting Kit Assembly",
        "sku": "DUCT-KIT-01",
        "unit": "Set",
        "description": "Complete ducting assembly",
        "combo_type": "kit",
        "rate": 75000000.0,
        "mapped_items": [
            {"item_id": "2552396000011501084", "quantity": 2.0}
        ]
    }

    # 1. Service test
    result = zoho_books_service.create_composite_item(payload=payload)
    assert result["success"] is True
    assert result["composite_item_id"] == "2552396000099999001"
    assert result["composite_item_id"].isdigit()
    assert not result["composite_item_id"].startswith("ZB-NEW-")

    # Verify endpoint called
    assert len(captured_posts) >= 1
    assert "/books/v3/compositeitems" in captured_posts[0]["url"]

    # 2. API endpoint test
    api_res = client.post("/api/supplier-pricing/zoho/composite-items", json=payload)
    assert api_res.status_code == 200
    api_data = api_res.json()
    assert api_data["success"] is True
    assert api_data["composite_item_id"] == "2552396000099999001"


def test_composite_item_create_api_failure(monkeypatch):
    """Test composite item creation fails gracefully when Zoho returns non-zero code."""
    from app.services.zoho_books_service import zoho_books_service
    import httpx

    orig_post = httpx.Client.post

    def mock_post_fail(self, url, *args, **kwargs):
        if "zohoapis" in str(url):
            return httpx.Response(
                status_code=400,
                json={"code": 1005, "message": "Duplicate composite item name."},
                request=httpx.Request("POST", str(url))
            )
        return orig_post(self, url, *args, **kwargs)

    monkeypatch.setattr(zoho_books_service.token_manager, "get_valid_access_token", lambda: "mock_test_token")
    monkeypatch.setattr(httpx.Client, "post", mock_post_fail)

    payload = {
        "name": "Duplicate Name",
        "rate": 1000.0,
        "mapped_items": [{"item_id": "2552396000011501084", "quantity": 1.0}]
    }

    with pytest.raises(RuntimeError) as exc_info:
        zoho_books_service.create_composite_item(payload)
    assert "Duplicate composite item name" in str(exc_info.value)

    # API test returns 502
    api_res = client.post("/api/supplier-pricing/zoho/composite-items", json=payload)
    assert api_res.status_code == 502


def test_composite_item_create_rejects_fake_or_non_numeric_id(monkeypatch):
    """Test safety requirement: reject fake or non-numeric composite_item_id from response."""
    from app.services.zoho_books_service import zoho_books_service
    import httpx

    orig_post = httpx.Client.post

    def mock_post_fake_id(self, url, *args, **kwargs):
        if "zohoapis" in str(url):
            return httpx.Response(
                status_code=200,
                json={
                    "code": 0,
                    "message": "success",
                    "composite_item": {
                        "composite_item_id": "ZB-NEW-12345",  # FAKE ID
                        "name": "Test"
                    }
                },
                request=httpx.Request("POST", str(url))
            )
        return orig_post(self, url, *args, **kwargs)

    monkeypatch.setattr(zoho_books_service.token_manager, "get_valid_access_token", lambda: "mock_test_token")
    monkeypatch.setattr(httpx.Client, "post", mock_post_fake_id)

    payload = {
        "name": "Test",
        "rate": 1000.0,
        "mapped_items": [{"item_id": "2552396000011501084", "quantity": 1.0}]
    }

    with pytest.raises(ValueError) as exc_info:
        zoho_books_service.create_composite_item(payload)
    assert "invalid or non-numeric composite_item_id" in str(exc_info.value)


def test_composite_item_create_rejects_fake_component_id():
    """Test safety requirement: reject component item_id that is fake or non-numeric before calling Zoho."""
    from app.services.zoho_books_service import zoho_books_service

    invalid_payload = {
        "name": "Test Kit",
        "rate": 1000.0,
        "mapped_items": [{"item_id": "ZB-NEW-54321", "quantity": 1.0}]
    }

    with pytest.raises(ValueError) as exc_info:
        zoho_books_service.create_composite_item(invalid_payload)
    assert "All component item IDs must be real numeric Zoho item IDs" in str(exc_info.value)


def test_composite_item_create_auth_failure(monkeypatch):
    """Test composite item creation raises clear error on 401 authentication failure."""
    from app.services.zoho_books_service import zoho_books_service
    import httpx

    orig_post = httpx.Client.post

    def mock_post_401(self, url, *args, **kwargs):
        if "zohoapis" in str(url):
            return httpx.Response(
                status_code=401,
                json={"code": 57, "message": "You are not authorized to perform this operation"},
                request=httpx.Request("POST", str(url))
            )
        return orig_post(self, url, *args, **kwargs)

    monkeypatch.setattr(zoho_books_service.token_manager, "get_valid_access_token", lambda: "invalid_token")
    monkeypatch.setattr(zoho_books_service.token_manager, "_refresh_token", None)
    monkeypatch.setattr(httpx.Client, "post", mock_post_401)

    payload = {
        "name": "Test",
        "rate": 1000.0,
        "mapped_items": [{"item_id": "2552396000011501084", "quantity": 1.0}]
    }

    with pytest.raises(RuntimeError) as exc_info:
        zoho_books_service.create_composite_item(payload)
    assert "authentication failure" in str(exc_info.value).lower()


def test_composite_item_update_success(monkeypatch):
    """Test successful composite item update via service and API route."""
    from app.services.zoho_books_service import zoho_books_service
    import httpx

    captured_puts = []
    orig_put = httpx.Client.put

    def mock_put(self, url, *args, **kwargs):
        if "zohoapis" in str(url):
            captured_puts.append({"url": str(url), "json": kwargs.get("json")})
            return httpx.Response(
                status_code=200,
                json={
                    "code": 0,
                    "message": "Composite item updated successfully",
                    "composite_item": {
                        "composite_item_id": "2552396000011501220",
                        "name": "Updated Flap Type Valve",
                        "rate": 80000000.0
                    }
                },
                request=httpx.Request("PUT", str(url))
            )
        return orig_put(self, url, *args, **kwargs)

    monkeypatch.setattr(zoho_books_service.token_manager, "get_valid_access_token", lambda: "mock_test_token")
    monkeypatch.setattr(httpx.Client, "put", mock_put)

    update_payload = {
        "name": "Updated Flap Type Valve",
        "rate": 80000000.0,
        "composite_item_id": "HACK_ATTEMPT_ID"  # Must be stripped/prevented from replacing target ID
    }

    res = zoho_books_service.update_composite_item("2552396000011501220", update_payload)
    assert res["success"] is True
    assert res["composite_item_id"] == "2552396000011501220"

    # Verify ID was NOT in payload body
    assert len(captured_puts) == 1
    assert "composite_item_id" not in captured_puts[0]["json"]
    assert "/books/v3/compositeitems/2552396000011501220" in captured_puts[0]["url"]

    # API PUT route test
    api_res = client.put("/api/supplier-pricing/zoho/composite-items/2552396000011501220", json={"name": "Updated Flap Type Valve"})
    assert api_res.status_code == 200
    assert api_res.json()["composite_item_id"] == "2552396000011501220"


def test_composite_item_update_rejects_invalid_id():
    """Test safety requirement: reject invalid/non-numeric/fake composite_item_id on update."""
    from app.services.zoho_books_service import zoho_books_service

    for bad_id in ["", "   ", "abc", "ZB-NEW-12345", "ID_999"]:
        with pytest.raises(ValueError) as exc_info:
            zoho_books_service.update_composite_item(bad_id, {"name": "Test"})
        assert "Expected real numeric Zoho Composite Item ID" in str(exc_info.value)


def test_composite_item_update_404(monkeypatch):
    """Test composite item update handles 404 Not Found cleanly."""
    from app.services.zoho_books_service import zoho_books_service
    import httpx

    orig_put = httpx.Client.put

    def mock_put_404(self, url, *args, **kwargs):
        if "zohoapis" in str(url):
            return httpx.Response(status_code=404, request=httpx.Request("PUT", str(url)))
        return orig_put(self, url, *args, **kwargs)

    monkeypatch.setattr(zoho_books_service.token_manager, "get_valid_access_token", lambda: "mock_test_token")
    monkeypatch.setattr(httpx.Client, "put", mock_put_404)

    with pytest.raises(ValueError) as exc_info:
        zoho_books_service.update_composite_item("2552396000099999999", {"name": "Test"})
    assert "not found" in str(exc_info.value).lower()

    # API returns 404
    api_res = client.put("/api/supplier-pricing/zoho/composite-items/2552396000099999999", json={"name": "Test"})
    assert api_res.status_code == 404


def test_composite_item_update_401_and_403(monkeypatch):
    """Test composite item update handles 401 and 403 error codes cleanly."""
    from app.services.zoho_books_service import zoho_books_service
    import httpx

    orig_put = httpx.Client.put

    def mock_put_403(self, url, *args, **kwargs):
        if "zohoapis" in str(url):
            return httpx.Response(status_code=403, request=httpx.Request("PUT", str(url)))
        return orig_put(self, url, *args, **kwargs)

    monkeypatch.setattr(zoho_books_service.token_manager, "get_valid_access_token", lambda: "mock_test_token")
    monkeypatch.setattr(httpx.Client, "put", mock_put_403)

    with pytest.raises(RuntimeError) as exc_info:
        zoho_books_service.update_composite_item("2552396000011501220", {"name": "Test"})
    assert "permission denied" in str(exc_info.value).lower()

    def mock_put_401(self, url, *args, **kwargs):
        if "zohoapis" in str(url):
            return httpx.Response(status_code=401, request=httpx.Request("PUT", str(url)))
        return orig_put(self, url, *args, **kwargs)

    monkeypatch.setattr(httpx.Client, "put", mock_put_401)
    with pytest.raises(RuntimeError) as exc_info:
        zoho_books_service.update_composite_item("2552396000011501220", {"name": "Test"})
    assert "authentication failure" in str(exc_info.value).lower()


def test_find_composite_item_by_exact_sku(monkeypatch):
    """Test exact SKU lookup compares SKU strictly and never matches description or name."""
    from app.services.zoho_books_service import zoho_books_service

    mock_items = [
        {
            "composite_item_id": "2552396000011501220",
            "name": "Supply of DMN Flap Type Diverter Valve unit, Type : FDVP 125 1",
            "sku": "FDVP 125 1 11251038  1",
            "part_number": "",
            "description": "FDVP Diverter Valve"
        },
        {
            "composite_item_id": "2552396000004709149",
            "name": "CUTTER BLOWER TCB7-30",
            "sku": "TCB7-30-SKU",
            "part_number": "",
            "description": "High pressure blower"
        }
    ]

    def mock_list(organization_id=None, search_text=None):
        return {
            "success": True,
            "composite_items": mock_items,
            "count": len(mock_items)
        }

    monkeypatch.setattr(zoho_books_service, "list_composite_items", mock_list)

    # 1. Exact SKU match
    item = zoho_books_service.find_composite_item_by_exact_sku("FDVP 125 1 11251038  1")
    assert item is not None
    assert item["composite_item_id"] == "2552396000011501220"

    # 2. Case-insensitive exact match
    item_ci = zoho_books_service.find_composite_item_by_exact_sku("fdvp 125 1 11251038  1")
    assert item_ci is not None
    assert item_ci["composite_item_id"] == "2552396000011501220"

    # 3. Match by name or description must return None (NEVER match name/desc)
    name_match = zoho_books_service.find_composite_item_by_exact_sku("Supply of DMN Flap Type Diverter")
    assert name_match is None

    desc_match = zoho_books_service.find_composite_item_by_exact_sku("High pressure blower")
    assert desc_match is None

    # 4. Non-existent SKU
    missing = zoho_books_service.find_composite_item_by_exact_sku("NON-EXISTENT-SKU")
    assert missing is None

    # 5. Empty SKU
    empty = zoho_books_service.find_composite_item_by_exact_sku("")
    assert empty is None




