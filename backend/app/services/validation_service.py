import logging
from typing import Tuple

from app.schemas.quotation import (
    QuotationData,
    ValidationSummary,
    ValidationIssue,
)

logger = logging.getLogger(__name__)


NON_INVENTORY_CHARGE_CODES = {
    "S&H", "SHIPPING", "HANDLING", "FREIGHT", "PACKAGING", "MISC", "MISCELLANEOUS",
    "SERVICE", "SERVICE FEE", "N/A", "NONE", "-", "PACKING", "DELIVERY", "TRANSPORT",
    "PACKING & FORWARDING", "P&F", "INSURANCE", "DOC FEE", "DOCUMENTATION",
}

NON_INVENTORY_KEYWORDS = [
    "SHIPPING & HANDLING", "SHIPPING AND HANDLING", "SHIPPING CHARGE", "SHIPPING CHARGES",
    "FREIGHT CHARGE", "FREIGHT CHARGES", "DELIVERY CHARGE", "DELIVERY CHARGES",
    "PACKAGING CHARGE", "PACKAGING CHARGES", "PACKAGING COST", "PACKAGING COSTS",
    "HANDLING CHARGE", "HANDLING CHARGES", "SERVICE CHARGE", "SERVICE FEE",
    "DOCUMENTATION FEE", "PACKING & FORWARDING", "TRANSPORTATION CHARGES",
    "FREIGHT & INSURANCE", "RESTOCKING FEE", "MISCELLANEOUS CHARGE",
]


def is_non_inventory_charge(item) -> bool:
    """Returns True if the line item represents a non-inventory charge (freight, shipping,
    handling, packaging, service fee, etc.) rather than a physical stock/OEM part number."""
    if getattr(item, "item_type", None) in ("charge", "service", "freight", "shipping", "non_inventory"):
        return True
    
    pn_clean = (item.part_number or "").strip().upper()
    if pn_clean in NON_INVENTORY_CHARGE_CODES:
        return True
    
    desc_upper = (item.description or "").upper()
    if any(kw in desc_upper for kw in NON_INVENTORY_KEYWORDS):
        return True
        
    if not pn_clean and any(w in desc_upper for w in ["SHIPPING", "FREIGHT", "HANDLING", "PACKAGING", "DELIVERY", "MISCELLANEOUS", "LABOR", "SERVICE"]):
        return True

    return False


class ValidationService:
    """Deterministic validation engine for quotation extraction."""

    def validate_quotation(
        self, quotation: QuotationData, raw_pdf_text: str = ""
    ) -> Tuple[QuotationData, ValidationSummary]:
        logger.info(f"Starting deterministic validation for quote {quotation.quote_number or 'unnamed'}")
        
        issues: list[ValidationIssue] = []
        errors_count = 0
        warnings_count = 0
        raw_text_lower = (raw_pdf_text or quotation.raw_pdf_text or "").lower()

        total_confidence_points = 0.0
        total_fields_checked = 0
        price_validation_passed = 0
        part_number_validation_passed = 0
        seen_line_numbers = set()

        # 1. Check Duplicate Line Numbers
        for item in quotation.items:
            if item.line_number in seen_line_numbers:
                issues.append(
                    ValidationIssue(
                        item_line=item.line_number,
                        field="line_number",
                        issue_type="error",
                        message=f"Duplicate line number detected: {item.line_number}.",
                        actual_value=item.line_number,
                    )
                )
                errors_count += 1
            seen_line_numbers.add(item.line_number)

        # 2. Validate line items
        for item in quotation.items:
            item_status = "verified"
            item_notes: list[str] = []
            item_confidence: dict[str, float] = {}

            # Part Number Validation
            pn = item.part_number.strip() if item.part_number else ""
            is_charge = is_non_inventory_charge(item)

            if is_charge:
                # Legitimate non-inventory charge line (e.g. S&H, Shipping & Handling, Freight)
                item.item_type = "charge"
                label = pn if pn else "Charge"
                issues.append(
                    ValidationIssue(
                        item_line=item.line_number,
                        field="part_number",
                        issue_type="info",
                        message=f"Line {item.line_number} ({label}): Recognized as a non-inventory charge ({item.description or 'shipping/handling'}) — OEM stock part number not required.",
                        actual_value=pn,
                    )
                )
                item_confidence["part_number"] = 1.0
                part_number_validation_passed += 1
                item_notes.append(f"Non-inventory charge ({label})")
            elif not pn:
                # True extraction failure on a physical part item
                issues.append(
                    ValidationIssue(
                        item_line=item.line_number,
                        field="part_number",
                        issue_type="error",
                        message=f"Line {item.line_number}: Missing part number.",
                    )
                )
                errors_count += 1
                item_status = "error"
                item_confidence["part_number"] = 0.0
            elif pn.startswith("848190") and "commodity" in (item.description or "").lower():
                issues.append(
                    ValidationIssue(
                        item_line=item.line_number,
                        field="part_number",
                        issue_type="error",
                        message=f"Line {item.line_number}: Commodity code was mistakenly extracted as a line item.",
                        actual_value=pn,
                    )
                )
                errors_count += 1
                item_status = "error"
                item_confidence["part_number"] = 0.0
            else:
                if raw_text_lower and pn.lower() in raw_text_lower:
                    item_confidence["part_number"] = 1.0
                    part_number_validation_passed += 1
                elif raw_text_lower:
                    issues.append(
                        ValidationIssue(
                            item_line=item.line_number,
                            field="part_number",
                            issue_type="warning",
                            message=f"Line {item.line_number}: Part number '{pn}' not explicitly found in raw PDF text.",
                            actual_value=pn,
                        )
                    )
                    warnings_count += 1
                    item_confidence["part_number"] = 0.6
                    if item_status != "error":
                        item_status = "warning"
                    item_notes.append("Part number may need manual verification against PDF")
                else:
                    item_confidence["part_number"] = 0.9
                    part_number_validation_passed += 1


            # Quantity Validation
            if item.quantity is None:
                issues.append(
                    ValidationIssue(
                        item_line=item.line_number,
                        field="quantity",
                        issue_type="warning",
                        message=f"Line {item.line_number}: Missing quantity.",
                        actual_value=None,
                    )
                )
                warnings_count += 1
                item_status = "warning"
                item_confidence["quantity"] = 0.5
                item_notes.append("Quantity is missing")
            elif item.quantity < 0:
                issues.append(
                    ValidationIssue(
                        item_line=item.line_number,
                        field="quantity",
                        issue_type="error",
                        message=f"Line {item.line_number}: Quantity cannot be negative ({item.quantity}).",
                        actual_value=item.quantity,
                    )
                )
                errors_count += 1
                item_status = "error"
                item_confidence["quantity"] = 0.0
            else:
                item_confidence["quantity"] = 1.0

            # Unit Price Validation
            if item.unit_price is None:
                issues.append(
                    ValidationIssue(
                        item_line=item.line_number,
                        field="unit_price",
                        issue_type="warning",
                        message=f"Line {item.line_number}: Missing unit price.",
                        actual_value=None,
                    )
                )
                warnings_count += 1
                item_status = "warning"
                item_confidence["unit_price"] = 0.5
                item_notes.append("Unit price is missing")
            elif item.unit_price < 0:
                issues.append(
                    ValidationIssue(
                        item_line=item.line_number,
                        field="unit_price",
                        issue_type="error",
                        message=f"Line {item.line_number}: Unit price cannot be negative ({item.unit_price}).",
                        actual_value=item.unit_price,
                    )
                )
                errors_count += 1
                item_status = "error"
                item_confidence["unit_price"] = 0.0
            else:
                item_confidence["unit_price"] = 1.0

            # Discount Validation
            discount = item.discount_percent or 0.0
            if discount < 0 or discount > 100:
                issues.append(
                    ValidationIssue(
                        item_line=item.line_number,
                        field="discount_percent",
                        issue_type="error",
                        message=f"Line {item.line_number}: Invalid discount percent ({discount}%). Must be 0-100%.",
                        actual_value=discount,
                    )
                )
                errors_count += 1
                item_status = "error"
                item_confidence["discount"] = 0.0
            else:
                item_confidence["discount"] = 1.0

            # Total Price Arithmetic Check (VALIDATION ONLY - NEVER OVERWRITE PDF TOTAL)
            if item.quantity is not None and item.unit_price is not None:
                expected_total = round(item.quantity * item.unit_price * (1.0 - (discount / 100.0)), 2)
                actual_total = item.total_price if item.total_price is not None else expected_total

                if abs(actual_total - expected_total) > 0.08 and item.unit_price > 0 and item.quantity > 0:
                    issues.append(
                        ValidationIssue(
                            item_line=item.line_number,
                            field="total_price",
                            issue_type="warning",
                            message=f"Line {item.line_number}: Calculation mismatch (Qty {item.quantity} × Price {item.unit_price} with {discount}% discount = {expected_total}, extracted: {actual_total}).",
                            expected_value=expected_total,
                            actual_value=actual_total,
                        )
                    )
                    warnings_count += 1
                    item_confidence["total_price"] = 0.7
                    if item_status == "verified":
                        item_status = "warning"
                    item_notes.append(f"Price mismatch: Expected ~{expected_total}")
                else:
                    item_confidence["total_price"] = 1.0
                    price_validation_passed += 1
            else:
                item_confidence["total_price"] = 0.8

            # Assign item fields
            item.confidence = item_confidence
            item.status = item_status
            item.validation_notes = item_notes

            for conf_val in item_confidence.values():
                total_confidence_points += conf_val
                total_fields_checked += 1

        # 3. Overall Quote Grand Total Check
        calculated_lines_sum = sum(
            it.total_price if it.total_price is not None else ((it.quantity or 0.0) * (it.unit_price or 0.0))
            for it in quotation.items
        )
        calculated_lines_sum = round(calculated_lines_sum, 2)
        
        extracted_lines_total = quotation.lines_total if quotation.lines_total is not None else calculated_lines_sum
        if abs(calculated_lines_sum - extracted_lines_total) > 0.15 and quotation.items:
            issues.append(
                ValidationIssue(
                    field="lines_total",
                    issue_type="warning",
                    message=f"Sum of line items ({calculated_lines_sum}) differs from quotation header lines total ({extracted_lines_total}).",
                    expected_value=calculated_lines_sum,
                    actual_value=extracted_lines_total,
                )
            )
            warnings_count += 1

        pkg = quotation.packaging_cost or 0.0
        misc = quotation.miscellaneous_charges or 0.0
        
        # Check charge reconciliation: in some supplier quotes (like DMN), packaging is the miscellaneous charge
        if quotation.grand_total is not None and quotation.items:
            # Candidate 1: lines_total + packaging + misc
            cand1 = round(extracted_lines_total + pkg + misc, 2)
            # Candidate 2: lines_total + packaging (where misc is summary category for packaging)
            cand2 = round(extracted_lines_total + pkg, 2)
            # Candidate 3: lines_total + misc
            cand3 = round(extracted_lines_total + misc, 2)

            actual_gt = quotation.grand_total
            if abs(actual_gt - cand1) <= 0.15:
                expected_grand_total = cand1
            elif abs(actual_gt - cand2) <= 0.15:
                expected_grand_total = cand2
            elif abs(actual_gt - cand3) <= 0.15:
                expected_grand_total = cand3
            else:
                expected_grand_total = cand1
                issues.append(
                    ValidationIssue(
                        field="grand_total",
                        issue_type="warning",
                        message=f"Grand total ({quotation.grand_total}) does not match calculated sum ({expected_grand_total}).",
                        expected_value=expected_grand_total,
                        actual_value=quotation.grand_total,
                    )
                )
                warnings_count += 1
        else:
            expected_grand_total = round(extracted_lines_total + pkg + misc, 2)

        overall_confidence = (
            round(total_confidence_points / total_fields_checked, 2)
            if total_fields_checked > 0
            else 1.0
        )

        total_items = len(quotation.items)
        pdf_count = quotation.pdf_item_count or total_items
        extracted_count = quotation.extracted_item_count or total_items

        validation_summary = ValidationSummary(
            is_valid=(errors_count == 0),
            overall_confidence=overall_confidence,
            errors_count=errors_count,
            warnings_count=warnings_count,
            pdf_item_count=pdf_count,
            extracted_item_count=extracted_count,
            items_ready_for_excel=total_items,
            currency=quotation.currency or "EUR",
            currency_symbol=quotation.currency_symbol or "€",
            price_validation_passed=price_validation_passed,
            part_number_validation_passed=part_number_validation_passed,
            total_items_validated=total_items,
            issues=issues,
        )

        return quotation, validation_summary


validation_service = ValidationService()

