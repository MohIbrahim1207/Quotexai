import { apiClient } from './api';
import type {
  SupplierQuotationData,
  SupplierExtractionResponse,
  SupplierValidationSummary,
  SupplierWorkflowStagesResponse,
  SupplierPricingCalculationRequest,
  SupplierPricingCalculationResponse,
  ProcurementApprovalRequest,
  ProcurementApprovalResponse,
  ZohoPreviewRequest,
  ZohoPreviewResponse,
  ZohoExecuteSyncRequest,
  ZohoExecuteSyncResponse,
  SupplierPricingHistoryListResponse,
  SupplierPricingHistoryDetail,
  HistoryFilterParams,
  ZohoCompositeItemListResponse,
  ZohoCompositeItemDetailResponse,
} from '../types/supplierPricing';

export const supplierPricingApi = {
  async uploadSupplierPdf(file: File): Promise<{
    success: boolean;
    file_id: string;
    filename: string;
    size_bytes: number;
  }> {
    const formData = new FormData();
    formData.append('file', file);
    const res = await apiClient.post('/supplier-pricing/upload-pdf', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  },

  async extractSupplierQuotation(pdfId: string): Promise<SupplierExtractionResponse> {
    const formData = new FormData();
    formData.append('pdf_id', pdfId);
    const res = await apiClient.post<SupplierExtractionResponse>('/supplier-pricing/extract', formData);
    return res.data;
  },

  async validateSupplierQuotation(quotation: SupplierQuotationData): Promise<SupplierValidationSummary> {
    const res = await apiClient.post<SupplierValidationSummary>('/supplier-pricing/validate', quotation);
    return res.data;
  },

  async calculatePricing(
    req: SupplierPricingCalculationRequest
  ): Promise<SupplierPricingCalculationResponse> {
    const res = await apiClient.post<SupplierPricingCalculationResponse>(
      '/supplier-pricing/calculate-pricing',
      req
    );
    return res.data;
  },

  async submitApproval(
    req: ProcurementApprovalRequest
  ): Promise<ProcurementApprovalResponse> {
    const res = await apiClient.post<ProcurementApprovalResponse>(
      '/supplier-pricing/approval',
      req
    );
    return res.data;
  },

  async previewZohoSync(
    req: ZohoPreviewRequest
  ): Promise<ZohoPreviewResponse> {
    const res = await apiClient.post<ZohoPreviewResponse>(
      '/supplier-pricing/zoho-preview',
      req
    );
    return res.data;
  },

  async executeZohoSync(
    req: ZohoExecuteSyncRequest
  ): Promise<ZohoExecuteSyncResponse> {
    const res = await apiClient.post<ZohoExecuteSyncResponse>(
      '/supplier-pricing/zoho-sync',
      req
    );
    return res.data;
  },

  async getWorkflowStages(): Promise<SupplierWorkflowStagesResponse> {
    const res = await apiClient.get<SupplierWorkflowStagesResponse>('/supplier-pricing/stages');
    return res.data;
  },

  async getHistory(params?: HistoryFilterParams): Promise<SupplierPricingHistoryListResponse> {
    const res = await apiClient.get<SupplierPricingHistoryListResponse>(
      '/supplier-pricing/history',
      { params }
    );
    return res.data;
  },

  async getHistoryDetail(historyId: string): Promise<SupplierPricingHistoryDetail> {
    const res = await apiClient.get<SupplierPricingHistoryDetail>(
      `/supplier-pricing/history/${historyId}`
    );
    return res.data;
  },

  async listCompositeItems(search?: string, organizationId?: string): Promise<ZohoCompositeItemListResponse> {
    const res = await apiClient.get<ZohoCompositeItemListResponse>(
      '/supplier-pricing/zoho/composite-items',
      {
        params: {
          search: search || undefined,
          organization_id: organizationId || undefined,
        },
      }
    );
    return res.data;
  },

  async getCompositeItem(compositeItemId: string, organizationId?: string): Promise<ZohoCompositeItemDetailResponse> {
    const res = await apiClient.get<ZohoCompositeItemDetailResponse>(
      `/supplier-pricing/zoho/composite-items/${compositeItemId}`,
      {
        params: {
          organization_id: organizationId || undefined,
        },
      }
    );
    return res.data;
  },
};



