from typing import Optional, Any, Union
from pydantic import BaseModel, Field, field_validator


class PriceDetail(BaseModel):
    amount: float
    currency: str = "EUR"
    symbol: Optional[str] = "€"


class FieldConfidence(BaseModel):
    field: str
    value: Any
    confidence: float = 1.0
    status: str = "verified"  # "verified", "warning", "error"
    message: Optional[str] = None


class QuoteItem(BaseModel):
    line_number: int
    part_number: str = Field(..., description="Part number as exact string. Must preserve leading zeros.")
    description: str = ""
    quantity: Optional[float] = None
    unit: Optional[str] = None
    unit_price: Optional[float] = None
    unit_price_detail: Optional[PriceDetail] = None
    currency: Optional[str] = "EUR"
    currency_symbol: Optional[str] = "€"
    discount_percent: Optional[float] = None
    total_price: Optional[float] = None
    total_price_detail: Optional[PriceDetail] = None
    commodity_code: Optional[str] = None
    equipment_group: Optional[str] = None
    item_type: Optional[str] = "part"  # "part", "charge", "service", "non_inventory"
    source_page: Optional[int] = 1
    confidence: dict[str, float] = Field(default_factory=dict)
    status: str = "verified"  # "verified", "warning", "error"
    validation_notes: list[str] = Field(default_factory=list)

    @field_validator("part_number", mode="before")
    @classmethod
    def enforce_string_part_number(cls, v: Any) -> str:
        if v is None:
            return ""
        return str(v).strip()

    @field_validator("commodity_code", mode="before")
    @classmethod
    def enforce_string_commodity_code(cls, v: Any) -> Optional[str]:
        if v is None or str(v).strip() == "" or str(v).strip().lower() in ("none", "null"):
            return None
        return str(v).strip()

    @field_validator("unit_price", mode="before")
    @classmethod
    def parse_unit_price(cls, v: Any) -> Optional[float]:
        if isinstance(v, dict):
            return float(v.get("amount", 0.0)) if v.get("amount") is not None else None
        if v is None or str(v).strip() == "" or str(v).strip().lower() in ("none", "null"):
            return None
        try:
            return float(v)
        except (ValueError, TypeError):
            return None

    @field_validator("total_price", mode="before")
    @classmethod
    def parse_total_price(cls, v: Any) -> Optional[float]:
        if isinstance(v, dict):
            return float(v.get("amount", 0.0)) if v.get("amount") is not None else None
        if v is None or str(v).strip() == "" or str(v).strip().lower() in ("none", "null"):
            return None
        try:
            return float(v)
        except (ValueError, TypeError):
            return None


class EquipmentGroup(BaseModel):
    name: str
    serial_numbers: list[str] = Field(default_factory=list)
    line_numbers: list[int] = Field(default_factory=list)
    line_start: Optional[int] = None
    line_end: Optional[int] = None


class QuotationData(BaseModel):
    quote_number: Optional[str] = None
    quote_date: Optional[str] = None
    expiry_date: Optional[str] = None
    supplier_name: Optional[str] = None
    customer: Optional[str] = None
    payment_terms: Optional[str] = None
    delivery_terms: Optional[str] = None
    sales_person: Optional[str] = None
    handled_by: Optional[str] = None
    email: Optional[str] = None
    currency: Optional[str] = "EUR"
    currency_symbol: Optional[str] = "€"
    items: list[QuoteItem] = Field(default_factory=list)
    equipment_groups: list[EquipmentGroup] = Field(default_factory=list)
    packaging_cost: Optional[float] = None
    miscellaneous_charges: Optional[float] = None
    lines_total: Optional[float] = None
    grand_total: Optional[float] = None
    pdf_item_count: Optional[int] = None
    extracted_item_count: Optional[int] = None
    raw_pdf_text: Optional[str] = None
    source_pdf_id: Optional[str] = None
    template_id: Optional[str] = None


class ValidationIssue(BaseModel):
    item_line: Optional[int] = None
    field: str
    issue_type: str  # "error", "warning", "info"
    message: str
    expected_value: Optional[Any] = None
    actual_value: Optional[Any] = None


class ValidationSummary(BaseModel):
    is_valid: bool = True
    overall_confidence: float = 1.0
    errors_count: int = 0
    warnings_count: int = 0
    pdf_item_count: int = 0
    extracted_item_count: int = 0
    items_ready_for_excel: int = 0
    currency: str = "EUR"
    currency_symbol: str = "€"
    price_validation_passed: int = 0
    part_number_validation_passed: int = 0
    total_items_validated: int = 0
    issues: list[ValidationIssue] = Field(default_factory=list)


class ExtractionResponse(BaseModel):
    success: bool
    quotation: QuotationData
    validation: ValidationSummary
    processing_time_seconds: float = 0.0
    extracted_page_count: int = 1
    extraction_source: str = "pdf_text_ai"


class ColumnMappingConfig(BaseModel):
    line_number_column: Optional[str] = "A"
    part_number_column: Optional[str] = "B"
    description_column: Optional[str] = "C"
    quantity_column: Optional[str] = "D"
    unit_column: Optional[str] = None
    unit_price_column: Optional[str] = "F"
    discount_column: Optional[str] = None
    total_price_column: Optional[str] = None
    currency_column: Optional[str] = None
    start_row: int = 6
    quote_number_cell: Optional[str] = None
    customer_cell: Optional[str] = None
    date_cell: Optional[str] = None
    currency_cell: Optional[str] = None


class TemplateAnalysisResponse(BaseModel):
    template_id: str
    sheet_names: list[str]
    detected_headers: dict[str, str]
    suggested_mapping: ColumnMappingConfig
    preview_rows: list[list[Any]] = Field(default_factory=list)


class GenerateExcelRequest(BaseModel):
    quotation: QuotationData
    template_id: str
    pricing_mode: str = "quoted_price"
    margin_percent: float = 0.0
    supplier_discount_percent: Optional[float] = None
    custom_mapping: Optional[ColumnMappingConfig] = None


class GenerateExcelResponse(BaseModel):
    success: bool
    download_url: str
    filename: str
    file_id: str
    total_items_written: int
    grand_total_written: float

