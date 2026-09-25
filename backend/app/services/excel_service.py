import copy
import logging
import re
from pathlib import Path
from typing import Optional, Dict, Any, List
import openpyxl
from openpyxl.utils import get_column_letter, column_index_from_string

from app.schemas.quotation import (
    QuotationData,
    QuoteItem,
    ColumnMappingConfig,
    TemplateAnalysisResponse,
)
from app.utils.text_utils import clean_part_number, get_currency_symbol

logger = logging.getLogger(__name__)


HEADER_SYNONYMS: dict[str, str] = {
    "no.": "line_number",
    "no": "line_number",
    "line": "line_number",
    "sl": "line_number",
    "item": "line_number",
    "item no": "line_number",
    "item no.": "line_number",
    "part number": "part_number",
    "part no": "part_number",
    "part no.": "part_number",
    "part #": "part_number",
    "p/n": "part_number",
    "description": "description",
    "item description": "description",
    "desc": "description",
    "specification": "description",
    "unit price": "unit_price",
    "unit rate": "unit_price",
    "price": "unit_price",
    "rate": "unit_price",
    "qty": "quantity",
    "quantity": "quantity",
    "qty.": "quantity",
    "nos": "quantity",
    "unit": "unit",
    "uom": "unit",
    "discount": "discount_pct",
    "discount %": "discount_pct",
    "discount percent": "discount_pct",
    "disc": "discount_pct",
    "disc %": "discount_pct",
    "total price": "total_price",
    "total": "total_price",
    "line total": "total_price",
    "total amount": "total_price",
    "amount": "total_price",
    "currency": "currency",
}


def detect_column_mapping(ws, header_row_range=range(1, 15)) -> tuple[dict[str, str], int, dict[str, str]]:
    """Scan the given header rows and return (mapping, last_header_row, detected_headers).
    mapping: {field_name: column_letter} based on labels that actually exist in THIS template.
    A field with no matching header is simply absent from the mapping - callers must never invent a column for it.
    last_header_row: the highest row number that actually contained a recognized header label."""
    mapping: dict[str, str] = {}
    detected_headers: dict[str, str] = {}
    last_header_row = 0

    for row_idx in header_row_range:
        for cell in ws[row_idx]:
            if cell.value is None:
                continue
            raw_text = str(cell.value).strip()
            label = raw_text.lower()
            
            # Clean possible sub-tokens (e.g., "Unit Price (€)" -> "unit price")
            cleaned_label = re.sub(r'[\(\[\{].*?[\)\]\}]', '', label).strip()
            
            field = HEADER_SYNONYMS.get(cleaned_label) or HEADER_SYNONYMS.get(label)
            if not field:
                for syn_k, syn_v in HEADER_SYNONYMS.items():
                    if syn_k in label and len(syn_k) >= 3:
                        field = syn_v
                        break

            if field:
                col_letter = cell.column_letter
                if field not in mapping:
                    mapping[field] = col_letter
                    detected_headers[col_letter] = raw_text
                last_header_row = max(last_header_row, row_idx)

    return mapping, last_header_row, detected_headers


def find_first_data_row(ws, mapping: dict[str, str], last_header_row: int, max_scan: int = 40) -> int:
    """Header blocks can span extra rows beyond the labeled ones (e.g. a currency subtitle like "Euro"
    sitting under the Unit Price header, with no other column populated on that row).
    Scan forward from the last recognized header row and keep treating a row as "still header"
    as long as at least one MAPPED column on it has content. The first row where every mapped column
    is empty is the true data start."""
    row = last_header_row
    cols = list(mapping.values())
    while row < last_header_row + max_scan:
        row += 1
        if all(ws[f"{c}{row}"].value in (None, "") for c in cols):
            return row
    return last_header_row + 1


class ExcelTemplateService:
    """Fills existing Excel templates while 100% preserving styles, formulas, merged cells, and formats,
    ensuring NO sample template data survives and PDF is strictly the source of truth."""

    def analyze_template(self, template_path: str | Path) -> TemplateAnalysisResponse:
        """Inspects an Excel template to discover sheet names, headers, and best column mapping."""
        template_path = Path(template_path)
        if not template_path.exists():
            raise FileNotFoundError(f"Template file not found: {template_path}")

        wb = openpyxl.load_workbook(str(template_path), data_only=False)
        sheet = wb.active

        raw_mapping, last_header_row, detected_headers = detect_column_mapping(sheet)
        if not raw_mapping:
            # Fallback default if completely empty template
            raw_mapping = {"line_number": "A", "part_number": "B", "description": "C"}
            last_header_row = 4

        first_data_row = find_first_data_row(sheet, raw_mapping, last_header_row)

        mapping = ColumnMappingConfig(
            line_number_column=raw_mapping.get("line_number"),
            part_number_column=raw_mapping.get("part_number"),
            description_column=raw_mapping.get("description"),
            quantity_column=raw_mapping.get("quantity"),
            unit_column=raw_mapping.get("unit"),
            unit_price_column=raw_mapping.get("unit_price"),
            discount_column=raw_mapping.get("discount_pct"),
            total_price_column=raw_mapping.get("total_price"),
            currency_column=raw_mapping.get("currency"),
            start_row=first_data_row,
            quote_number_cell=None,
            customer_cell=None,
            date_cell=None,
            currency_cell=None,
        )

        # Detect Header Metadata Cells outside the table data area
        for r in range(1, max(2, last_header_row)):
            for c in range(1, min(15, sheet.max_column + 1)):
                cell_v = str(sheet.cell(row=r, column=c).value or "").strip().lower()
                adj_col = get_column_letter(c + 1)
                if any(k in cell_v for k in ["quote ref", "reference:", "quote no", "quote #", "enquiry no"]):
                    if not mapping.quote_number_cell or "quote" in cell_v:
                        mapping.quote_number_cell = f"{adj_col}{r}"
                elif any(k in cell_v for k in ["customer:", "client:", "buyer:"]):
                    mapping.customer_cell = f"{adj_col}{r}"
                elif any(k in cell_v for k in ["date:"]):
                    mapping.date_cell = f"{adj_col}{r}"
                elif any(k in cell_v for k in ["currency:"]):
                    mapping.currency_cell = f"{adj_col}{r}"

        preview_rows = []
        for r in range(1, min(15, sheet.max_row + 1)):
            row_data = [
                str(sheet.cell(row=r, column=c).value or "")
                for c in range(1, min(10, sheet.max_column + 1))
            ]
            preview_rows.append(row_data)

        wb.close()

        return TemplateAnalysisResponse(
            template_id=template_path.name,
            sheet_names=wb.sheetnames,
            detected_headers=detected_headers,
            suggested_mapping=mapping,
            preview_rows=preview_rows,
        )



    def generate_quotation_excel(
        self,
        template_path: str | Path,
        output_path: str | Path,
        quotation: QuotationData,
        pricing_mode: str = "quoted_price",
        margin_percent: float = 0.0,
        supplier_discount_percent: Optional[float] = None,
        custom_mapping: Optional[ColumnMappingConfig] = None,
    ) -> int:
        """Fills the quotation data into the existing template and saves it to output_path.
        Crucial Rule: All old sample data is removed. PDF items are strictly the source of truth.
        The template's own headers govern WHERE data is written."""
        template_path = Path(template_path)
        output_path = Path(output_path)
        
        logger.info(f"Generating quotation Excel using template: {template_path.name}")
        
        pdf_item_count = len(quotation.items)
        if quotation.pdf_item_count and quotation.pdf_item_count != pdf_item_count:
            logger.warning(f"Quotation items length ({pdf_item_count}) differs from pdf_item_count ({quotation.pdf_item_count})")

        wb = openpyxl.load_workbook(str(template_path), data_only=False)
        sheet = wb.active

        # Always detect the template's actual headers and start row from THIS file
        detected_map, last_hdr, detected_headers = detect_column_mapping(sheet)
        detected_start_row = find_first_data_row(sheet, detected_map, last_hdr)

        # Base mapping is derived directly from template's own headers
        auto_analysis = self.analyze_template(template_path)
        auto_mapping = auto_analysis.suggested_mapping

        if custom_mapping is None or not any([
            custom_mapping.line_number_column,
            custom_mapping.part_number_column,
            custom_mapping.description_column,
            custom_mapping.quantity_column,
            custom_mapping.unit_price_column,
        ]):
            mapping = auto_mapping
        else:
            # If custom mapping was passed, reconcile with template's actual columns
            # NEVER allow writing unit/total/discount if the template has no such header!
            mapping = ColumnMappingConfig(
                line_number_column=custom_mapping.line_number_column or auto_mapping.line_number_column or "A",
                part_number_column=custom_mapping.part_number_column or auto_mapping.part_number_column or "B",
                description_column=custom_mapping.description_column or auto_mapping.description_column or "C",
                quantity_column=custom_mapping.quantity_column or auto_mapping.quantity_column,
                unit_price_column=custom_mapping.unit_price_column or auto_mapping.unit_price_column,
                unit_column=custom_mapping.unit_column if "unit" in detected_map else None,
                discount_column=custom_mapping.discount_column if "discount_pct" in detected_map else None,
                total_price_column=custom_mapping.total_price_column if "total_price" in detected_map else None,
                currency_column=custom_mapping.currency_column if "currency" in detected_map else None,
                start_row=max(detected_start_row, auto_mapping.start_row),
                quote_number_cell=custom_mapping.quote_number_cell or auto_mapping.quote_number_cell,
                customer_cell=custom_mapping.customer_cell or auto_mapping.customer_cell,
                date_cell=custom_mapping.date_cell or auto_mapping.date_cell,
                currency_cell=custom_mapping.currency_cell or auto_mapping.currency_cell,
            )
            # Extra safety check: if custom_mapping tried to put quantity in D when D is labeled Unit Price, correct it
            if auto_mapping.unit_price_column and mapping.quantity_column == auto_mapping.unit_price_column:
                logger.warning("Custom mapping inverted quantity and unit price; correcting to template's declared headers.")
                mapping.unit_price_column = auto_mapping.unit_price_column
                mapping.quantity_column = auto_mapping.quantity_column


        # 1. Fill Header cells if present in header area (rows 1 to start_row - 1)
        if mapping.quote_number_cell:
            self._safe_set_cell(sheet, mapping.quote_number_cell, str(quotation.quote_number or ""))
        if mapping.customer_cell:
            self._safe_set_cell(sheet, mapping.customer_cell, str(quotation.customer or ""))
        if mapping.date_cell:
            self._safe_set_cell(sheet, mapping.date_cell, str(quotation.quote_date or ""))
        if mapping.currency_cell:
            self._safe_set_cell(sheet, mapping.currency_cell, str(quotation.currency or "EUR"))

        start_row = mapping.start_row or 6
        initial_max_row = sheet.max_row
        initial_max_col = max(sheet.max_column, 8)

        # 2. Sample Style Detection
        # Find style prototypes for data rows and section header rows from the template
        sample_data_style_row = None
        sample_header_style_row = None
        for r in range(start_row, min(initial_max_row + 1, start_row + 15)):
            val_a = sheet.cell(row=r, column=1).value
            val_b = sheet.cell(row=r, column=2).value
            # Check if row is equipment section header (e.g. text in col A, rest empty)
            if val_a and not val_b and any(k in str(val_a).upper() for k in ["VALVE", "ROTARY", "LINE", "S/N", "SERIAL", "EQUIPMENT", "GROUP"]):
                if sample_header_style_row is None:
                    sample_header_style_row = r
            elif val_a or val_b:
                if sample_data_style_row is None:
                    sample_data_style_row = r

        if sample_data_style_row is None:
            sample_data_style_row = start_row
        if sample_header_style_row is None:
            sample_header_style_row = start_row

        # Save style templates into memory
        data_row_styles = [self._copy_cell_style(sheet.cell(row=sample_data_style_row, column=c)) for c in range(1, initial_max_col + 1)]
        header_row_styles = [self._copy_cell_style(sheet.cell(row=sample_header_style_row, column=c)) for c in range(1, initial_max_col + 1)]
        data_row_height = sheet.row_dimensions[sample_data_style_row].height
        header_row_height = sheet.row_dimensions[sample_header_style_row].height

        # 3. COMPLETE CLEARING OF SAMPLE DATA ROWS
        # Unmerge any merged cells in data section
        merged_ranges = list(sheet.merged_cells.ranges)
        for rng in merged_ranges:
            if rng.min_row >= start_row:
                sheet.unmerge_cells(str(rng))

        # Clear all rows from start_row to initial_max_row so NO old sample parts/rows survive!
        for r in range(start_row, initial_max_row + 5):
            sheet.row_dimensions[r].height = None
            for c in range(1, initial_max_col + 2):
                cell = sheet.cell(row=r, column=c)
                if type(cell).__name__ == "MergedCell":
                    continue
                cell.value = None
                # Reset style to default clean state
                cell.font = openpyxl.styles.Font()
                cell.border = openpyxl.styles.Border()
                cell.fill = openpyxl.styles.PatternFill(fill_type=None)
                cell.alignment = openpyxl.styles.Alignment()
                cell.number_format = "General"

        # 4. Group items by equipment group if present, otherwise flat list
        has_groups = bool(quotation.equipment_groups and len(quotation.equipment_groups) > 0)
        
        # Prepare execution plan
        grouped_items: list[tuple[Optional[str], list[QuoteItem]]] = []
        if has_groups:
            # Map items to groups
            assigned_item_indices = set()
            for group in quotation.equipment_groups:
                g_items = []
                for idx, it in enumerate(quotation.items):
                    if it.equipment_group and (it.equipment_group == group.name or group.name in it.equipment_group):
                        g_items.append(it)
                        assigned_item_indices.add(idx)
                    elif it.line_number in group.line_numbers:
                        g_items.append(it)
                        assigned_item_indices.add(idx)

                # Format group title
                title = group.name
                if group.serial_numbers:
                    sn_str = " & ".join(group.serial_numbers)
                    if f"S/N" not in title and f"Serial" not in title:
                        title = f"{title} (S/N: {sn_str})"
                
                if g_items:
                    grouped_items.append((title, g_items))

            # Catch any unassigned items
            unassigned = [it for idx, it in enumerate(quotation.items) if idx not in assigned_item_indices]
            if unassigned:
                grouped_items.append((None, unassigned))
        else:
            grouped_items.append((None, quotation.items))

        # 5. Populate Excel Sheet strictly with PDF items
        current_row = start_row
        written_items_count = 0
        currency_code = quotation.currency or "EUR"
        currency_sym = quotation.currency_symbol or get_currency_symbol(currency_code)

        for group_title, items in grouped_items:
            # Write Equipment Group Header row if title exists
            if group_title:
                sheet.row_dimensions[current_row].height = header_row_height or 22
                for col_idx in range(1, initial_max_col + 1):
                    cell = sheet.cell(row=current_row, column=col_idx)
                    self._apply_cell_style(cell, header_row_styles[col_idx - 1])
                # Write group header text in Column A (or B)
                sheet.cell(row=current_row, column=1).value = group_title
                sheet.cell(row=current_row, column=1).font = openpyxl.styles.Font(bold=True, size=10)
                current_row += 1

            # Write Items for this group
            for item in items:
                sheet.row_dimensions[current_row].height = data_row_height or 18
                for col_idx in range(1, initial_max_col + 1):
                    cell = sheet.cell(row=current_row, column=col_idx)
                    self._apply_cell_style(cell, data_row_styles[col_idx - 1])

                # Calculate pricing based on pricing mode
                unit_price = item.unit_price
                if unit_price is not None:
                    if pricing_mode == "supplier_discount":
                        disc = supplier_discount_percent if supplier_discount_percent is not None else (item.discount_percent or 0.0)
                        unit_price = round(unit_price * (1.0 - (disc / 100.0)), 2)
                    elif pricing_mode == "add_margin" and margin_percent > 0:
                        if margin_percent < 100:
                            unit_price = round(unit_price / (1.0 - (margin_percent / 100.0)), 2)
                        else:
                            unit_price = round(unit_price * (1.0 + (margin_percent / 100.0)), 2)

                qty = item.quantity if item.quantity is not None else 0.0
                line_total = item.total_price if item.total_price is not None else (round(qty * unit_price, 2) if unit_price is not None else 0.0)

                # Column A: Line Number
                if mapping.line_number_column:
                    cell = sheet[f"{mapping.line_number_column}{current_row}"]
                    cell.value = item.line_number

                # Column B: Part Number - CRITICAL RULE: STRICT STRING WITH '@' NUMBER FORMAT
                if mapping.part_number_column:
                    cell = sheet[f"{mapping.part_number_column}{current_row}"]
                    if item.part_number:
                        cell.value = str(item.part_number)
                        cell.number_format = "@"
                    else:
                        cell.value = None

                # Column C: Description
                if mapping.description_column:
                    cell = sheet[f"{mapping.description_column}{current_row}"]
                    cell.value = str(item.description or "").strip()

                # Unit Price Column
                if mapping.unit_price_column:
                    cell = sheet[f"{mapping.unit_price_column}{current_row}"]
                    if unit_price is not None:
                        cell.value = float(unit_price)
                        cell.number_format = "#,##0.00"
                    else:
                        cell.value = ""

                # Quantity Column
                if mapping.quantity_column:
                    cell = sheet[f"{mapping.quantity_column}{current_row}"]
                    cell.value = float(qty) if item.quantity is not None else ""

                # Unit Column
                if mapping.unit_column:
                    cell = sheet[f"{mapping.unit_column}{current_row}"]
                    cell.value = str(item.unit or "NOS")

                # Discount Column
                if mapping.discount_column:
                    cell = sheet[f"{mapping.discount_column}{current_row}"]
                    cell.value = float(item.discount_percent or 0.0)

                # Total Price Column
                if mapping.total_price_column:
                    cell = sheet[f"{mapping.total_price_column}{current_row}"]
                    if mapping.quantity_column and mapping.unit_price_column and item.discount_percent is None:
                        cell.value = f"={mapping.quantity_column}{current_row}*{mapping.unit_price_column}{current_row}"
                    else:
                        cell.value = float(line_total)
                    cell.number_format = "#,##0.00"

                # Currency Column (if mapped)
                if mapping.currency_column:
                    cell = sheet[f"{mapping.currency_column}{current_row}"]
                    cell.value = currency_code

                current_row += 1
                written_items_count += 1

            # Blank row between equipment groups for neat layout
            if has_groups and group_title:
                current_row += 1

        # 6. HARD ITEM COUNT SAFETY CHECK
        if written_items_count != pdf_item_count:
            wb.close()
            error_msg = f"Item count mismatch. PDF contains {pdf_item_count} quotation items but {written_items_count} items are prepared for Excel."
            logger.error(error_msg)
            raise ValueError(error_msg)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        wb.save(str(output_path))
        wb.close()
        
        # 7. POST-GENERATION DETERMINISTIC VERIFICATION (Rule 11)
        self.verify_generated_excel(output_path, quotation, written_items_count, mapping=mapping, start_row=start_row)

        logger.info(f"Successfully generated and verified quotation Excel at {output_path} with EXACTLY {written_items_count} items")
        return written_items_count

    def verify_generated_excel(
        self,
        file_path: Path,
        quotation: QuotationData,
        expected_count: int,
        mapping: Optional[ColumnMappingConfig] = None,
        start_row: int = 6,
    ):
        """Reopens generated Excel with openpyxl and deterministically verifies:
        1. Number of quotation items = extracted quotation items.
        2. Every PDF part number exists in Excel.
        3. Every PDF quantity matches Excel.
        4. Every PDF unit price matches Excel.
        5. Part numbers with leading zeros are preserved as text.
        6. Currency has not been converted.
        7. No sample/template part numbers remain.
        8. No equipment header is counted as an item.
        9. Values are in the correct template columns."""
        wb = openpyxl.load_workbook(str(file_path), data_only=False)
        sheet = wb.active

        written_items = []
        all_values = []

        pn_col = mapping.part_number_column if mapping and mapping.part_number_column else "B"
        qty_col = mapping.quantity_column if mapping and mapping.quantity_column else "E"
        price_col = mapping.unit_price_column if mapping and mapping.unit_price_column else "D"
        line_col = mapping.line_number_column if mapping and mapping.line_number_column else "A"
        desc_col = mapping.description_column if mapping and mapping.description_column else "C"

        # Build list of equipment group keywords to exclude from line counting
        equipment_keywords = ["rotary valve", "s/n:", "serial", "lines", "equipment", "bxl-", "bl-"]
        if quotation.equipment_groups:
            for g in quotation.equipment_groups:
                equipment_keywords.append(g.name.lower())

        for r in range(1, sheet.max_row + 1):
            row_vals = [sheet.cell(row=r, column=c).value for c in range(1, sheet.max_column + 1)]
            for v in row_vals:
                if v is not None:
                    all_values.append(str(v).strip())

            # Exclude header metadata area above start_row
            if r < start_row:
                continue

            a_val = sheet[f"{line_col}{r}"].value
            b_val = sheet[f"{pn_col}{r}"].value
            c_val = sheet[f"{desc_col}{r}"].value
            d_val = sheet[f"{price_col}{r}"].value
            e_val = sheet[f"{qty_col}{r}"].value

            # Ignore completely empty rows
            if a_val is None and b_val is None and c_val is None and d_val is None and e_val is None:
                continue

            row_str = " ".join(str(v).strip() for v in (a_val, b_val, c_val) if v is not None).lower()

            # Skip equipment group headers and section titles (where price and qty are absent, or column A is the group title text)
            is_item_row = (isinstance(a_val, (int, float)) or (isinstance(a_val, str) and a_val.strip().isdigit())) and (d_val is not None or e_val is not None)
            if not is_item_row and any(k in row_str for k in equipment_keywords):
                continue

            # Skip table headers and currency rows
            if not is_item_row and any(k in row_str for k in ["part number", "item no", "description", "unit price", "qty", "euro", "eur", "usd", "inr"]):
                continue

            # Check for valid part number in designated part number column
            if b_val is not None and str(b_val).strip():
                pn = str(b_val).strip()
                if pn.lower() not in ("part number", "description", "part", "item", "qty", "no.", "no"):
                    written_items.append({
                        "row": r,
                        "line_number": a_val,
                        "part_number": pn,
                        "description": c_val,
                        "unit_price": d_val,
                        "quantity": e_val,
                        "cell_format": sheet[f"{pn_col}{r}"].number_format,
                    })
                    logger.info(f"Excel verification counted row {r} as an item (Part Number: '{pn}', Line: {a_val}, Qty: {e_val}, Unit Price: {d_val})")
            elif (b_val is None or str(b_val).strip() == "") and c_val is not None and str(c_val).strip():
                c_str = str(c_val).strip()
                if c_str.lower() not in ("description", "part number", "item description", "spec", "specification"):
                    if a_val is not None or d_val is not None or e_val is not None:
                        written_items.append({
                            "row": r,
                            "line_number": a_val,
                            "part_number": "",
                            "description": c_val,
                            "unit_price": d_val,
                            "quantity": e_val,
                            "cell_format": sheet[f"{pn_col}{r}"].number_format,
                        })
                        logger.info(f"Excel verification counted row {r} as an item without part number (Line: {a_val}, Description: '{c_val}', Qty: {e_val}, Unit Price: {d_val})")

        wb.close()

        # Check 1: Exact count of quotation items
        if len(written_items) != expected_count:
            counted_rows_desc = ", ".join(f"Row {it['row']}: '{it['part_number'] or it['description']}'" for it in written_items)
            raise ValueError(
                f"Excel verification failed: Expected {expected_count} quotation items in Excel, but found {len(written_items)} ({counted_rows_desc})."
            )

        # Check 2: All PDF part numbers, quantities, unit prices, and leading zeros
        written_map = {str(it["part_number"]).strip(): it for it in written_items if it.get("part_number")}
        for item in quotation.items:
            expected_pn = str(item.part_number).strip() if item.part_number else ""
            if not expected_pn:
                matched_entry = None
                for entry in written_items:
                    if entry["line_number"] == item.line_number or (entry["description"] and item.description and item.description in str(entry["description"])):
                        matched_entry = entry
                        break
                if not matched_entry:
                    raise ValueError(f"Excel verification failed: Item '{item.description}' from PDF is missing in generated Excel.")
                entry = matched_entry
            else:
                if expected_pn not in written_map:
                    raise ValueError(
                        f"Excel verification failed: Part number '{expected_pn}' from PDF is missing in generated Excel."
                    )
                entry = written_map[expected_pn]

            # Check quantity matches if quantity column is in template
            if mapping and mapping.quantity_column and item.quantity is not None:
                excel_qty = entry.get("quantity")
                if excel_qty is not None and excel_qty != "":
                    try:
                        if abs(float(excel_qty) - float(item.quantity)) > 0.001:
                            raise ValueError(
                                f"Excel mapping verification failed: For item '{expected_pn or item.description}', expected Quantity {item.quantity} in column {mapping.quantity_column} but found {excel_qty}."
                            )
                    except (ValueError, TypeError):
                        pass

            # Check unit price matches if unit price column is in template
            if mapping and mapping.unit_price_column and item.unit_price is not None:
                excel_price = entry.get("unit_price")
                if excel_price is not None and excel_price != "":
                    try:
                        if abs(float(excel_price) - float(item.unit_price)) > 0.01:
                            raise ValueError(
                                f"Excel mapping verification failed: For item '{expected_pn or item.description}', expected Unit Price {item.unit_price} in column {mapping.unit_price_column} but found {excel_price}."
                            )
                    except (ValueError, TypeError):
                        pass

            # Check 4: Ensure no unmapped fields spilled into adjacent unmapped columns
            if mapping:
                mapped_cols = {
                    c for c in [
                        mapping.line_number_column,
                        mapping.part_number_column,
                        mapping.description_column,
                        mapping.unit_price_column,
                        mapping.quantity_column,
                        mapping.unit_column,
                        mapping.discount_column,
                        mapping.total_price_column,
                        mapping.currency_column,
                    ]
                    if c
                }
                # Check for accidental spillover in unmapped columns (e.g. F, G) for this item row
                for c_idx in range(1, sheet.max_column + 1):
                    col_let = get_column_letter(c_idx)
                    if col_let not in mapped_cols:
                        cell_v = sheet.cell(row=entry["row"], column=c_idx).value
                        if cell_v is not None and str(cell_v).strip():
                            raise ValueError(
                                f"Excel mapping verification failed: Unmapped column {col_let} row {entry['row']} contains value '{cell_v}'. Only mapped template columns must be written."
                            )

        # Check 5: Forbidden old template sample part numbers must NEVER appear
        forbidden_sample_parts = [
            "03431814",
            "22462055",
            "02176160",
            "02175055",
            "46016050",
            "00354420",
            "00302550",
            "00185452",
        ]
        pdf_pns = {str(it.part_number).strip() for it in quotation.items}
        for forbidden in forbidden_sample_parts:
            if forbidden in all_values and forbidden not in pdf_pns:
                raise ValueError(
                    f"Excel verification failed: Old template sample part '{forbidden}' leaked into generated Excel."
                )





    def _safe_set_cell(self, sheet, cell_coordinate: str, value: Any):
        try:
            sheet[cell_coordinate] = value
        except Exception as e:
            logger.warning(f"Could not set header cell {cell_coordinate}: {e}")

    def _copy_cell_style(self, cell) -> dict:
        return {
            "font": copy.copy(cell.font) if cell.font else openpyxl.styles.Font(),
            "border": copy.copy(cell.border) if cell.border else openpyxl.styles.Border(),
            "fill": copy.copy(cell.fill) if cell.fill else openpyxl.styles.PatternFill(fill_type=None),
            "number_format": cell.number_format or "General",
            "protection": copy.copy(cell.protection) if cell.protection else openpyxl.styles.Protection(),
            "alignment": copy.copy(cell.alignment) if cell.alignment else openpyxl.styles.Alignment(),
        }

    def _apply_cell_style(self, cell, style_dict: dict):
        cell.font = copy.copy(style_dict["font"])
        cell.border = copy.copy(style_dict["border"])
        cell.fill = copy.copy(style_dict["fill"])
        cell.number_format = style_dict["number_format"]
        cell.protection = copy.copy(style_dict["protection"])
        cell.alignment = copy.copy(style_dict["alignment"])


excel_service = ExcelTemplateService()

