import React, { useRef } from 'react';
import { FileText, FileSpreadsheet, Upload, CheckCircle2, ArrowRight } from 'lucide-react';

interface DropzoneProps {
  pdfFile: File | null;
  templateFile: File | null;
  onPdfSelect: (file: File) => void;
  onTemplateSelect: (file: File) => void;
  onExtract: () => void;
  isLoading: boolean;
}

export const Dropzone: React.FC<DropzoneProps> = ({
  pdfFile,
  templateFile,
  onPdfSelect,
  onTemplateSelect,
  onExtract,
  isLoading,
}) => {
  const pdfInputRef = useRef<HTMLInputElement>(null);
  const templateInputRef = useRef<HTMLInputElement>(null);

  const handlePdfDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      if (file.name.toLowerCase().endsWith('.pdf')) {
        onPdfSelect(file);
      }
    }
  };

  const handleTemplateDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      if (file.name.toLowerCase().endsWith('.xlsx') || file.name.toLowerCase().endsWith('.xlsm')) {
        onTemplateSelect(file);
      }
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const canExtract = pdfFile !== null;

  return (
    <div className="space-y-12 max-w-5xl mx-auto py-10 relative">
      {/* Subtle warm ambient background blur shapes */}
      <div className="absolute top-10 left-1/4 w-96 h-96 bg-[#C98B4A]/10 rounded-full blur-3xl pointer-events-none -z-10 animate-pulse" />
      <div className="absolute top-20 right-1/4 w-96 h-96 bg-[#E2D5BE]/40 rounded-full blur-3xl pointer-events-none -z-10" />

      {/* Hero Section */}
      <div className="text-center space-y-4 max-w-3xl mx-auto">
        <div className="inline-flex items-center space-x-2 text-xs font-semibold px-3.5 py-1.5 rounded-full bg-white/80 border border-[#786446]/15 text-[#716B61] shadow-2xs backdrop-blur-md mb-2">
          <span className="w-2 h-2 rounded-full bg-[#C98B4A]"></span>
          <span>Enterprise Document Processing</span>
        </div>

        <h1 className="text-4xl sm:text-5xl font-extrabold text-[#26231F] tracking-tight leading-tight">
          Convert Supplier Quotations to Excel
        </h1>
        <p className="text-[#716B61] text-base sm:text-lg max-w-2xl mx-auto font-normal leading-relaxed">
          Extract quotation tables, line items, and equipment groupings from PDF quotes using Gemini AI, validate prices deterministically, and populate your exact Excel template without breaking formatting.
        </p>
      </div>

      {/* Dual Upload Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* PDF Upload Card */}
        <div
          onDragOver={(e) => e.preventDefault()}
          onDrop={handlePdfDrop}
          onClick={() => pdfInputRef.current?.click()}
          className={`group cursor-pointer rounded-3xl border p-8 transition-all duration-300 flex flex-col items-center justify-center text-center min-h-[300px] backdrop-blur-xl relative overflow-hidden ${
            pdfFile
              ? 'border-[#C98B4A]/40 bg-white/90 shadow-md ring-1 ring-[#C98B4A]/20'
              : 'border-[#786446]/15 hover:border-[#C98B4A]/40 bg-white/65 hover:bg-white/85 shadow-sm hover:shadow-lg hover:-translate-y-1'
          }`}
        >
          <input
            ref={pdfInputRef}
            type="file"
            accept=".pdf"
            className="hidden"
            onChange={(e) => {
              if (e.target.files && e.target.files[0]) {
                onPdfSelect(e.target.files[0]);
              }
            }}
          />

          <div
            className={`w-16 h-16 rounded-2xl flex items-center justify-center mb-5 transition-transform duration-300 ${
              pdfFile
                ? 'bg-[#26231F] text-white shadow-md shadow-black/10 scale-105'
                : 'bg-[#F5F1E8] text-[#716B61] group-hover:text-[#26231F] group-hover:scale-105 border border-[#786446]/10'
            }`}
          >
            {pdfFile ? <CheckCircle2 className="w-8 h-8 text-emerald-400" /> : <FileText className="w-8 h-8" />}
          </div>

          <h3 className="text-lg font-bold text-[#26231F] mb-1.5">
            {pdfFile ? 'Quotation PDF Selected' : 'Upload Supplier Quotation PDF'}
          </h3>

          {pdfFile ? (
            <div className="space-y-1.5 mt-1">
              <p className="text-sm font-semibold text-[#26231F] max-w-[280px] truncate">{pdfFile.name}</p>
              <p className="text-xs text-[#716B61]">{formatFileSize(pdfFile.size)} • PDF Document</p>
              <span className="inline-block mt-3 text-[11px] font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200 px-3 py-1 rounded-full shadow-2xs">
                ✓ Ready for Extraction
              </span>
            </div>
          ) : (
            <div className="space-y-3 mt-1">
              <p className="text-xs text-[#716B61] max-w-xs leading-relaxed">
                Drag & drop your supplier quotation PDF here, or click to browse.
              </p>
              <div className="inline-flex items-center space-x-1.5 text-xs font-semibold text-[#26231F] bg-white px-4 py-2 rounded-xl border border-[#786446]/20 shadow-2xs group-hover:border-[#26231F] transition">
                <Upload className="w-3.5 h-3.5 text-[#716B61]" />
                <span>Select PDF file</span>
              </div>
            </div>
          )}
        </div>

        {/* Excel Template Upload Card */}
        <div
          onDragOver={(e) => e.preventDefault()}
          onDrop={handleTemplateDrop}
          onClick={() => templateInputRef.current?.click()}
          className={`group cursor-pointer rounded-3xl border p-8 transition-all duration-300 flex flex-col items-center justify-center text-center min-h-[300px] backdrop-blur-xl relative overflow-hidden ${
            templateFile
              ? 'border-[#C98B4A]/40 bg-white/90 shadow-md ring-1 ring-[#C98B4A]/20'
              : 'border-[#786446]/15 hover:border-[#C98B4A]/40 bg-white/65 hover:bg-white/85 shadow-sm hover:shadow-lg hover:-translate-y-1'
          }`}
        >
          <input
            ref={templateInputRef}
            type="file"
            accept=".xlsx,.xlsm"
            className="hidden"
            onChange={(e) => {
              if (e.target.files && e.target.files[0]) {
                onTemplateSelect(e.target.files[0]);
              }
            }}
          />

          <div
            className={`w-16 h-16 rounded-2xl flex items-center justify-center mb-5 transition-transform duration-300 ${
              templateFile
                ? 'bg-[#26231F] text-white shadow-md shadow-black/10 scale-105'
                : 'bg-[#F5F1E8] text-[#716B61] group-hover:text-[#26231F] group-hover:scale-105 border border-[#786446]/10'
            }`}
          >
            {templateFile ? <CheckCircle2 className="w-8 h-8 text-emerald-400" /> : <FileSpreadsheet className="w-8 h-8" />}
          </div>

          <h3 className="text-lg font-bold text-[#26231F] mb-1.5">
            {templateFile ? 'Excel Template Selected' : 'Upload Excel Quotation Template'}
          </h3>

          {templateFile ? (
            <div className="space-y-1.5 mt-1">
              <p className="text-sm font-semibold text-[#26231F] max-w-[280px] truncate">{templateFile.name}</p>
              <p className="text-xs text-[#716B61]">{formatFileSize(templateFile.size)} • Excel Spreadsheet</p>
              <span className="inline-block mt-3 text-[11px] font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200 px-3 py-1 rounded-full shadow-2xs">
                ✓ Template Formatting Preserved
              </span>
            </div>
          ) : (
            <div className="space-y-3 mt-1">
              <p className="text-xs text-[#716B61] max-w-xs leading-relaxed">
                Upload your company's existing .xlsx quotation template, or use our standard template.
              </p>
              <div className="inline-flex items-center space-x-1.5 text-xs font-semibold text-[#26231F] bg-white px-4 py-2 rounded-xl border border-[#786446]/20 shadow-2xs group-hover:border-[#26231F] transition">
                <Upload className="w-3.5 h-3.5 text-[#716B61]" />
                <span>Select Excel template (Optional)</span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Primary CTA */}
      <div className="flex justify-center pt-2">
        <button
          type="button"
          onClick={onExtract}
          disabled={!canExtract || isLoading}
          className="inline-flex items-center space-x-3 text-sm font-bold text-white bg-[#26231F] hover:bg-black disabled:bg-[#716B61]/30 disabled:text-[#716B61] px-9 py-4 rounded-2xl shadow-lg shadow-black/10 hover:shadow-xl hover:scale-[1.02] active:scale-[0.98] transition-all duration-200 disabled:shadow-none disabled:cursor-not-allowed cursor-pointer"
        >
          <span>Extract & Analyze Quotation</span>
          <ArrowRight className="w-4 h-4 text-[#C98B4A]" />
        </button>
      </div>

      {/* Feature Highlights */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-5 pt-8 border-t border-[#786446]/10 text-center sm:text-left">
        <div className="p-5 rounded-2xl bg-white/60 border border-[#786446]/10 shadow-2xs backdrop-blur-md">
          <p className="text-xs font-bold text-[#26231F]">Zero-Loss Part Numbers</p>
          <p className="text-xs text-[#716B61] mt-1.5 leading-relaxed">
            Leading zeros like <code className="text-[#26231F] font-semibold bg-[#F5F1E8] px-1 py-0.5 rounded">00138737</code> and <code className="text-[#26231F] font-semibold bg-[#F5F1E8] px-1 py-0.5 rounded">02174072</code> are strictly retained.
          </p>
        </div>
        <div className="p-5 rounded-2xl bg-white/60 border border-[#786446]/10 shadow-2xs backdrop-blur-md">
          <p className="text-xs font-bold text-[#26231F]">100% Format Preservation</p>
          <p className="text-xs text-[#716B61] mt-1.5 leading-relaxed">
            Preserves existing formulas, merged headers, fonts, and borders.
          </p>
        </div>
        <div className="p-5 rounded-2xl bg-white/60 border border-[#786446]/10 shadow-2xs backdrop-blur-md">
          <p className="text-xs font-bold text-[#26231F]">Deterministic Validation</p>
          <p className="text-xs text-[#716B61] mt-1.5 leading-relaxed">
            AI outputs are cross-checked against source PDF text and arithmetic.
          </p>
        </div>
      </div>
    </div>
  );
};
