import re
import time
import datetime
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any

try:
    import pymupdf as fitz
except ImportError:
    import fitz

from app.schemas.supplier_pricing import (
    SupplierQuotationData,
    SupplierQuoteItem,
    SupplierValidationSummary,
    SupplierValidationIssue,
    SupplierExtractionResponse,
    WorkflowStage,
    SupplierWorkflowStagesResponse,
    PricingConfigParameters,
    CalculatedLinePrice,
    PricingSummary,
    SupplierPricingCalculationRequest,
    SupplierPricingCalculationResponse,
    ProcurementApprovalRequest,
    ProcurementApprovalResponse,
    ZohoItemSyncRecord,
    ZohoSyncConfig,
    ZohoPreviewRequest,
    ZohoPreviewResponse,
    ZohoExecuteSyncRequest,
    ZohoExecuteSyncResponse,
)
from app.services.pdf_service import pdf_service
from app.utils.text_utils import extract_currency, normalize_price, clean_part_number

logger = logging.getLogger(__name__)


class SupplierPricingService:
    """Service handling supplier quotation PDF parsing, validation, and workflow state."""

    def validate_quotation(self, quotation: SupplierQuotationData) -> SupplierValidationSummary:
        issues: list[SupplierValidationIssue] = []
        missing_fields: list[str] = []
        uncertain_fields: list[str] = []
        field_status: dict[str, str] = {}

        # 1. Header validations
        if not quotation.supplier_name or not quotation.supplier_name.strip():
            issues.append(SupplierValidationIssue(
                field="supplier_name",
                issue_type="error",
                message="Supplier name is missing.",
                suggested_fix="Enter the supplier/vendor business name."
            ))
            missing_fields.append("supplier_name")
            field_status["supplier_name"] = "missing"
        else:
            field_status["supplier_name"] = "valid"

        if not quotation.customer or not quotation.customer.strip():
            issues.append(SupplierValidationIssue(
                field="customer",
                issue_type="info",
                message="Customer name is not explicitly specified.",
                suggested_fix="Enter the purchasing customer name."
            ))
            field_status["customer"] = "warning"
        else:
            field_status["customer"] = "valid"

        if not quotation.quote_number or not quotation.quote_number.strip():
            issues.append(SupplierValidationIssue(
                field="quote_number",
                issue_type="error",
                message="Quote reference number is missing.",
                suggested_fix="Enter supplier's quote or reference ID."
            ))
            missing_fields.append("quote_number")
            field_status["quote_number"] = "missing"
        else:
            field_status["quote_number"] = "valid"

        if not quotation.quote_date or not quotation.quote_date.strip():
            issues.append(SupplierValidationIssue(
                field="quote_date",
                issue_type="warning",
                message="Quote issue date is missing.",
                suggested_fix="Provide date of quotation issue (DD/MM/YYYY or YYYY-MM-DD)."
            ))
            missing_fields.append("quote_date")
            field_status["quote_date"] = "warning"
        else:
            field_status["quote_date"] = "valid"

        if not quotation.currency or not quotation.currency.strip():
            issues.append(SupplierValidationIssue(
                field="currency",
                issue_type="warning",
                message="Currency is not specified.",
                suggested_fix="Defaulting to EUR/USD. Verify currency code."
            ))
            uncertain_fields.append("currency")
            field_status["currency"] = "warning"
        else:
            field_status["currency"] = "valid"

        if not quotation.delivery_lead_time or not quotation.delivery_lead_time.strip():
            issues.append(SupplierValidationIssue(
                field="delivery_lead_time",
                issue_type="info",
                message="General delivery/lead time is not specified at quote level.",
                suggested_fix="Check quotation notes or item lines for lead time."
            ))
            field_status["delivery_lead_time"] = "warning"
        else:
            field_status["delivery_lead_time"] = "valid"

        # 2. Line item validations
        if not quotation.items:
            issues.append(SupplierValidationIssue(
                field="items",
                issue_type="error",
                message="No line items detected in quotation.",
                suggested_fix="Add at least one supplier quote item."
            ))
            missing_fields.append("items")

        calculated_lines_total = 0.0

        for item in quotation.items:
            item_line = item.line_number
            item_errors = 0

            # Part number
            if not item.part_number or not item.part_number.strip():
                issues.append(SupplierValidationIssue(
                    field=f"items[{item_line}].part_number",
                    item_line=item_line,
                    issue_type="error",
                    message=f"Line {item_line}: Part number is missing.",
                    suggested_fix="Enter part number or SKU."
                ))
                missing_fields.append(f"Line {item_line} Part Number")
                item_errors += 1

            # Description
            if not item.description or not item.description.strip():
                issues.append(SupplierValidationIssue(
                    field=f"items[{item_line}].description",
                    item_line=item_line,
                    issue_type="warning",
                    message=f"Line {item_line}: Description is empty.",
                    suggested_fix="Provide part description."
                ))
                uncertain_fields.append(f"Line {item_line} Description")

            # Quantity
            if item.quantity is None:
                issues.append(SupplierValidationIssue(
                    field=f"items[{item_line}].quantity",
                    item_line=item_line,
                    issue_type="error",
                    message=f"Line {item_line}: Quantity is missing.",
                    suggested_fix="Specify numerical quantity."
                ))
                missing_fields.append(f"Line {item_line} Quantity")
                item_errors += 1
            elif item.quantity <= 0:
                issues.append(SupplierValidationIssue(
                    field=f"items[{item_line}].quantity",
                    item_line=item_line,
                    issue_type="warning",
                    message=f"Line {item_line}: Quantity is zero or negative.",
                ))
                uncertain_fields.append(f"Line {item_line} Quantity")

            # Unit
            if not item.unit:
                uncertain_fields.append(f"Line {item_line} Unit")

            # Unit price
            if item.unit_price is None:
                issues.append(SupplierValidationIssue(
                    field=f"items[{item_line}].unit_price",
                    item_line=item_line,
                    issue_type="error",
                    message=f"Line {item_line}: Unit price is missing.",
                    suggested_fix="Enter quoted unit price."
                ))
                missing_fields.append(f"Line {item_line} Unit Price")
                item_errors += 1

            # Total and math check
            if item.quantity is not None and item.unit_price is not None:
                discount_val = item.discount or 0.0
                expected_subtotal = item.quantity * item.unit_price
                if 0 < discount_val <= 100:
                    discount_deduction = expected_subtotal * (discount_val / 100.0)
                else:
                    discount_deduction = discount_val
                expected_item_total = max(0.0, expected_subtotal - discount_deduction)

                if item.total is not None:
                    diff = abs(item.total - expected_item_total)
                    if diff > 0.05 and diff > (expected_item_total * 0.01):
                        issues.append(SupplierValidationIssue(
                            field=f"items[{item_line}].total",
                            item_line=item_line,
                            issue_type="warning",
                            message=f"Line {item_line}: Total ({item.total:.2f}) does not match Qty × Unit Price - Discount ({expected_item_total:.2f}).",
                            suggested_fix="Review total or discount calculation."
                        ))
                        uncertain_fields.append(f"Line {item_line} Total")
                    calculated_lines_total += item.total
                else:
                    item.total = round(expected_item_total, 2)
                    calculated_lines_total += item.total
            elif item.total is not None:
                calculated_lines_total += item.total

            # Item status
            if item_errors > 0:
                item.validation_status = "error"
            elif any(iss.item_line == item_line for iss in issues if iss.issue_type == "warning"):
                item.validation_status = "warning"
            else:
                item.validation_status = "valid"

        # 3. Totals math verification
        packing = quotation.packing_charges or 0.0
        freight = quotation.freight_charges or 0.0
        other = quotation.other_charges or 0.0
        expected_grand_total = calculated_lines_total + freight + other  # Note: in DMN, other_charges (Line Misc Charges) already sums up packing

        if quotation.grand_total is not None:
            # Check against either lines + other or lines + packing + freight
            alt_expected = calculated_lines_total + packing + freight
            if abs(quotation.grand_total - expected_grand_total) > 0.15 and abs(quotation.grand_total - alt_expected) > 0.15:
                issues.append(SupplierValidationIssue(
                    field="grand_total",
                    issue_type="warning",
                    message=f"Grand Total ({quotation.grand_total:.2f}) differs from lines sum ({calculated_lines_total:.2f}) plus charges.",
                    suggested_fix="Verify charges and grand total sum."
                ))
                uncertain_fields.append("grand_total")
                field_status["grand_total"] = "warning"
            else:
                field_status["grand_total"] = "valid"
        else:
            quotation.grand_total = round(expected_grand_total, 2)
            field_status["grand_total"] = "valid"

        if quotation.lines_total is None:
            quotation.lines_total = round(calculated_lines_total, 2)

        errors_count = sum(1 for i in issues if i.issue_type == "error")
        warnings_count = sum(1 for i in issues if i.issue_type == "warning")
        is_valid = errors_count == 0

        overall_conf = 1.0 - (errors_count * 0.15) - (warnings_count * 0.04)
        overall_conf = max(0.1, min(1.0, overall_conf))

        return SupplierValidationSummary(
            is_valid=is_valid,
            overall_confidence=round(overall_conf, 2),
            errors_count=errors_count,
            warnings_count=warnings_count,
            missing_fields=missing_fields,
            uncertain_fields=uncertain_fields,
            field_status=field_status,
            issues=issues,
        )

    def extract_from_pdf(self, pdf_path: Path, source_pdf_id: str, original_filename: str = "") -> SupplierExtractionResponse:
        start_time = time.time()
        
        # Open PDF directly with fitz for high-fidelity block analysis
        doc = fitz.open(str(pdf_path))
        try:
            quotation = self._parse_supplier_document(doc, source_pdf_id, original_filename or pdf_path.name)
        finally:
            doc.close()

        validation = self.validate_quotation(quotation)
        duration = time.time() - start_time

        return SupplierExtractionResponse(
            success=True,
            quotation=quotation,
            validation=validation,
            processing_time_seconds=round(duration, 3),
            source_pdf_id=source_pdf_id,
            filename=original_filename or pdf_path.name,
        )

    def _parse_supplier_document(self, doc: fitz.Document, source_pdf_id: str, filename: str) -> SupplierQuotationData:
        if len(doc) == 0:
            raise ValueError("Empty PDF document provided.")

        p1_text = doc[0].get_text("text")

        # 1. Supplier Name: check top blocks of Page 1
        supplier_name = ""
        top_lines = [l.strip() for l in p1_text.split("\n") if l.strip()][:10]
        for line in top_lines:
            upper = line.upper()
            if any(term in upper for term in ["LIMITED", "LTD", "INC", "CORP", "GMBH", "B.V.", "LLC", "SDN BHD"]):
                supplier_name = line.strip()
                break
        if not supplier_name and top_lines:
            supplier_name = top_lines[0]

        # 2. Customer Name
        customer = ""
        cust_match = re.search(r"Customer:\s*([^\n\r]+)", p1_text)
        if cust_match:
            customer = cust_match.group(1).strip()
        else:
            # Look for customer address block under supplier
            for line in top_lines[4:]:
                if "PT." in line or "Customer" in line or "INC" in line.upper():
                    customer = line.strip()
                    break

        # 3. Quote Number
        quote_number = ""
        qn_match = (
            re.search(r"Quote Number[:\s]+(\d+)", p1_text, re.IGNORECASE)
            or re.search(r"Reference:[\s\d]*\n(\d{6,10})", p1_text)
            or re.search(r"Quote[\s\S]{0,120}?\n(\d{6,10})\b", p1_text)
            or re.search(r"\b(4\d{7})\b", p1_text)  # Standard 8-digit DMN quotation identifier
        )
        if qn_match:
            quote_number = qn_match.group(1).strip()

        # 4. Quote Date
        quote_date = ""
        date_match = re.search(r"Date Quoted:\s*(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4})", p1_text) or re.search(
            r"Date:\s*(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4})", p1_text, re.IGNORECASE
        )
        if date_match:
            quote_date = date_match.group(1).strip()

        # 5. Currency
        currency = extract_currency(p1_text) or "EUR"

        # 6. Payment Terms
        payment_terms = ""
        pay_match = re.search(r"Payment terms:\s*([^\n\r]+)", p1_text, re.IGNORECASE)
        if pay_match:
            payment_terms = pay_match.group(1).strip()

        # 7. Delivery / Lead Time (Header)
        delivery_terms = ""
        deliv_match = re.search(r"Delivery:\s*([^\n\r]+(?:\n[^\n\r]+)?)", p1_text, re.IGNORECASE)
        if deliv_match:
            raw_deliv = " ".join(deliv_match.group(1).split())
            cleaned_deliv = re.sub(r"[\x00-\x1f\x7f-\x9f\ufffd\ufffe\uffff]+", " ", raw_deliv)
            delivery_terms = re.sub(r"\s+", " ", cleaned_deliv).strip()

        # 8. Totals from quotation pages
        lines_total = None
        other_charges = 0.0
        grand_total = None

        # 9. Line Items Extraction across valid quotation pages
        items: list[SupplierQuoteItem] = []
        has_found_totals = False

        for page_idx in range(len(doc)):
            if has_found_totals:
                break
            page_text = doc[page_idx].get_text("text")

            # CRITICAL: Skip technical specification, datasheet, or appendix pages
            if any(term in page_text for term in [
                "Web Configuration ID",
                "Customer specification",
                "Product specification",
                "Product Certification",
            ]):
                continue

            # Look for structured table header (e.g. DMN or standard columns)
            tbl_match = re.search(
                r"(?:Discount %|Unit Price|Total Price)\s*\n([\s\S]+?)(?=\nLines Total:|\nTotal Net:|\nTotal Net Including Taxes:|\n\d+\s*/\s*\d+|\Z)",
                page_text
            )

            if tbl_match:
                tbl_text = tbl_match.group(1).strip()
                # Split by line items: sequential integer on its own line
                raw_chunks = re.split(r"(?:^|\n)(?=[1-9]\d{0,2}\n)", tbl_text)

                for c in raw_chunks:
                    if not c.strip():
                        continue
                    lines = [l.strip() for l in c.split("\n") if l.strip()]
                    if not lines or not lines[0].isdigit():
                        continue

                    line_num = int(lines[0])

                    # Find quantity and unit line: e.g. "1 NOS", "2 NOS", "4.0 PCS"
                    qty = None
                    unit = "NOS"
                    qty_idx = -1

                    for idx, l in enumerate(lines):
                        qm = re.match(r"^(\d+(?:\.\d+)?)\s+([A-Za-z]{2,5})$", l)
                        if qm and idx > 0:
                            qty = float(qm.group(1))
                            unit = qm.group(2).upper()
                            qty_idx = idx
                            break

                    discount = 0.0
                    packaging = 0.0
                    lead_time = None
                    commodity_code = None
                    option = None
                    price_candidates: list[float] = []

                    for idx in range(qty_idx + 1 if qty_idx > 0 else 1, len(lines)):
                        l = lines[idx]

                        # Discount %
                        dm = re.search(r"(\d+(?:\.\d+)?)\s*%", l)
                        if dm:
                            discount = float(dm.group(1))
                            continue

                        # Packaging cost per item
                        if "packaging" in l.lower() or "packing" in l.lower():
                            if idx + 1 < len(lines):
                                pval = normalize_price(lines[idx + 1])
                                if pval is not None:
                                    packaging = pval
                            continue

                        # Lead time
                        lm = re.search(r"Lead Time\s+([^\n\r]+)", l, re.IGNORECASE)
                        if lm:
                            raw_lt = lm.group(1).strip()
                            raw_lt = re.sub(r"(\d+)([a-zA-Z])", r"\1 \2", raw_lt)
                            lead_time = raw_lt
                            continue

                        # Commodity code
                        cm = re.search(r"Commodity Code:\s*([A-Za-z0-9]+)", l, re.IGNORECASE)
                        if cm:
                            commodity_code = cm.group(1)
                            continue

                        # Price candidate
                        pval = normalize_price(l)
                        if pval is not None and not l.isdigit() and ("€" in l or "$" in l or "." in l or "," in l):
                            price_candidates.append(pval)

                    unit_price = price_candidates[0] if len(price_candidates) >= 1 else None
                    if len(price_candidates) >= 2:
                        total_price = price_candidates[1]
                    elif qty and unit_price:
                        total_price = round(qty * unit_price * (1.0 - discount / 100.0), 2)
                    else:
                        total_price = unit_price

                    # Parse header lines for Part Number, Description, Option
                    header_lines = lines[1:qty_idx] if qty_idx > 0 else lines[1:3]
                    desc_lines: list[str] = []

                    for hl in header_lines:
                        om = re.search(r"Option\s*(\d+)", hl, re.IGNORECASE)
                        if om:
                            option = om.group(1)
                        else:
                            desc_lines.append(hl)

                    # Determine Part Number and Description
                    if len(desc_lines) >= 2 and len(desc_lines[0]) <= 4 and ":" in desc_lines[1]:
                        # e.g. "RV" + "BL 200 4TS : BL - Rotary valve" -> Part: "RV BL 200 4TS"
                        prefix = desc_lines[0].strip()
                        model_part = desc_lines[1].split(":")[0].strip()
                        part_number = f"{prefix} {model_part}"
                        description = desc_lines[1].strip()
                    elif len(desc_lines) >= 1 and ":" in desc_lines[0]:
                        model_part = desc_lines[0].split(":")[0].strip()
                        part_number = model_part
                        description = desc_lines[0].strip()
                    elif len(desc_lines) >= 2 and (desc_lines[0].isdigit() or clean_part_number(desc_lines[0])):
                        part_number = clean_part_number(desc_lines[0])
                        description = " ".join(desc_lines[1:]).strip()
                    elif desc_lines:
                        part_number = clean_part_number(desc_lines[0])
                        description = desc_lines[0]
                    else:
                        part_number = f"PART-{line_num}"
                        description = ""

                    items.append(
                        SupplierQuoteItem(
                            line_number=line_num,
                            part_number=part_number,
                            description=description,
                            quantity=qty,
                            unit=unit,
                            currency=currency,
                            unit_price=unit_price,
                            discount=discount,
                            packing_charges=packaging,
                            freight_charges=0.0,
                            total=total_price,
                            delivery_lead_time=lead_time or delivery_terms,
                            option=option,
                            commodity_code=commodity_code,
                            validation_status="valid",
                        )
                    )

            # Check summary totals across pages
            if not lines_total:
                lt_m = re.search(r"Lines Total:\s*[^\d]*([\d,.]+)", page_text)
                if lt_m:
                    lines_total = normalize_price(lt_m.group(1))

            if not other_charges:
                mc_m = re.search(r"Line Miscellaneous Charges:\s*[^\d]*([\d,.]+)", page_text)
                if mc_m:
                    other_charges = normalize_price(mc_m.group(1)) or 0.0

            if not grand_total:
                tot_m = (
                    re.search(r"Total Net Including Taxes:\s*[^\d]*([\d,.]+)", page_text)
                    or re.search(r"Total Net:\s*[^\d]*([\d,.]+)", page_text)
                    or re.search(r"Grand Total:\s*[^\d]*([\d,.]+)", page_text)
                )
                if tot_m:
                    grand_total = normalize_price(tot_m.group(1))

            if "Lines Total:" in page_text or "Total Net:" in page_text or "Total Net Including Taxes:" in page_text:
                has_found_totals = True

        # Fallback if no table items were parsed: try generic line heuristic
        if not items:
            items = self._fallback_parse_items(p1_text, currency, delivery_terms)

        # Compute header packing charges from items if not explicit
        item_packing_sum = sum(it.packing_charges or 0.0 for it in items)
        final_packing = item_packing_sum if item_packing_sum > 0 else 0.0

        final_lines_total = lines_total or sum(it.total or 0.0 for it in items)
        final_grand_total = grand_total or (final_lines_total + other_charges)

        return SupplierQuotationData(
            supplier_name=supplier_name or "Supplier Inc.",
            customer=customer or "Valued Customer",
            quote_number=quote_number or f"SQ-{int(time.time()) % 100000}",
            quote_date=quote_date or "2026-09-15",
            delivery_lead_time=delivery_terms or "Standard",
            currency=currency,
            packing_charges=final_packing,
            freight_charges=0.0,
            other_charges=other_charges,
            lines_total=final_lines_total,
            grand_total=final_grand_total,
            payment_terms=payment_terms or "Standard Commercial Terms",
            valid_until=None,
            notes=None,
            items=items,
            source_file_id=source_pdf_id,
            source_filename=filename,
        )

    def _fallback_parse_items(self, text: str, currency: str, delivery_terms: str) -> list[SupplierQuoteItem]:
        """Fallback parser for non-standard supplier quotation layouts."""
        items: list[SupplierQuoteItem] = []
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        line_num = 1

        for line in lines:
            tokens = line.split()
            if len(tokens) >= 4:
                numeric_candidates = []
                for tok in reversed(tokens):
                    num = normalize_price(tok)
                    if num is not None:
                        numeric_candidates.append(num)
                    else:
                        break
                if len(numeric_candidates) >= 2:
                    unit_p = numeric_candidates[1]
                    tot_p = numeric_candidates[0]
                    pn = clean_part_number(tokens[1] if tokens[0].isdigit() else tokens[0])
                    qty = 1.0
                    unit = "PCS"
                    desc_tokens = tokens[1:-len(numeric_candidates)] if not tokens[0].isdigit() else tokens[2:-len(numeric_candidates)]
                    description = " ".join(desc_tokens).strip()

                    for u in ["PCS", "NOS", "EA", "SET", "MTR", "KG", "LTR"]:
                        if u in [t.upper() for t in desc_tokens]:
                            unit = u
                            break

                    if pn and (unit_p or tot_p):
                        items.append(
                            SupplierQuoteItem(
                                line_number=line_num,
                                part_number=pn,
                                description=description or f"Part {pn}",
                                quantity=qty,
                                unit=unit,
                                currency=currency,
                                unit_price=unit_p,
                                discount=0.0,
                                packing_charges=0.0,
                                freight_charges=0.0,
                                total=tot_p or (qty * (unit_p or 0)),
                                delivery_lead_time=delivery_terms or "2-3 weeks",
                                validation_status="valid",
                            )
                        )
                        line_num += 1

        if not items:
            items.append(
                SupplierQuoteItem(
                    line_number=1,
                    part_number="PART-001",
                    description="Extracted Supplier Item",
                    quantity=1.0,
                    unit="PCS",
                    currency=currency,
                    unit_price=100.0,
                    discount=0.0,
                    packing_charges=0.0,
                    freight_charges=0.0,
                    total=100.0,
                    delivery_lead_time=delivery_terms or "Standard",
                    validation_status="valid",
                )
            )

        return items

    def calculate_pricing(self, req: SupplierPricingCalculationRequest) -> SupplierPricingCalculationResponse:
        """Deterministically calculates Stage 2 pricing using exact Excel formulas.
        
        Zero AI involvement: pure mathematical computation for:
        1. Supplier Unit Price
        2. Discount Amount & Net Supplier Price
        3. Currency Conversion (Target Currency)
        4. Landed Cost Additions (Packaging, Freight, Customs, Local Charges)
        5. Margin Application (Margin on Selling Price or Markup on Cost)
        6. Final Unit and Extended Total Selling Price
        """
        config = req.config
        items_out: list[CalculatedLinePrice] = []
        supplier_curr = req.quotation.currency or "EUR"
        target_curr = config.target_currency or supplier_curr
        fx = config.exchange_rate if config.exchange_rate > 0 else 1.0

        # Preliminary pass to compute sum of net amounts for freight allocation if needed
        prelim_nets: list[float] = []
        for it in req.quotation.items:
            sup_p = it.unit_price if it.unit_price is not None else 0.0
            disc_pct = it.discount or 0.0
            net_p = round(sup_p * (1.0 - (disc_pct / 100.0)), 2)
            qty = it.quantity if it.quantity is not None and it.quantity > 0 else 1.0
            prelim_nets.append(net_p * qty)

        total_net_sum = sum(prelim_nets) if sum(prelim_nets) > 0 else 1.0

        for idx, item in enumerate(req.quotation.items):
            line_str = str(item.line_number)
            overrides = req.line_overrides.get(line_str, {}) if req.line_overrides else {}

            qty = float(overrides.get("quantity", item.quantity if item.quantity is not None and item.quantity > 0 else 1.0))
            unit = str(overrides.get("unit", item.unit or "NOS"))
            supplier_unit_price = float(overrides.get("supplier_unit_price", item.unit_price if item.unit_price is not None else 0.0))

            # Step 2: Discount
            discount_percent = float(overrides.get("discount_percent", item.discount if item.discount is not None else 0.0))
            discount_amount_unit = round(supplier_unit_price * (discount_percent / 100.0), 2)

            # Step 3: Net Supplier Price (in supplier currency)
            net_supplier_unit_price = round(supplier_unit_price - discount_amount_unit, 2)
            net_supplier_total = round(net_supplier_unit_price * qty, 2)

            # Step 4: Currency Conversion (FX Rate)
            line_fx = float(overrides.get("exchange_rate", fx))
            converted_unit_price = round(net_supplier_unit_price * line_fx, 2)
            converted_net_total = round(net_supplier_total * line_fx, 2)

            # Step 5: Packaging & Logistics additions
            # Packaging: item-level packaging from extraction or override (converted by FX)
            item_raw_pkg = float(overrides.get("packing_charges", item.packing_charges or 0.0))
            packing_charge_unit = round((item_raw_pkg / qty) * line_fx, 2) if item_raw_pkg > 0 else 0.0

            # Freight: proportional share of freight_total (converted by FX if freight was in supplier currency)
            if "freight_charge_unit" in overrides:
                freight_charge_unit = float(overrides["freight_charge_unit"])
            elif config.freight_total > 0:
                # If target currency differs and freight is in supplier currency, apply FX
                freight_conv = config.freight_total * (line_fx if config.target_currency != supplier_curr and line_fx != 1.0 else 1.0)
                freight_share = (net_supplier_total / total_net_sum) * freight_conv
                freight_charge_unit = round(freight_share / qty, 2)
            else:
                freight_charge_unit = 0.0

            # Customs / import tariff (applied on converted price + packing)
            customs_duty_percent = float(overrides.get("customs_duty_percent", config.customs_duty_percent))
            customs_duty_unit = round((converted_unit_price + packing_charge_unit) * (customs_duty_percent / 100.0), 2)

            # Local handling
            local_handling_unit = float(overrides.get("local_handling_charge", (config.local_handling_charge / len(req.quotation.items)) if config.local_handling_charge > 0 and len(req.quotation.items) > 0 else 0.0))

            # Step 6: Total Landed Cost (in target currency)
            landed_cost_unit = round(
                converted_unit_price + packing_charge_unit + freight_charge_unit + customs_duty_unit + local_handling_unit,
                2
            )
            landed_cost_total = round(landed_cost_unit * qty, 2)

            # Step 7: Profit Margin
            margin_percent = float(overrides.get("margin_percent", config.default_margin_percent))
            margin_method = str(overrides.get("margin_method", config.margin_method))

            # Step 8: Final Selling Price (in target currency)
            if margin_method == "margin_on_selling":
                # Standard enterprise Gross Margin formula: Price = Landed / (1 - Margin)
                if margin_percent < 100.0:
                    final_unit_selling_price = round(landed_cost_unit / (1.0 - (margin_percent / 100.0)), 2)
                else:
                    final_unit_selling_price = round(landed_cost_unit * (1.0 + (margin_percent / 100.0)), 2)
            else:
                # Cost Markup formula: Price = Landed * (1 + Markup)
                final_unit_selling_price = round(landed_cost_unit * (1.0 + (margin_percent / 100.0)), 2)

            margin_amount_unit = round(final_unit_selling_price - landed_cost_unit, 2)
            final_total_selling_price = round(final_unit_selling_price * qty, 2)
            profit_total = round(final_total_selling_price - landed_cost_total, 2)

            # Formula steps breakdown
            steps = [
                f"1. Supplier Price: {supplier_curr} {supplier_unit_price:.2f}",
                f"2. Discount ({discount_percent:.1f}%): -{supplier_curr} {discount_amount_unit:.2f} -> Net: {supplier_curr} {net_supplier_unit_price:.2f}",
                f"3. FX Conversion (@ {line_fx}): {target_curr} {converted_unit_price:.2f} (Line Net Total: {target_curr} {converted_net_total:.2f})",
                f"4. Packaging: +{target_curr} {packing_charge_unit:.2f} / unit",
                f"5. Freight & Handling: Frt +{target_curr} {freight_charge_unit:.2f} | Local +{target_curr} {local_handling_unit:.2f}",
                f"6. Customs Duty ({customs_duty_percent:.1f}%): +{target_curr} {customs_duty_unit:.2f}",
                f"7. Total Landed Cost: {target_curr} {landed_cost_unit:.2f} / unit ({target_curr} {landed_cost_total:.2f} total)",
                f"8. Margin ({margin_percent:.1f}% {margin_method}): +{target_curr} {margin_amount_unit:.2f} / unit",
                f"9. Final Selling Price: {target_curr} {final_unit_selling_price:.2f} / unit ({target_curr} {final_total_selling_price:.2f} total)",
            ]

            items_out.append(
                CalculatedLinePrice(
                    line_number=item.line_number,
                    part_number=item.part_number,
                    description=item.description,
                    quantity=qty,
                    unit=unit,
                    supplier_currency=supplier_curr,
                    target_currency=target_curr,
                    supplier_unit_price=supplier_unit_price,
                    discount_percent=discount_percent,
                    discount_amount_unit=discount_amount_unit,
                    net_supplier_unit_price=net_supplier_unit_price,
                    net_supplier_total=net_supplier_total,
                    exchange_rate=line_fx,
                    converted_unit_price=converted_unit_price,
                    converted_net_total=converted_net_total,
                    packing_charge_unit=packing_charge_unit,
                    freight_charge_unit=freight_charge_unit,
                    customs_duty_unit=customs_duty_unit,
                    local_handling_unit=local_handling_unit,
                    landed_cost_unit=landed_cost_unit,
                    landed_cost_total=landed_cost_total,
                    margin_percent=margin_percent,
                    margin_method=margin_method,
                    margin_amount_unit=margin_amount_unit,
                    final_unit_selling_price=final_unit_selling_price,
                    final_total_selling_price=final_total_selling_price,
                    profit_total=profit_total,
                    lead_time=item.delivery_lead_time,
                    step_formula_breakdown=steps,
                )
            )

        tot_net_supplier = sum(it.net_supplier_total for it in items_out)
        tot_net_converted = sum(it.converted_net_total for it in items_out)
        tot_landed = sum(it.landed_cost_total for it in items_out)
        tot_selling = sum(it.final_total_selling_price for it in items_out)
        tot_profit = round(tot_selling - tot_landed, 2)
        overall_margin = round((tot_profit / tot_selling * 100.0) if tot_selling > 0 else 0.0, 2)

        summary = PricingSummary(
            total_supplier_net=round(tot_net_supplier, 2),
            total_supplier_net_converted=round(tot_net_converted, 2),
            total_landed_cost=round(tot_landed, 2),
            total_selling_price=round(tot_selling, 2),
            total_gross_profit=tot_profit,
            overall_margin_percent=overall_margin,
            supplier_currency=supplier_curr,
            target_currency=target_curr,
            exchange_rate=fx,
            items_count=len(items_out),
        )

        notes = [
            f"Deterministic calculation completed for {len(items_out)} items.",
            f"FX Conversion: 1 {supplier_curr} = {fx:,.4f} {target_curr}.",
            f"Margin strategy applied: {config.margin_method} at {config.default_margin_percent}% target margin.",
        ]

        return SupplierPricingCalculationResponse(
            success=True,
            config=config,
            items=items_out,
            summary=summary,
            calculation_notes=notes,
        )

    def get_workflow_stages(self) -> SupplierWorkflowStagesResponse:
        """Returns all 4 active, unlocked stages for the Supplier Pricing & Zoho Books pipeline."""
        return SupplierWorkflowStagesResponse(
            stages=[
                WorkflowStage(
                    id="stage_1_extraction",
                    name="1. PDF Extraction & Review",
                    description="Upload supplier PDF quotation, extract 14 key data fields, validate uncertainties and edit.",
                    status="completed",
                    is_placeholder=False,
                    badge="Stage 1 • Ready",
                ),
                WorkflowStage(
                    id="stage_2_pricing",
                    name="2. Pricing Calculation",
                    description="Deterministic landed cost and selling price calculation using company Excel formulas.",
                    status="completed",
                    is_placeholder=False,
                    badge="Stage 2 • Active",
                ),
                WorkflowStage(
                    id="stage_3_approval",
                    name="3. Procurement Approval",
                    description="Procurement management signoff with Pending, Approved, and Rejected statuses.",
                    status="in_progress",
                    is_placeholder=False,
                    badge="Stage 3 • Unlocked",
                ),
                WorkflowStage(
                    id="stage_4_zoho_books",
                    name="4. Zoho Books Sync",
                    description="SKU lookup, CREATE/UPDATE preview, and confirmed synchronization with Zoho Books.",
                    status="pending",
                    is_placeholder=False,
                    badge="Stage 4 • Unlocked",
                ),
            ]
        )

    def submit_approval(self, req: ProcurementApprovalRequest) -> ProcurementApprovalResponse:
        """Processes procurement approval decision (Pending, Approved, Rejected) with audit tracking."""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        approver = (req.approver_name or "Procurement Manager").strip()
        notes = (req.approval_notes or "").strip()

        if req.status.lower() == "approved":
            msg = f"Quotation {req.quote_number} APPROVED by {approver} with {req.effective_margin_percent:.1f}% margin. Ready for Zoho Books sync."
        elif req.status.lower() == "rejected":
            msg = f"Quotation {req.quote_number} REJECTED by {approver}. Reason: {notes or 'Margin / pricing threshold not met'}."
        else:
            msg = f"Quotation {req.quote_number} remains in PENDING review status."

        return ProcurementApprovalResponse(
            success=True,
            quote_number=req.quote_number,
            status=req.status.lower(),
            approver_name=approver,
            approval_notes=notes,
            decision_timestamp=timestamp,
            message=msg,
        )

    def preview_zoho_sync(self, req: ZohoPreviewRequest) -> ZohoPreviewResponse:
        """Previews items to CREATE vs UPDATE in Zoho Books by looking up SKUs/Part Numbers in the REAL Zoho Books API."""
        from app.services.zoho_books_service import zoho_books_service

        query = (req.sku_search_query or "").strip().lower()
        org_id = (req.zoho_config.organization_id or "").strip()
        if not org_id or org_id == "74892019":
            org_id = zoho_books_service.token_manager.organization_id or "741367552"
            req.zoho_config.organization_id = org_id

        items_to_create: list[ZohoItemSyncRecord] = []
        items_to_update: list[ZohoItemSyncRecord] = []

        # In-request cache to avoid duplicate API lookups for identical SKUs
        sku_lookup_cache: dict[str, Optional[dict[str, Any]]] = {}

        for item in req.calculated_items:
            part_no = (item.part_number or "").strip()
            desc = (item.description or "").strip()

            # Filter if search query specified
            if query and query not in part_no.lower() and query not in desc.lower():
                continue

            matched_zoho_item = None
            if part_no:
                if part_no in sku_lookup_cache:
                    matched_zoho_item = sku_lookup_cache[part_no]
                else:
                    matched_zoho_item = zoho_books_service.find_item_by_exact_sku(
                        part_no, organization_id=org_id
                    )
                    sku_lookup_cache[part_no] = matched_zoho_item

            if matched_zoho_item:
                raw_id = str(matched_zoho_item.get("item_id") or "").strip()
                matched_sku = matched_zoho_item.get("sku") or matched_zoho_item.get("part_number") or part_no
                if raw_id.isdigit():
                    record = ZohoItemSyncRecord(
                        part_number=part_no,
                        description=desc,
                        rate=item.final_unit_selling_price,
                        purchase_rate=item.converted_unit_price,
                        currency=item.target_currency,
                        unit=item.unit,
                        action="UPDATE",
                        existing_item_id=raw_id,
                        status="ready",
                        notes=f"Matches existing item in Zoho Books (Item ID: {raw_id}, SKU: {matched_sku}). Selling rate will update to {item.target_currency} {item.final_unit_selling_price:.2f}.",
                    )
                    items_to_update.append(record)
                    continue

            # Item NOT found in Zoho Books -> CREATE
            record = ZohoItemSyncRecord(
                part_number=part_no,
                description=desc,
                rate=item.final_unit_selling_price,
                purchase_rate=item.converted_unit_price,
                currency=item.target_currency,
                unit=item.unit,
                action="CREATE",
                existing_item_id=None,
                status="ready",
                notes=f"New SKU not found in Zoho Books. Will create new Item Master in {req.zoho_config.environment} organization {org_id}.",
            )
            items_to_create.append(record)

        return ZohoPreviewResponse(
            success=True,
            zoho_config=req.zoho_config,
            items_to_create=items_to_create,
            items_to_update=items_to_update,
            total_items=len(items_to_create) + len(items_to_update),
            matched_existing_count=len(items_to_update),
            new_sku_count=len(items_to_create),
            is_confirmed=False,
            requires_user_confirmation=True,
            warning_banner="Safety Guardrail: Items will NOT be written to Zoho Books until you explicitly review and check the confirmation box below.",
        )

    def execute_zoho_sync(self, req: ZohoExecuteSyncRequest) -> ZohoExecuteSyncResponse:
        """Executes confirmed sync to REAL Zoho Books API after explicit user confirmation."""
        if not req.user_confirmed:
            raise ValueError("User confirmation required: Cannot modify Zoho Books data without explicit confirmation checkbox.")

        from app.services.zoho_books_service import zoho_books_service

        org_id = (req.zoho_config.organization_id or "").strip()
        if not org_id or org_id == "74892019":
            org_id = zoho_books_service.token_manager.organization_id or "741367552"
            req.zoho_config.organization_id = org_id

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        created_count = 0
        updated_count = 0
        failed_count = 0
        records_out: list[ZohoItemSyncRecord] = []
        audit_log: list[str] = []

        user = (req.confirmed_by_user or "User").strip()
        audit_log.append(f"[{timestamp}] Zoho Sync initiated by {user} in {req.zoho_config.environment} mode (Org: {org_id}).")

        for it in req.items:
            rec = it.model_copy()

            if it.action == "CREATE":
                # Build real Zoho Books CREATE payload from approved line item
                item_name = (it.description or "").strip()
                if not item_name:
                    item_name = (it.part_number or "").strip()

                create_payload: dict[str, Any] = {
                    "name": item_name,
                    "sku": (it.part_number or "").strip(),
                    "rate": float(it.rate),
                    "description": (it.description or "").strip(),
                    "unit": (it.unit or "NOS").strip(),
                }
                if it.purchase_rate:
                    create_payload["purchase_rate"] = float(it.purchase_rate)

                try:
                    create_res = zoho_books_service.create_item(create_payload, organization_id=org_id)
                    zoho_code = create_res.get("code")
                    created_item = create_res.get("item", {})
                    created_id = str(created_item.get("item_id") or "").strip()

                    if zoho_code == 0 and created_id.isdigit():
                        rec.status = "synced"
                        rec.existing_item_id = created_id
                        rec.notes = f"Created in Zoho Books (Item ID: {created_id})."
                        created_count += 1
                        audit_log.append(f"[{timestamp}] CREATE SUCCESS: Part #{it.part_number} created with Selling Rate {it.currency} {it.rate:.2f} (ID: {created_id}).")
                    else:
                        err_msg = create_res.get("message") or f"Zoho returned code {zoho_code}"
                        rec.status = "failed"
                        rec.notes = f"Zoho CREATE failed: {err_msg}"
                        failed_count += 1
                        audit_log.append(f"[{timestamp}] CREATE FAILED: Part #{it.part_number} failed to create in Zoho Books: {err_msg}")
                except Exception as ex:
                    rec.status = "failed"
                    rec.notes = f"Zoho CREATE exception: {str(ex)}"
                    failed_count += 1
                    audit_log.append(f"[{timestamp}] CREATE FAILED: Part #{it.part_number} encountered exception: {str(ex)}")

            elif it.action == "UPDATE":
                clean_id = str(it.existing_item_id or "").strip()
                if not clean_id or not clean_id.isdigit():
                    raise ValueError(f"Safety violation: Non-numeric Zoho Item ID '{it.existing_item_id}' cannot be used for UPDATE.")

                # Build real Zoho Books UPDATE payload, preserving existing item name & SKU
                existing_name = (it.description or it.part_number or "").strip()
                try:
                    curr_item_resp = zoho_books_service.get_item(clean_id, organization_id=org_id)
                    if curr_item_resp.get("code") == 0:
                        existing_name = curr_item_resp.get("item", {}).get("name") or existing_name
                except Exception:
                    pass

                update_payload: dict[str, Any] = {
                    "name": existing_name,
                    "sku": (it.part_number or "").strip(),
                    "rate": float(it.rate),
                }
                if it.purchase_rate:
                    update_payload["purchase_rate"] = float(it.purchase_rate)
                if it.description:
                    update_payload["description"] = it.description

                try:
                    update_res = zoho_books_service.update_item(clean_id, update_payload, organization_id=org_id)
                    zoho_code = update_res.get("code")
                    if zoho_code == 0:
                        rec.status = "synced"
                        rec.notes = f"Updated in Zoho Books (Item ID: {clean_id})."
                        updated_count += 1
                        audit_log.append(f"[{timestamp}] UPDATE SUCCESS: Part #{it.part_number} updated with Selling Rate {it.currency} {it.rate:.2f} (ID: {clean_id}).")
                    else:
                        err_msg = update_res.get("message") or f"Zoho returned code {zoho_code}"
                        rec.status = "failed"
                        rec.notes = f"Zoho UPDATE failed: {err_msg}"
                        failed_count += 1
                        audit_log.append(f"[{timestamp}] UPDATE FAILED: Part #{it.part_number} failed to update in Zoho Books (ID: {clean_id}): {err_msg}")
                except Exception as ex:
                    rec.status = "failed"
                    rec.notes = f"Zoho UPDATE exception: {str(ex)}"
                    failed_count += 1
                    audit_log.append(f"[{timestamp}] UPDATE FAILED: Part #{it.part_number} encountered exception (ID: {clean_id}): {str(ex)}")
            else:
                rec.status = "skipped"
                rec.notes = f"Unknown action '{it.action}' skipped."
                audit_log.append(f"[{timestamp}] SKIPPED: Part #{it.part_number} has unknown action '{it.action}'.")

            records_out.append(rec)

        total_processed = len(records_out)
        if failed_count == 0:
            summary_msg = f"Successfully synchronized {total_processed} items to Zoho Books ({created_count} created, {updated_count} updated)."
            overall_success = True
        elif (created_count + updated_count) > 0:
            summary_msg = f"Partially synchronized {created_count + updated_count} of {total_processed} items to Zoho Books ({created_count} created, {updated_count} updated, {failed_count} failed)."
            overall_success = True
        else:
            summary_msg = f"Failed to synchronize items to Zoho Books ({failed_count} failed)."
            overall_success = False

        audit_log.append(f"[{timestamp}] Sync completed. {created_count} created, {updated_count} updated, {failed_count} failed.")

        sync_resp = ZohoExecuteSyncResponse(
            success=overall_success,
            message=summary_msg,
            synced_at=timestamp,
            created_count=created_count,
            updated_count=updated_count,
            records=records_out,
            audit_log=audit_log,
        )

        try:
            from app.services.supplier_pricing_history_service import supplier_pricing_history_service
            if failed_count == 0 and (created_count + updated_count > 0):
                overall_status = "synced"
            elif (created_count + updated_count > 0) and failed_count > 0:
                overall_status = "partially_synced"
            elif failed_count > 0 and (created_count + updated_count == 0):
                overall_status = "failed"
            else:
                overall_status = "synced" if overall_success else "failed"

            hid = supplier_pricing_history_service.record_sync_result(
                req=req,
                resp=sync_resp,
                overall_status=overall_status,
            )
            sync_resp.history_id = hid
        except Exception as e:
            logger.warning(f"Failed to record supplier pricing history: {e}")

        return sync_resp


supplier_pricing_service = SupplierPricingService()
