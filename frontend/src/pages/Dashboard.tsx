import React, { useState } from 'react';
import { Header } from '../components/Header';
import { Dropzone } from '../components/Dropzone';
import { ProcessingStatus } from '../components/ProcessingStatus';
import { QuotationReview } from '../components/QuotationReview';
import { TemplateMappingModal } from '../components/TemplateMappingModal';
import { DownloadCard } from '../components/DownloadCard';
import { quotationApi } from '../services/api';
import { ConversionHistory } from '../components/ConversionHistory';
import type {
  QuotationData,
  ValidationSummary,
  TemplateAnalysisResponse,
  ColumnMappingConfig,
  GenerateExcelResponse,
  ConversionRecord,
} from '../types/quotation';
import { AlertCircle } from 'lucide-react';

interface DashboardProps {
  activeModule?: 'quotation' | 'supplier_pricing' | 'history';
  onSelectModule?: (mod: 'quotation' | 'supplier_pricing' | 'history') => void;
}

export const Dashboard: React.FC<DashboardProps> = ({ activeModule, onSelectModule }) => {
  const [step, setStep] = useState<'upload' | 'processing' | 'review' | 'success'>('upload');
  const [pdfFile, setPdfFile] = useState<File | null>(null);
  const [pdfId, setPdfId] = useState<string | null>(null);
  const [templateFile, setTemplateFile] = useState<File | null>(null);
  const [templateId, setTemplateId] = useState<string | null>(null);

  const [quotation, setQuotation] = useState<QuotationData | null>(null);
  const [validation, setValidation] = useState<ValidationSummary | null>(null);
  const [templateAnalysis, setTemplateAnalysis] = useState<TemplateAnalysisResponse | null>(null);
  const [columnMapping, setColumnMapping] = useState<ColumnMappingConfig | undefined>(undefined);

  const [pricingMode, setPricingMode] = useState<'quoted_price' | 'supplier_discount' | 'add_margin'>('quoted_price');
  const [marginPercent, setMarginPercent] = useState<number>(10.0);
  const [supplierDiscountPercent, setSupplierDiscountPercent] = useState<number>(0.0);

  const [isMappingOpen, setIsMappingOpen] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedResponse, setGeneratedResponse] = useState<GenerateExcelResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [historyRefreshKey, setHistoryRefreshKey] = useState<number>(0);

  const handlePdfSelect = async (file: File) => {
    setPdfFile(file);
    setErrorMessage(null);
    try {
      const res = await quotationApi.uploadPdf(file);
      setPdfId(res.file_id);
    } catch (err: any) {
      setErrorMessage(err.response?.data?.detail || 'Failed to upload PDF. Please try again.');
    }
  };

  const handleTemplateSelect = async (file: File) => {
    setTemplateFile(file);
    setErrorMessage(null);
    try {
      const res = await quotationApi.uploadTemplate(file);
      setTemplateId(res.template_id);
      if (res.analysis) {
        setTemplateAnalysis(res.analysis);
        if (res.analysis.suggested_mapping) {
          setColumnMapping(res.analysis.suggested_mapping);
        }
      }
    } catch (err: any) {
      setErrorMessage(err.response?.data?.detail || 'Failed to upload template. Please try again.');
    }
  };

  const handleExtract = async () => {
    if (!pdfId) {
      if (pdfFile) {
        try {
          const res = await quotationApi.uploadPdf(pdfFile);
          setPdfId(res.file_id);
          startExtraction(res.file_id, templateId || undefined);
        } catch (e: any) {
          setErrorMessage(e.response?.data?.detail || 'Upload failed.');
        }
      }
      return;
    }
    startExtraction(pdfId, templateId || undefined);
  };

  const startExtraction = async (pId: string, tId?: string) => {
    setStep('processing');
    setErrorMessage(null);

    try {
      const res = await quotationApi.extractQuotation(pId, tId);
      setQuotation(res.quotation);
      setValidation(res.validation);
      setHistoryRefreshKey((k) => k + 1);
      setStep('review');
    } catch (err: any) {
      setErrorMessage(err.response?.data?.detail || 'Quotation extraction failed. Please check the PDF.');
      setStep('upload');
    }
  };

  const handleGenerate = async () => {
    if (!quotation) return;
    setIsGenerating(true);
    setErrorMessage(null);

    try {
      const res = await quotationApi.generateExcel({
        quotation,
        template_id: templateId || 'ENQ-2026-07-2549.xlsx',
        pricing_mode: pricingMode,
        margin_percent: marginPercent,
        supplier_discount_percent: supplierDiscountPercent,
        custom_mapping: columnMapping,
      });

      setGeneratedResponse(res);
      setHistoryRefreshKey((k) => k + 1);
      setStep('success');
    } catch (err: any) {
      setErrorMessage(err.response?.data?.detail || 'Failed to generate Excel quotation.');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleDownload = () => {
    if (!generatedResponse) return;
    const url = quotationApi.getDownloadUrl(generatedResponse.file_id);
    const link = document.createElement('a');
    link.href = url;
    link.download = generatedResponse.filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleReset = () => {
    setStep('upload');
    setPdfFile(null);
    setPdfId(null);
    setTemplateFile(null);
    setTemplateId(null);
    setQuotation(null);
    setValidation(null);
    setGeneratedResponse(null);
    setErrorMessage(null);
  };

  const handleSelectHistoryRecord = async (record: ConversionRecord) => {
    try {
      setIsGenerating(true);
      // Fetch full details if quotation_data is not fully in memory
      let fullRecord = record;
      if (!record.quotation_data) {
        const res = await quotationApi.getConversion(record.id);
        fullRecord = res.record;
      }

      if (fullRecord.quotation_data) {
        setQuotation(fullRecord.quotation_data);
        if (fullRecord.validation_summary) {
          setValidation(fullRecord.validation_summary);
        } else {
          // Re-validate dynamically
          const val = await quotationApi.validateQuotation(fullRecord.quotation_data);
          setValidation(val);
        }
        setPdfId(fullRecord.source_pdf_id || null);
        setTemplateId(fullRecord.template_id || null);
        if (fullRecord.excel_file_id) {
          setGeneratedResponse({
            success: true,
            download_url: quotationApi.getDownloadUrl(fullRecord.excel_file_id),
            filename: fullRecord.excel_filename || `${fullRecord.quote_number}_Quotation.xlsx`,
            file_id: fullRecord.excel_file_id,
            total_items_written: fullRecord.items_count,
            grand_total_written: fullRecord.grand_total,
          });
        }
        setStep('review');
      }
    } catch (err: any) {
      setErrorMessage(err.response?.data?.detail || 'Failed to open historical conversion.');
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#F5F1E8] text-[#26231F] flex flex-col font-sans selection:bg-[#C98B4A]/20 selection:text-[#26231F]">
      <Header
        onReset={handleReset}
        isBusy={step === 'processing' || isGenerating}
        activeModule={activeModule}
        onSelectModule={onSelectModule}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {/* Error Banner */}
        {errorMessage && (
          <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200 flex items-start space-x-3 text-xs text-rose-900 shadow-2xs backdrop-blur-md">
            <AlertCircle className="w-4 h-4 text-rose-600 mt-0.5 shrink-0" />
            <div className="flex-1">
              <p className="font-bold text-rose-950">Action Required</p>
              <p className="mt-0.5">{errorMessage}</p>
            </div>
            <button onClick={() => setErrorMessage(null)} className="text-rose-500 hover:text-rose-800 cursor-pointer">
              ✕
            </button>
          </div>
        )}

        {/* Workflow Views */}
        {step === 'upload' && (
          <>
            <Dropzone
              pdfFile={pdfFile}
              templateFile={templateFile}
              onPdfSelect={handlePdfSelect}
              onTemplateSelect={handleTemplateSelect}
              onExtract={handleExtract}
              isLoading={false}
            />

            {/* Persistent Conversion History Bar */}
            <ConversionHistory
              onSelectRecord={handleSelectHistoryRecord}
              refreshTrigger={historyRefreshKey}
            />
          </>
        )}

        {step === 'processing' && <ProcessingStatus />}

        {step === 'review' && quotation && validation && (
          <QuotationReview
            quotation={quotation}
            validation={validation}
            onChange={setQuotation}
            onGenerate={handleGenerate}
            pricingMode={pricingMode}
            marginPercent={marginPercent}
            supplierDiscountPercent={supplierDiscountPercent}
            onPricingModeChange={setPricingMode}
            onMarginChange={setMarginPercent}
            onSupplierDiscountChange={setSupplierDiscountPercent}
            isGenerating={isGenerating}
          />
        )}

        {step === 'success' && generatedResponse && (
          <DownloadCard
            response={generatedResponse}
            onDownload={handleDownload}
            onReset={handleReset}
            quoteNumber={quotation?.quote_number}
            customer={quotation?.customer}
          />
        )}
      </main>


      {/* Template Mapping Modal */}
      <TemplateMappingModal
        isOpen={isMappingOpen}
        onClose={() => setIsMappingOpen(false)}
        analysis={templateAnalysis}
        mapping={columnMapping}
        onSaveMapping={setColumnMapping}
      />

      <footer className="border-t border-[#786446]/10 bg-white/40 backdrop-blur-md py-5 text-center text-xs text-[#716B61]">
        QuotexAI Enterprise • Built with FastAPI, PyMuPDF, openpyxl & Google Gemini AI
      </footer>
    </div>
  );
};
