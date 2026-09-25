import React, { useState } from 'react';
import { AlertCircle, Sparkles, RefreshCw, CheckCircle2, Calculator, FileText, UserCheck, BookOpen } from 'lucide-react';
import { SupplierPdfUploader } from '../components/supplier-pricing/SupplierPdfUploader';
import { SupplierQuoteReview } from '../components/supplier-pricing/SupplierQuoteReview';
import { PricingCalculationStep } from '../components/supplier-pricing/PricingCalculationStep';
import { ProcurementApprovalStep } from '../components/supplier-pricing/ProcurementApprovalStep';
import { ZohoBooksSyncStep } from '../components/supplier-pricing/ZohoBooksSyncStep';
import { FutureStagesCard } from '../components/supplier-pricing/FutureStagesCard';
import { supplierPricingApi } from '../services/supplierPricingApi';
import type {
  SupplierQuotationData,
  SupplierValidationSummary,
  CalculatedLinePrice,
  PricingSummary,
} from '../types/supplierPricing';

const defaultBrowseQuotation: SupplierQuotationData = {
  supplier_name: 'PT. Flow Force Indonesia Catalog Browse',
  quote_number: 'CATALOG-VIEW',
  quote_date: new Date().toISOString().slice(0, 10),
  delivery_lead_time: 'Ex-Works',
  currency: 'EUR',
  packing_charges: 0,
  freight_charges: 0,
  other_charges: 0,
  lines_total: 0,
  grand_total: 0,
  items: [],
};

const defaultBrowsePricing: PricingSummary = {
  total_supplier_net: 0,
  total_supplier_net_converted: 0,
  exchange_rate: 1.0,
  total_landed_cost: 0,
  total_selling_price: 0,
  total_gross_profit: 0,
  overall_margin_percent: 0,
  supplier_currency: 'EUR',
  target_currency: 'IDR',
  items_count: 0,
};

export const SupplierPricingModule: React.FC = () => {
  const [step, setStep] = useState<'upload' | 'extracting' | 'review' | 'pricing' | 'approval' | 'zoho'>('upload');
  const [pdfFile, setPdfFile] = useState<File | null>(null);
  const [pdfId, setPdfId] = useState<string | null>(null);
  const [quotation, setQuotation] = useState<SupplierQuotationData | null>(null);
  const [validation, setValidation] = useState<SupplierValidationSummary | null>(null);

  // Pricing & Approval State across pipeline
  const [calculatedItems, setCalculatedItems] = useState<CalculatedLinePrice[]>([]);
  const [pricingSummary, setPricingSummary] = useState<PricingSummary | null>(null);
  const [approvalStatus, setApprovalStatus] = useState<'pending' | 'approved' | 'rejected'>('pending');
  const [approverName, setApproverName] = useState('Procurement Lead');
  const [approvalNotes, setApprovalNotes] = useState('');

  const [isLoading, setIsLoading] = useState(false);
  const [isValidating, setIsValidating] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handlePdfSelect = async (file: File) => {
    setPdfFile(file);
    setErrorMessage(null);
    try {
      const res = await supplierPricingApi.uploadSupplierPdf(file);
      setPdfId(res.file_id);
    } catch (err: any) {
      setErrorMessage(err.response?.data?.detail || 'Failed to upload supplier quotation PDF.');
    }
  };

  const handleExtract = async () => {
    if (!pdfFile && !pdfId) return;
    setIsLoading(true);
    setErrorMessage(null);
    setStep('extracting');

    try {
      let fileId = pdfId;
      if (!fileId && pdfFile) {
        const uploadRes = await supplierPricingApi.uploadSupplierPdf(pdfFile);
        fileId = uploadRes.file_id;
        setPdfId(fileId);
      }

      if (!fileId) throw new Error('No PDF file ID available for extraction.');

      const extractRes = await supplierPricingApi.extractSupplierQuotation(fileId);
      setQuotation(extractRes.quotation);
      setValidation(extractRes.validation);
      setStep('review');
    } catch (err: any) {
      setErrorMessage(err.response?.data?.detail || 'Quotation extraction failed. Please try again or check the PDF.');
      setStep('upload');
    } finally {
      setIsLoading(false);
    }
  };

  const handleRevalidate = async () => {
    if (!quotation) return;
    setIsValidating(true);
    setErrorMessage(null);

    try {
      const res = await supplierPricingApi.validateSupplierQuotation(quotation);
      setValidation(res);
    } catch (err: any) {
      setErrorMessage(err.response?.data?.detail || 'Validation request failed.');
    } finally {
      setIsValidating(false);
    }
  };

  const handleLoadSample = () => {
    const sampleQuote: SupplierQuotationData = {
      supplier_name: 'DMN Westinghouse India Pvt Ltd',
      quote_number: '41260607',
      quote_date: '2026-07-30',
      delivery_lead_time: '4-6 Weeks Ex-Works',
      currency: 'EUR',
      packing_charges: 16.0,
      freight_charges: 45.0,
      other_charges: 0.0,
      lines_total: 1240.59,
      grand_total: 1301.59,
      payment_terms: '100% Upfront Before Dispatch',
      valid_until: '2026-09-13',
      notes: 'Standard OEM packaging included. FCA Noordwijkerhout Incoterms 2020.',
      items: [
        {
          line_number: 1,
          part_number: '23254164',
          description: 'Lantern ring AL/BL 300-350 PTFE FDA EC1935/2004 USP klasse VI SAS-II',
          quantity: 2.0,
          unit: 'NOS',
          currency: 'EUR',
          unit_price: 562.0,
          discount: 30.0,
          packing_charges: 0.0,
          freight_charges: 0.0,
          total: 786.8,
          delivery_lead_time: '4-6 Weeks',
          validation_status: 'valid',
          validation_notes: [],
        },
        {
          line_number: 2,
          part_number: '00138737',
          description: 'O-Ring 320x5 FPM70 DIN 3771 Shore A',
          quantity: 4.0,
          unit: 'NOS',
          currency: 'EUR',
          unit_price: 34.5,
          discount: 25.0,
          packing_charges: 0.0,
          freight_charges: 0.0,
          total: 103.5,
          delivery_lead_time: 'Ex-Stock',
          validation_status: 'valid',
          validation_notes: [],
        },
        {
          line_number: 3,
          part_number: '02174072',
          description: 'Rotor vane scraper brass DMN-300',
          quantity: 1.0,
          unit: 'NOS',
          currency: 'EUR',
          unit_price: 350.29,
          discount: 0.0,
          packing_charges: 0.0,
          freight_charges: 0.0,
          total: 350.29,
          delivery_lead_time: '2-3 Weeks',
          validation_status: 'valid',
          validation_notes: [],
        },
      ],
    };

    const sampleValidation: SupplierValidationSummary = {
      is_valid: true,
      overall_confidence: 0.98,
      errors_count: 0,
      warnings_count: 0,
      missing_fields: [],
      uncertain_fields: [],
      field_status: {
        supplier_name: 'valid',
        quote_number: 'valid',
        quote_date: 'valid',
        currency: 'valid',
        delivery_lead_time: 'valid',
        grand_total: 'valid',
      },
      issues: [],
    };

    setQuotation(sampleQuote);
    setValidation(sampleValidation);
    setStep('review');
  };

  const handleReset = () => {
    setStep('upload');
    setPdfFile(null);
    setPdfId(null);
    setQuotation(null);
    setValidation(null);
    setCalculatedItems([]);
    setPricingSummary(null);
    setApprovalStatus('pending');
    setErrorMessage(null);
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-200">
      {/* Error Banner */}
      {errorMessage && (
        <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200 flex items-start space-x-3 text-xs text-rose-900 shadow-2xs backdrop-blur-md">
          <AlertCircle className="w-4 h-4 text-rose-600 mt-0.5 shrink-0" />
          <div className="flex-1">
            <p className="font-bold text-rose-950">Supplier Pricing Notice</p>
            <p className="mt-0.5">{errorMessage}</p>
          </div>
          <button
            onClick={() => setErrorMessage(null)}
            className="text-rose-500 hover:text-rose-800 cursor-pointer font-bold"
          >
            ✕
          </button>
        </div>
      )}

      {/* Step 1: Upload View */}
      {step === 'upload' && (
        <>
          <SupplierPdfUploader
            pdfFile={pdfFile}
            onPdfSelect={handlePdfSelect}
            onExtract={handleExtract}
            isLoading={isLoading}
            onLoadSample={handleLoadSample}
          />
          <FutureStagesCard />
        </>
      )}

      {/* Step 2: Extracting View */}
      {step === 'extracting' && (
        <div className="rounded-3xl border border-[#786446]/15 bg-white/70 backdrop-blur-xl p-12 text-center max-w-lg mx-auto shadow-xs space-y-4 my-12">
          <div className="w-16 h-16 rounded-2xl bg-[#C98B4A]/10 flex items-center justify-center mx-auto text-[#C98B4A] shadow-xs">
            <RefreshCw className="w-8 h-8 animate-spin" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-[#26231F]">Extracting Supplier Quotation</h3>
            <p className="text-xs text-[#716B61] mt-1 max-w-sm mx-auto">
              Extracting supplier name, quote number, date, line items, currency, charges, discounts, and lead times...
            </p>
          </div>
          <div className="flex items-center justify-center space-x-2 text-[11px] text-[#A66E32] font-semibold bg-[#C98B4A]/10 px-3 py-1.5 rounded-full w-max mx-auto border border-[#C98B4A]/20">
            <Sparkles className="w-3.5 h-3.5" />
            <span>Preserving leading zero part numbers & audit trail</span>
          </div>
        </div>
      )}

      {/* Complete 4-Stage Interactive Pipeline Navigator */}
      {quotation && step !== 'upload' && step !== 'extracting' && (
        <div className="flex items-center space-x-2 bg-white/85 backdrop-blur-md p-2 rounded-2xl border border-[#786446]/15 overflow-x-auto shadow-2xs">
          {/* Stage 1 Tab */}
          <button
            onClick={() => setStep('review')}
            className={`px-3.5 py-2 rounded-xl text-xs font-bold transition cursor-pointer flex items-center space-x-2 shrink-0 ${
              step === 'review'
                ? 'bg-[#26231F] text-white shadow-xs'
                : 'text-[#716B61] hover:text-[#26231F] hover:bg-[#786446]/10'
            }`}
          >
            <FileText className="w-3.5 h-3.5" />
            <span>1. Extraction & Review</span>
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
          </button>

          {/* Stage 2 Tab */}
          <button
            onClick={() => setStep('pricing')}
            className={`px-3.5 py-2 rounded-xl text-xs font-bold transition cursor-pointer flex items-center space-x-2 shrink-0 ${
              step === 'pricing'
                ? 'bg-[#26231F] text-white shadow-xs'
                : 'text-[#716B61] hover:text-[#26231F] hover:bg-[#786446]/10'
            }`}
          >
            <Calculator className="w-3.5 h-3.5" />
            <span>2. Pricing Calculation</span>
            <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-emerald-500/20 text-emerald-800">Live</span>
          </button>

          {/* Stage 3 Tab */}
          <button
            onClick={() => {
              if (calculatedItems.length === 0) {
                setStep('pricing');
              } else {
                setStep('approval');
              }
            }}
            className={`px-3.5 py-2 rounded-xl text-xs font-bold transition cursor-pointer flex items-center space-x-2 shrink-0 ${
              step === 'approval'
                ? 'bg-[#26231F] text-white shadow-xs'
                : 'text-[#716B61] hover:text-[#26231F] hover:bg-[#786446]/10'
            }`}
          >
            <UserCheck className="w-3.5 h-3.5" />
            <span>3. Procurement Approval</span>
            <span className={`text-[10px] px-1.5 py-0.2 rounded-full capitalize ${
              approvalStatus === 'approved'
                ? 'bg-emerald-500/20 text-emerald-800 font-bold'
                : approvalStatus === 'rejected'
                ? 'bg-rose-500/20 text-rose-800 font-bold'
                : 'bg-amber-500/20 text-amber-800 font-bold'
            }`}>
              {approvalStatus}
            </span>
          </button>

          {/* Stage 4 Tab */}
          <button
            onClick={() => {
              if (calculatedItems.length === 0) {
                setStep('pricing');
              } else {
                setStep('zoho');
              }
            }}
            className={`px-3.5 py-2 rounded-xl text-xs font-bold transition cursor-pointer flex items-center space-x-2 shrink-0 ${
              step === 'zoho'
                ? 'bg-[#26231F] text-white shadow-xs'
                : 'text-[#716B61] hover:text-[#26231F] hover:bg-[#786446]/10'
            }`}
          >
            <BookOpen className="w-3.5 h-3.5" />
            <span>4. Zoho Books Sync</span>
            <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-blue-500/20 text-blue-900 font-bold">Ready</span>
          </button>
        </div>
      )}

      {/* Stage 1: Review View */}
      {step === 'review' && quotation && validation && (
        <>
          <SupplierQuoteReview
            quotation={quotation}
            validation={validation}
            onChange={setQuotation}
            onRevalidate={handleRevalidate}
            onReset={handleReset}
            isValidating={isValidating}
            onProceedToPricing={() => setStep('pricing')}
          />
          <FutureStagesCard
            currentStage={step}
            canNavigate={true}
            onSelectStage={(s) => setStep(s)}
          />
        </>
      )}

      {/* Stage 2: Pricing Calculation View */}
      {step === 'pricing' && quotation && (
        <>
          <PricingCalculationStep
            quotation={quotation}
            onBackToReview={() => setStep('review')}
            onProceedToApproval={(items, sum) => {
              setCalculatedItems(items);
              setPricingSummary(sum);
              setStep('approval');
            }}
          />
          <FutureStagesCard
            currentStage={step}
            canNavigate={true}
            onSelectStage={(s) => setStep(s)}
          />
        </>
      )}

      {/* Stage 3: Procurement Approval View */}
      {step === 'approval' && quotation && pricingSummary && (
        <>
          <ProcurementApprovalStep
            quotation={quotation}
            calculatedItems={calculatedItems}
            pricingSummary={pricingSummary}
            approvalStatus={approvalStatus}
            approverName={approverName}
            approvalNotes={approvalNotes}
            onApprovalUpdate={(st, app, nt) => {
              setApprovalStatus(st);
              setApproverName(app);
              setApprovalNotes(nt);
            }}
            onBackToPricing={() => setStep('pricing')}
            onProceedToZoho={() => setStep('zoho')}
          />
          <FutureStagesCard
            currentStage={step}
            canNavigate={true}
            onSelectStage={(s) => setStep(s)}
          />
        </>
      )}

      {/* Stage 4: Zoho Books Sync View */}
      {step === 'zoho' && (
        <>
          <ZohoBooksSyncStep
            quotation={quotation || defaultBrowseQuotation}
            calculatedItems={calculatedItems}
            pricingSummary={pricingSummary || defaultBrowsePricing}
            onBackToApproval={() => setStep(quotation ? 'approval' : 'upload')}
          />
          <FutureStagesCard
            currentStage={step}
            canNavigate={true}
            onSelectStage={(s) => setStep(s)}
          />
        </>
      )}
    </div>
  );
};
