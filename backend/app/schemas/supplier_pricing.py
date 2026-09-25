from typing import Optional, Any
from pydantic import BaseModel, Field, field_validator


class SupplierQuoteItem(BaseModel):
    line_number: int
    part_number: str = Field("", description="Supplier Part Number (preserves leading zeros)")
    description: str = Field("", description="Part / Service Description")
    quantity: Optional[float] = None
    unit: Optional[str] = Field(None, description="Unit of measurement (e.g. PCS, NOS, MTR, SET)")
    currency: Optional[str] = "USD"
    unit_price: Optional[float] = None
    discount: Optional[float] = Field(0.0, description="Discount percent or fixed amount")
    packing_charges: Optional[float] = Field(0.0, description="Item-level packaging charge if applicable")
    freight_charges: Optional[float] = Field(0.0, description="Item-level freight/other charge if applicable")
    total: Optional[float] = None
    delivery_lead_time: Optional[str] = Field(None, description="Item-level delivery or lead time (e.g. '2-3 weeks')")
    option: Optional[str] = Field(None, description="Item option (e.g. '1', 'Option 1')")
    commodity_code: Optional[str] = Field(None, description="HS / Commodity Code")
    validation_status: str = Field("valid", description="'valid' | 'warning' | 'error'")
    validation_notes: list[str] = Field(default_factory=list)
    confidence: dict[str, float] = Field(default_factory=dict)

    @field_validator("part_number", mode="before")
    @classmethod
    def enforce_string_part_number(cls, v: Any) -> str:
        if v is None:
            return ""
        return str(v).strip()

    @field_validator("quantity", "unit_price", "discount", "packing_charges", "freight_charges", "total", mode="before")
    @classmethod
    def parse_optional_float(cls, v: Any) -> Optional[float]:
        if v is None or str(v).strip() == "" or str(v).strip().lower() in ("none", "null"):
            return None
        try:
            return float(v)
        except (ValueError, TypeError):
            return None


class SupplierValidationIssue(BaseModel):
    field: str
    item_line: Optional[int] = None
    issue_type: str = "warning"  # "error", "warning", "info"
    message: str
    suggested_fix: Optional[str] = None


class SupplierValidationSummary(BaseModel):
    is_valid: bool = True
    overall_confidence: float = 1.0
    errors_count: int = 0
    warnings_count: int = 0
    missing_fields: list[str] = Field(default_factory=list)
    uncertain_fields: list[str] = Field(default_factory=list)
    field_status: dict[str, str] = Field(default_factory=dict)  # "field_name": "valid" | "warning" | "error" | "missing"
    issues: list[SupplierValidationIssue] = Field(default_factory=list)


class SupplierQuotationData(BaseModel):
    # Header-level fields
    supplier_name: Optional[str] = None
    customer: Optional[str] = None
    quote_number: Optional[str] = None
    quote_date: Optional[str] = None
    delivery_lead_time: Optional[str] = None
    currency: Optional[str] = "USD"
    packing_charges: Optional[float] = 0.0
    freight_charges: Optional[float] = 0.0
    other_charges: Optional[float] = 0.0
    lines_total: Optional[float] = None
    grand_total: Optional[float] = None
    payment_terms: Optional[str] = None
    valid_until: Optional[str] = None
    notes: Optional[str] = None

    # Line items
    items: list[SupplierQuoteItem] = Field(default_factory=list)

    # Source metadata
    source_file_id: Optional[str] = None
    source_filename: Optional[str] = None

    @field_validator("packing_charges", "freight_charges", "other_charges", "lines_total", "grand_total", mode="before")
    @classmethod
    def parse_optional_float(cls, v: Any) -> Optional[float]:
        if v is None or str(v).strip() == "" or str(v).strip().lower() in ("none", "null"):
            return None
        try:
            return float(v)
        except (ValueError, TypeError):
            return None


class SupplierExtractionResponse(BaseModel):
    success: bool = True
    quotation: SupplierQuotationData
    validation: SupplierValidationSummary
    processing_time_seconds: float = 0.0
    source_pdf_id: str
    filename: str


class WorkflowStage(BaseModel):
    id: str
    name: str
    description: str
    status: str  # "completed", "in_progress", "pending", "locked"
    is_placeholder: bool = False
    badge: str


class SupplierWorkflowStagesResponse(BaseModel):
    stages: list[WorkflowStage]


# ============================================================================
# STAGE 2: PRICING CALCULATION MODELS
# ============================================================================

class PricingConfigParameters(BaseModel):
    """Configurable pricing parameters for deterministic Stage 2 calculation."""
    exchange_rate: float = Field(1.0, description="FX multiplier to convert supplier currency to target currency")
    target_currency: str = Field("EUR", description="Output/customer quotation currency (e.g. EUR, USD, IDR)")
    default_margin_percent: float = Field(10.0, description="Target profit margin percent (e.g. 10.0%)")
    margin_method: str = Field("margin_on_selling", description="'margin_on_selling' (Price = Landed / (1 - M)) or 'markup_on_cost' (Price = Landed * (1 + M))")
    freight_total: float = Field(0.0, description="Additional freight or logistics charges to allocate")
    customs_duty_percent: float = Field(0.0, description="Import customs or tariff duty percent (e.g. 5.0%)")
    local_handling_charge: float = Field(0.0, description="Local handling or clearance fee per unit or total")


class CalculatedLinePrice(BaseModel):
    """Full step-by-step pricing breakdown for an individual quotation line item."""
    line_number: int
    part_number: str
    description: str
    quantity: float
    unit: str
    supplier_currency: str
    target_currency: str
    
    # Step 1: Supplier Quoted Price
    supplier_unit_price: float
    
    # Step 2: Supplier Discount
    discount_percent: float
    discount_amount_unit: float
    
    # Step 3: Net Supplier Price
    net_supplier_unit_price: float
    net_supplier_total: float
    
    # Step 4: Currency Conversion
    exchange_rate: float
    converted_unit_price: float
    converted_net_total: float = 0.0
    
    # Step 5: Packaging & Logistics
    packing_charge_unit: float
    freight_charge_unit: float
    customs_duty_unit: float
    local_handling_unit: float
    
    # Step 6: Landed Cost
    landed_cost_unit: float
    landed_cost_total: float
    
    # Step 7: Profit Margin
    margin_percent: float
    margin_method: str
    margin_amount_unit: float
    
    # Step 8: Final Selling Price
    final_unit_selling_price: float
    final_total_selling_price: float
    profit_total: float
    
    lead_time: Optional[str] = None
    step_formula_breakdown: list[str] = Field(default_factory=list)


class PricingSummary(BaseModel):
    total_supplier_net: float
    total_supplier_net_converted: float = 0.0
    total_landed_cost: float
    total_selling_price: float
    total_gross_profit: float
    overall_margin_percent: float
    supplier_currency: str
    target_currency: str
    exchange_rate: float = 1.0
    items_count: int


class SupplierPricingCalculationRequest(BaseModel):
    quotation: SupplierQuotationData
    config: PricingConfigParameters
    line_overrides: Optional[dict[str, dict[str, Any]]] = None  # e.g. {"1": {"margin_percent": 15.0}}


class SupplierPricingCalculationResponse(BaseModel):
    success: bool = True
    config: PricingConfigParameters
    items: list[CalculatedLinePrice]
    summary: PricingSummary
    calculation_notes: list[str] = Field(default_factory=list)


# ============================================================================
# Stage 3: Procurement Approval Models
# ============================================================================

class ProcurementApprovalRequest(BaseModel):
    quote_number: str
    supplier_name: str
    total_selling_price: float
    currency: str
    effective_margin_percent: float
    status: str = Field("pending", description="'pending' | 'approved' | 'rejected'")
    approver_name: Optional[str] = None
    approval_notes: Optional[str] = None


class ProcurementApprovalResponse(BaseModel):
    success: bool = True
    quote_number: str
    status: str
    approver_name: Optional[str]
    approval_notes: Optional[str]
    decision_timestamp: str
    message: str


# ============================================================================
# Stage 4: Zoho Books Synchronization Models
# ============================================================================

class ZohoItemSyncRecord(BaseModel):
    part_number: str
    description: str
    rate: float  # Final Selling Price
    purchase_rate: float  # Net Supplier / Landed Cost Price
    currency: str
    unit: str
    action: str = Field("CREATE", description="'CREATE' or 'UPDATE'")
    existing_item_id: Optional[str] = None
    status: str = Field("ready", description="'ready' | 'synced' | 'skipped'")
    notes: Optional[str] = None


class ZohoSyncConfig(BaseModel):
    organization_id: str = "741367552"
    environment: str = Field("production", description="'sandbox' or 'production'")
    sync_mode: str = Field("items_only", description="'items_only' or 'items_and_po'")


class ZohoPreviewRequest(BaseModel):
    quotation: SupplierQuotationData
    pricing_summary: PricingSummary
    calculated_items: list[CalculatedLinePrice]
    zoho_config: ZohoSyncConfig
    sku_search_query: Optional[str] = None


class ZohoPreviewResponse(BaseModel):
    success: bool = True
    zoho_config: ZohoSyncConfig
    items_to_create: list[ZohoItemSyncRecord]
    items_to_update: list[ZohoItemSyncRecord]
    total_items: int
    matched_existing_count: int
    new_sku_count: int
    is_confirmed: bool = False
    requires_user_confirmation: bool = True
    warning_banner: str = "Items will NOT be written to Zoho Books until you explicitly review and check the confirmation box."


class ZohoExecuteSyncRequest(BaseModel):
    zoho_config: ZohoSyncConfig
    items: list[ZohoItemSyncRecord]
    user_confirmed: bool = Field(False, description="Must be explicitly True to execute")
    confirmed_by_user: Optional[str] = None
    quotation_number: Optional[str] = None
    supplier_name: Optional[str] = None
    quotation_date: Optional[str] = None
    source_filename: Optional[str] = None
    currency: Optional[str] = None
    pricing_summary: Optional[PricingSummary] = None


class ZohoExecuteSyncResponse(BaseModel):
    success: bool
    message: str
    synced_at: str
    created_count: int
    updated_count: int
    records: list[ZohoItemSyncRecord]
    audit_log: list[str]
    history_id: Optional[str] = None


class SupplierPricingHistoryItem(BaseModel):
    id: str
    history_id: str
    line_number: int
    sku: str
    description: Optional[str] = None
    quantity: float = 1.0
    unit: str = "NOS"
    supplier_unit_price: float = 0.0
    discount_percent: float = 0.0
    landed_cost: float = 0.0
    selling_price: float = 0.0
    action: str = "CREATE"
    zoho_item_id: Optional[str] = None
    zoho_status: str = "ready"
    zoho_message: Optional[str] = None
    error_message: Optional[str] = None


class SupplierPricingHistorySummary(BaseModel):
    id: str
    quotation_number: str
    supplier_name: str
    quotation_date: Optional[str] = None
    source_filename: Optional[str] = None
    currency: str = "EUR"
    processed_at: str
    processed_by: Optional[str] = None
    overall_status: str
    total_items: int
    created_count: int
    updated_count: int
    failed_count: int
    total_supplier_net: Optional[float] = 0.0
    total_landed_cost: Optional[float] = 0.0
    total_selling_price: Optional[float] = 0.0
    total_gross_profit: Optional[float] = 0.0
    overall_margin_percent: Optional[float] = 0.0
    zoho_organization_id: Optional[str] = None
    zoho_environment: Optional[str] = None
    sync_message: Optional[str] = None


class SupplierPricingHistoryDetail(SupplierPricingHistorySummary):
    audit_log: list[str] = []
    items: list[SupplierPricingHistoryItem] = []


class SupplierPricingHistoryStats(BaseModel):
    total_quotations: int = 0
    successfully_synced: int = 0
    partially_failed: int = 0
    failed: int = 0


class SupplierPricingHistoryListResponse(BaseModel):
    success: bool = True
    records: list[SupplierPricingHistorySummary]
    total_count: int
    total_pages: int
    current_page: int
    summary_stats: SupplierPricingHistoryStats


# ============================================================================
# Zoho Books Composite Items Schemas
# ============================================================================

class ZohoCompositeMappedItem(BaseModel):
    item_id: str = Field(..., description="Real numeric Zoho Item ID of component item")
    quantity: float = Field(1.0, gt=0, description="Quantity of component item")
    item_order: Optional[int] = Field(None, description="Display order sequence")
    rate: Optional[float] = Field(None, description="Component selling rate")
    purchase_rate: Optional[float] = Field(None, description="Component purchase rate")
    name: Optional[str] = Field(None, description="Component name")
    sku: Optional[str] = Field(None, description="Component SKU")
    unit: Optional[str] = Field(None, description="Component unit")
    description: Optional[str] = Field(None, description="Component description")


class ZohoCompositeItemCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, description="Composite item name")
    sku: Optional[str] = Field(None, description="Composite item SKU / Part Number")
    unit: Optional[str] = Field("Set", description="Unit of measurement (e.g. Set, Kit, Each)")
    description: Optional[str] = Field(None, description="Description of composite item")
    combo_type: Optional[str] = Field("kit", description="'kit' or 'assembly'")
    rate: float = Field(..., ge=0, description="Selling rate")
    purchase_rate: Optional[float] = Field(0.0, ge=0, description="Purchase rate")
    mapped_items: list[ZohoCompositeMappedItem] = Field(..., min_length=1, description="List of component items")


class ZohoCompositeItemUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, description="Updated composite item name")
    sku: Optional[str] = Field(None, description="Updated SKU / Part Number")
    unit: Optional[str] = Field(None, description="Updated unit")
    description: Optional[str] = Field(None, description="Updated description")
    combo_type: Optional[str] = Field(None, description="'kit' or 'assembly'")
    rate: Optional[float] = Field(None, ge=0, description="Updated selling rate")
    purchase_rate: Optional[float] = Field(None, ge=0, description="Updated purchase rate")
    mapped_items: Optional[list[ZohoCompositeMappedItem]] = Field(None, description="Updated constituent component items")


class ZohoCompositeItemResponse(BaseModel):
    success: bool
    composite_item_id: Optional[str] = None
    message: str
    composite_item: Optional[dict[str, Any]] = None



