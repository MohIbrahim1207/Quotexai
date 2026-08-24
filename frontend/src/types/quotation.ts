export interface PriceDetail {
  amount: number;
  currency: string;
  symbol?: string;
}

export interface QuoteItem {
  line_number: number;
  part_number: string;
  description: string;
  quantity?: number | null;
  unit?: string | null;
  unit_price?: number | null;
  unit_price_detail?: PriceDetail | null;
  currency?: string;
  currency_symbol?: string;
  discount_percent?: number | null;
  total_price?: number | null;
  total_price_detail?: PriceDetail | null;
  commodity_code?: string | null;
  equipment_group?: string | null;
  item_type?: 'part' | 'charge' | 'service' | 'non_inventory' | string;
  source_page?: number;
  confidence?: Record<string, number>;
  status: 'verified' | 'warning' | 'error';
  validation_notes?: string[];
}

export interface EquipmentGroup {
  name: string;
  serial_numbers: string[];
  line_numbers: number[];
  line_start?: number;
  line_end?: number;
}

export interface QuotationData {
  quote_number?: string;
  quote_date?: string;
  expiry_date?: string;
  supplier_name?: string;
  customer?: string;
  payment_terms?: string;
  delivery_terms?: string;
  sales_person?: string;
  handled_by?: string;
  email?: string;
  currency?: string;
  currency_symbol?: string;
  items: QuoteItem[];
  equipment_groups: EquipmentGroup[];
  packaging_cost?: number | null;
  miscellaneous_charges?: number | null;
  lines_total?: number | null;
  grand_total?: number | null;
  pdf_item_count?: number;
  extracted_item_count?: number;
  raw_pdf_text?: string;
  source_pdf_id?: string;
  template_id?: string;
}

export interface ValidationIssue {
  item_line?: number;
  field: string;
  issue_type: 'error' | 'warning' | 'info';
  message: string;
  expected_value?: any;
  actual_value?: any;
}

export interface ValidationSummary {
  is_valid: boolean;
  overall_confidence: number;
  errors_count: number;
  warnings_count: number;
  pdf_item_count: number;
  extracted_item_count: number;
  items_ready_for_excel: number;
  currency: string;
  currency_symbol: string;
  price_validation_passed: number;
  part_number_validation_passed: number;
  total_items_validated: number;
  issues: ValidationIssue[];
}

export interface ExtractionResponse {
  success: boolean;
  quotation: QuotationData;
  validation: ValidationSummary;
  processing_time_seconds: number;
  extracted_page_count: number;
  extraction_source: string;
}

export interface ColumnMappingConfig {
  line_number_column?: string;
  part_number_column?: string;
  description_column?: string;
  quantity_column?: string;
  unit_column?: string;
  unit_price_column?: string;
  discount_column?: string;
  total_price_column?: string;
  currency_column?: string;
  start_row: number;
  quote_number_cell?: string;
  customer_cell?: string;
  date_cell?: string;
  currency_cell?: string;
}

export interface TemplateAnalysisResponse {
  template_id: string;
  sheet_names: string[];
  detected_headers: Record<string, string>;
  suggested_mapping: ColumnMappingConfig;
  preview_rows: any[][];
}

export interface GenerateExcelRequest {
  quotation: QuotationData;
  template_id: string;
  pricing_mode: 'quoted_price' | 'supplier_discount' | 'add_margin';
  margin_percent: number;
  supplier_discount_percent?: number;
  custom_mapping?: ColumnMappingConfig;
}

export interface GenerateExcelResponse {
  success: boolean;
  download_url: string;
  filename: string;
  file_id: string;
  total_items_written: number;
  grand_total_written: number;
}

export interface ConversionRecord {
  id: string;
  quote_number: string;
  customer: string;
  source_pdf_filename: string;
  source_pdf_id: string;
  template_id: string;
  quote_date: string;
  created_at: string;
  updated_at: string;
  status: 'generated' | 'verified' | 'warning' | 'error' | 'draft';
  items_count: number;
  currency: string;
  grand_total: number;
  pricing_mode?: string;
  excel_file_id?: string;
  excel_filename?: string;
  quotation_data?: QuotationData;
  validation_summary?: ValidationSummary;
}

export interface HistoryResponse {
  success: boolean;
  records: ConversionRecord[];
  total: number;
  page: number;
  limit: number;
  total_pages: number;
}


