import axios from 'axios';
import type {
  ExtractionResponse,
  GenerateExcelRequest,
  GenerateExcelResponse,
  QuotationData,
  TemplateAnalysisResponse,
  ValidationSummary,
} from '../types/quotation';

const API_BASE = import.meta.env.VITE_API_URL || '';

export const apiClient = axios.create({
  baseURL: `${API_BASE}/api`,
  headers: {
    'Accept': 'application/json',
  },
});

export const quotationApi = {
  async checkHealth() {
    const res = await apiClient.get('/health');
    return res.data;
  },

  async uploadPdf(file: File): Promise<{ success: boolean; file_id: string; filename: string; size_bytes: number }> {
    const formData = new FormData();
    formData.append('file', file);
    const res = await apiClient.post('/quotation/upload-pdf', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  },

  async uploadTemplate(file: File): Promise<{
    success: boolean;
    template_id: string;
    filename: string;
    size_bytes: number;
    analysis?: TemplateAnalysisResponse;
  }> {
    const formData = new FormData();
    formData.append('file', file);
    const res = await apiClient.post('/quotation/upload-template', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  },

  async extractQuotation(pdfId: string, templateId?: string): Promise<ExtractionResponse> {
    const formData = new FormData();
    formData.append('pdf_id', pdfId);
    if (templateId) {
      formData.append('template_id', templateId);
    }
    const res = await apiClient.post<ExtractionResponse>('/quotation/extract', formData);
    return res.data;
  },

  async validateQuotation(quotation: QuotationData): Promise<ValidationSummary> {
    const res = await apiClient.post<ValidationSummary>('/quotation/validate', quotation);
    return res.data;
  },

  async analyzeTemplate(templateId: string): Promise<TemplateAnalysisResponse> {
    const formData = new FormData();
    formData.append('template_id', templateId);
    const res = await apiClient.post<TemplateAnalysisResponse>('/quotation/analyze-template', formData);
    return res.data;
  },

  async generateExcel(req: GenerateExcelRequest): Promise<GenerateExcelResponse> {
    const res = await apiClient.post<GenerateExcelResponse>('/quotation/generate', req);
    return res.data;
  },

  getDownloadUrl(fileId: string): string {
    return `${API_BASE}/api/quotation/download/${fileId}`;
  },

  async getHistory(params?: {
    page?: number;
    limit?: number;
    search?: string;
    status?: string;
  }): Promise<import('../types/quotation').HistoryResponse> {
    const res = await apiClient.get<import('../types/quotation').HistoryResponse>('/history', {
      params,
    });
    return res.data;
  },

  async getConversion(conversionId: string): Promise<{ success: boolean; record: import('../types/quotation').ConversionRecord }> {
    const res = await apiClient.get(`/history/${conversionId}`);
    return res.data;
  },

  async deleteConversion(conversionId: string): Promise<{ success: boolean; message: string }> {
    const res = await apiClient.delete(`/history/${conversionId}`);
    return res.data;
  },

  async clearHistory(): Promise<{ success: boolean; message: string }> {
    const res = await apiClient.post('/history/clear');
    return res.data;
  },
};

