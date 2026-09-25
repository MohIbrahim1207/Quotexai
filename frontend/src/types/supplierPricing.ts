export interface SupplierQuoteItem {
  line_number: number;
  part_number: string;
  description: string;
  quantity: number | null;
  unit: string | null;
  currency: string;
  unit_price: number | null;
  discount: number | null;
  packing_charges: number | null;
  freight_charges: number | null;
  total: number | null;
  delivery_lead_time: string | null;
  option?: string | null;
  commodity_code?: string | null;
  validation_status: 'valid' | 'warning' | 'error';
  validation_notes: string[];
  confidence?: Record<string, number>;
}

export interface SupplierValidationIssue {
  field: string;
  item_line?: number;
  issue_type: 'error' | 'warning' | 'info';
  message: string;
  suggested_fix?: string;
}

export interface SupplierValidationSummary {
  is_valid: boolean;
  overall_confidence: number;
  errors_count: number;
  warnings_count: number;
  missing_fields: string[];
  uncertain_fields: string[];
  field_status: Record<string, string>;
  issues: SupplierValidationIssue[];
}

export interface SupplierQuotationData {
  supplier_name?: string;
  customer?: string;
  quote_number?: string;
  quote_date?: string;
  delivery_lead_time?: string;
  currency?: string;
  packing_charges?: number | null;
  freight_charges?: number | null;
  other_charges?: number | null;
  lines_total?: number | null;
  grand_total?: number | null;
  payment_terms?: string;
  valid_until?: string;
  notes?: string;
  items: SupplierQuoteItem[];
  source_file_id?: string;
  source_filename?: string;
}

export interface SupplierExtractionResponse {
  success: boolean;
  quotation: SupplierQuotationData;
  validation: SupplierValidationSummary;
  processing_time_seconds: number;
  source_pdf_id: string;
  filename: string;
}

export interface WorkflowStage {
  id: string;
  name: string;
  description: string;
  status: 'completed' | 'in_progress' | 'pending' | 'locked';
  is_placeholder: boolean;
  badge: string;
}

export interface SupplierWorkflowStagesResponse {
  stages: WorkflowStage[];
}

export interface PricingConfigParameters {
  exchange_rate: number;
  target_currency: string;
  default_margin_percent: number;
  margin_method: 'margin_on_selling' | 'markup_on_cost';
  freight_total: number;
  customs_duty_percent: number;
  local_handling_charge: number;
}

export interface CalculatedLinePrice {
  line_number: number;
  part_number: string;
  description: string;
  quantity: number;
  unit: string;
  supplier_currency: string;
  target_currency: string;

  // Step 1: Supplier Quoted Price
  supplier_unit_price: number;

  // Step 2: Supplier Discount
  discount_percent: number;
  discount_amount_unit: number;

  // Step 3: Net Supplier Price
  net_supplier_unit_price: number;
  net_supplier_total: number;

  // Step 4: Currency Conversion
  exchange_rate: number;
  converted_unit_price: number;
  converted_net_total: number;

  // Step 5: Packaging & Logistics
  packing_charge_unit: number;
  freight_charge_unit: number;
  customs_duty_unit: number;
  local_handling_unit: number;

  // Step 6: Landed Cost
  landed_cost_unit: number;
  landed_cost_total: number;

  // Step 7: Profit Margin
  margin_percent: number;
  margin_method: string;
  margin_amount_unit: number;

  // Step 8: Final Selling Price
  final_unit_selling_price: number;
  final_total_selling_price: number;
  profit_total: number;

  lead_time?: string | null;
  step_formula_breakdown: string[];
}

export interface PricingSummary {
  total_supplier_net: number;
  total_supplier_net_converted: number;
  total_landed_cost: number;
  total_selling_price: number;
  total_gross_profit: number;
  overall_margin_percent: number;
  supplier_currency: string;
  target_currency: string;
  exchange_rate: number;
  items_count: number;
}

export interface SupplierPricingCalculationRequest {
  quotation: SupplierQuotationData;
  config: PricingConfigParameters;
  line_overrides?: Record<string, Record<string, any>>;
}

export interface SupplierPricingCalculationResponse {
  success: boolean;
  config: PricingConfigParameters;
  items: CalculatedLinePrice[];
  summary: PricingSummary;
  calculation_notes: string[];
}

// ============================================================================
// Stage 3: Procurement Approval Types
// ============================================================================

export interface ProcurementApprovalRequest {
  quote_number: string;
  supplier_name: string;
  total_selling_price: number;
  currency: string;
  effective_margin_percent: number;
  status: 'pending' | 'approved' | 'rejected';
  approver_name?: string;
  approval_notes?: string;
}

export interface ProcurementApprovalResponse {
  success: boolean;
  quote_number: string;
  status: 'pending' | 'approved' | 'rejected';
  approver_name?: string;
  approval_notes?: string;
  decision_timestamp: string;
  message: string;
}

// ============================================================================
// Stage 4: Zoho Books Sync Types
// ============================================================================

export interface ZohoItemSyncRecord {
  part_number: string;
  description: string;
  rate: number;
  purchase_rate: number;
  currency: string;
  unit: string;
  action: 'CREATE' | 'UPDATE';
  existing_item_id?: string | null;
  status: 'ready' | 'synced' | 'skipped';
  notes?: string | null;
}

export interface ZohoSyncConfig {
  organization_id: string;
  environment: 'sandbox' | 'production';
  sync_mode: 'items_only' | 'items_and_po';
}

export interface ZohoPreviewRequest {
  quotation: SupplierQuotationData;
  pricing_summary: PricingSummary;
  calculated_items: CalculatedLinePrice[];
  zoho_config: ZohoSyncConfig;
  sku_search_query?: string;
}

export interface ZohoPreviewResponse {
  success: boolean;
  zoho_config: ZohoSyncConfig;
  items_to_create: ZohoItemSyncRecord[];
  items_to_update: ZohoItemSyncRecord[];
  total_items: number;
  matched_existing_count: number;
  new_sku_count: number;
  is_confirmed: boolean;
  requires_user_confirmation: boolean;
  warning_banner: string;
}

export interface ZohoExecuteSyncRequest {
  zoho_config: ZohoSyncConfig;
  items: ZohoItemSyncRecord[];
  user_confirmed: boolean;
  confirmed_by_user?: string;
  quotation_number?: string;
  supplier_name?: string;
  quotation_date?: string;
  source_filename?: string;
  currency?: string;
  pricing_summary?: PricingSummary;
}

export interface ZohoExecuteSyncResponse {
  success: boolean;
  message: string;
  synced_at: string;
  created_count: number;
  updated_count: number;
  records: ZohoItemSyncRecord[];
  audit_log: string[];
  history_id?: string | null;
}

// ============================================================================
// History & Audit Trail Types
// ============================================================================

export interface SupplierPricingHistoryItem {
  id: string;
  history_id: string;
  line_number: number;
  sku: string;
  description?: string | null;
  quantity: number;
  unit: string;
  supplier_unit_price: number;
  discount_percent: number;
  landed_cost: number;
  selling_price: number;
  action: 'CREATE' | 'UPDATE';
  zoho_item_id?: string | null;
  zoho_status: string;
  zoho_message?: string | null;
  error_message?: string | null;
}

export interface SupplierPricingHistorySummary {
  id: string;
  quotation_number: string;
  supplier_name: string;
  quotation_date?: string | null;
  source_filename?: string | null;
  currency: string;
  processed_at: string;
  processed_by?: string | null;
  overall_status: 'SUCCESS' | 'PARTIAL' | 'FAILED' | 'CALCULATED';
  total_items: number;
  created_count: number;
  updated_count: number;
  failed_count: number;
  total_supplier_net?: number | null;
  total_landed_cost?: number | null;
  total_selling_price?: number | null;
  total_gross_profit?: number | null;
  overall_margin_percent?: number | null;
  zoho_organization_id?: string | null;
  zoho_environment?: string | null;
  sync_message?: string | null;
}

export interface SupplierPricingHistoryDetail extends SupplierPricingHistorySummary {
  audit_log: string[];
  items: SupplierPricingHistoryItem[];
}

export interface SupplierPricingHistoryStats {
  total_quotations: number;
  successfully_synced: number;
  partially_failed: number;
  failed: number;
}

export interface SupplierPricingHistoryListResponse {
  success: boolean;
  records: SupplierPricingHistorySummary[];
  total_count: number;
  total_pages: number;
  current_page: number;
  summary_stats: SupplierPricingHistoryStats;
}

export interface HistoryFilterParams {
  page?: number;
  page_size?: number;
  search?: string;
  status?: string;
  action?: string;
  start_date?: string;
  end_date?: string;
}

// ============================================================================
// Zoho Books Composite Items Types
// ============================================================================

export interface ZohoCompositeMappedComponent {
  item_id: string;
  name?: string;
  item_name?: string;
  sku?: string;
  product_type?: string;
  quantity: number;
  unit?: string;
  rate?: number;
  purchase_rate?: number;
}

export interface ZohoCompositeItem {
  composite_item_id?: string | null;
  item_id?: string | null;
  name: string;
  item_name?: string;
  sku?: string;
  part_number?: string;
  description?: string;
  rate?: number;
  purchase_rate?: number;
  unit?: string;
  status?: string;
  item_type?: string;
  combo_type?: string;
  is_combo_product?: boolean;
  action?: 'CREATE' | 'UPDATE';
  mapped_items?: ZohoCompositeMappedComponent[];
  component_count?: number;
}

export interface ZohoCompositeItemListResponse {
  success: boolean;
  http_status: number;
  code: number;
  message?: string;
  composite_items: ZohoCompositeItem[];
  count: number;
}

export interface ZohoCompositeItemDetailResponse {
  code: number;
  message?: string;
  composite_item: ZohoCompositeItem;
}


