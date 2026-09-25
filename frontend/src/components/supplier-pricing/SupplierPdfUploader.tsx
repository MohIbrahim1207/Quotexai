import React, { useRef } from 'react';
import { FileText, Upload, CheckCircle2, ArrowRight, ShieldCheck, Zap } from 'lucide-react';

interface SupplierPdfUploaderProps {
  pdfFile: File | null;
  onPdfSelect: (file: File) => void;
  onExtract: () => void;
  isLoading: boolean;
  onLoadSample?: () => void;
}

export const SupplierPdfUploader: React.FC<SupplierPdfUploaderProps> = ({
  pdfFile,
  onPdfSelect,
  onExtract,
  isLoading,
  onLoadSample,
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      if (file.name.toLowerCase().endsWith('.pdf')) {
        onPdfSelect(file);
      }
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="space-y-8 max-w-4xl mx-auto py-6">
      {/* Header Banner */}
      <div className="text-center space-y-3">
        <div className="inline-flex items-center space-x-2 text-xs font-semibold px-3.5 py-1.5 rounded-full bg-white/80 border border-[#786446]/15 text-[#716B61] shadow-2xs backdrop-blur-md">
          <span className="w-2 h-2 rounded-full bg-[#C98B4A]"></span>
          <span>Stage 1: Ingestion & Validation</span>
        </div>
        <h2 className="text-3xl sm:text-4xl font-extrabold text-[#26231F] tracking-tight">
          Supplier Pricing & Zoho Books
        </h2>
        <p className="text-[#716B61] text-sm sm:text-base max-w-2xl mx-auto font-normal">
          Upload any supplier quotation PDF to automatically extract 14 key procurement fields, inspect line-item pricing and freight charges, review validation alerts, and prepare for downstream pricing calculations.
        </p>
      </div>

      {/* Main Upload Dropzone Card */}
      <div
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`group cursor-pointer rounded-3xl border p-10 transition-all duration-300 flex flex-col items-center justify-center text-center min-h-[280px] backdrop-blur-xl relative overflow-hidden ${
          pdfFile
            ? 'border-emerald-500/30 bg-emerald-500/5 ring-1 ring-emerald-500/20'
            : 'border-[#786446]/15 bg-white/70 hover:bg-white/90 hover:border-[#C98B4A]/40 shadow-xs hover:shadow-md'
        }`}
      >
        <input
          type="file"
          ref={fileInputRef}
          onChange={(e) => e.target.files?.[0] && onPdfSelect(e.target.files[0])}
          accept=".pdf"
          className="hidden"
        />

        {pdfFile ? (
          <div className="space-y-4 max-w-md animate-in fade-in zoom-in-95 duration-200">
            <div className="w-16 h-16 rounded-2xl bg-emerald-100 flex items-center justify-center mx-auto text-emerald-600 shadow-xs">
              <CheckCircle2 className="w-8 h-8" />
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-emerald-700">PDF Ready for Extraction</p>
              <h3 className="text-lg font-bold text-[#26231F] truncate mt-1">{pdfFile.name}</h3>
              <p className="text-xs text-[#716B61] mt-0.5">{formatFileSize(pdfFile.size)}</p>
            </div>
            <div className="inline-flex items-center space-x-1.5 text-xs text-[#716B61] bg-white/80 px-3 py-1.5 rounded-xl border border-[#786446]/10">
              <span>Click or drop another file to replace</span>
            </div>
          </div>
        ) : (
          <div className="space-y-4 max-w-md">
            <div className="w-16 h-16 rounded-2xl bg-[#C98B4A]/10 flex items-center justify-center mx-auto text-[#C98B4A] group-hover:scale-105 group-hover:bg-[#C98B4A]/15 transition duration-300 shadow-2xs">
              <Upload className="w-8 h-8" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-[#26231F]">Upload Supplier Quotation PDF</h3>
              <p className="text-xs text-[#716B61] mt-1">
                Drag and drop your vendor quotation document here, or browse files
              </p>
            </div>
            <div className="flex flex-wrap items-center justify-center gap-2 pt-2">
              <span className="text-[11px] font-medium text-[#716B61] bg-[#786446]/5 px-2.5 py-1 rounded-lg">
                Multi-page Tables
              </span>
              <span className="text-[11px] font-medium text-[#716B61] bg-[#786446]/5 px-2.5 py-1 rounded-lg">
                Preserves Leading Zeros
              </span>
              <span className="text-[11px] font-medium text-[#716B61] bg-[#786446]/5 px-2.5 py-1 rounded-lg">
                Charges & Lead Times
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Action Buttons & Sample Quick-Loader */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-2">
        <div className="flex items-center space-x-2">
          {onLoadSample && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onLoadSample();
              }}
              className="flex items-center space-x-2 text-xs font-semibold text-[#716B61] hover:text-[#26231F] bg-white/80 hover:bg-white px-4 py-2.5 rounded-xl border border-[#786446]/15 shadow-2xs transition"
            >
              <Zap className="w-3.5 h-3.5 text-[#C98B4A]" />
              <span>Load Sample Supplier Quote</span>
            </button>
          )}
        </div>

        <button
          type="button"
          onClick={onExtract}
          disabled={!pdfFile || isLoading}
          className="w-full sm:w-auto flex items-center justify-center space-x-2.5 px-8 py-3.5 rounded-2xl bg-[#26231F] text-[#F5F1E8] font-bold text-sm shadow-md hover:bg-black transition duration-200 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
        >
          {isLoading ? (
            <>
              <div className="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin" />
              <span>Extracting 14 Fields...</span>
            </>
          ) : (
            <>
              <span>Extract & Review Quotation</span>
              <ArrowRight className="w-4 h-4 text-[#C98B4A]" />
            </>
          )}
        </button>
      </div>

      {/* Feature Highlights Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-4">
        <div className="p-4 rounded-2xl bg-white/60 border border-[#786446]/10 backdrop-blur-md flex items-start space-x-3">
          <ShieldCheck className="w-5 h-5 text-[#C98B4A] shrink-0 mt-0.5" />
          <div>
            <h4 className="text-xs font-bold text-[#26231F]">Deterministic Validation</h4>
            <p className="text-[11px] text-[#716B61] mt-0.5 leading-relaxed">
              Flags missing supplier names, part numbers, missing prices, or math mismatches across line totals.
            </p>
          </div>
        </div>

        <div className="p-4 rounded-2xl bg-white/60 border border-[#786446]/10 backdrop-blur-md flex items-start space-x-3">
          <FileText className="w-5 h-5 text-[#C98B4A] shrink-0 mt-0.5" />
          <div>
            <h4 className="text-xs font-bold text-[#26231F]">Full 14-Field Schema</h4>
            <p className="text-[11px] text-[#716B61] mt-0.5 leading-relaxed">
              Extracts supplier name, quote #, date, parts, quantities, units, packaging, freight, discount, and lead time.
            </p>
          </div>
        </div>

        <div className="p-4 rounded-2xl bg-white/60 border border-[#786446]/10 backdrop-blur-md flex items-start space-x-3">
          <Zap className="w-5 h-5 text-[#C98B4A] shrink-0 mt-0.5" />
          <div>
            <h4 className="text-xs font-bold text-[#26231F]">Future Pipeline Ready</h4>
            <p className="text-[11px] text-[#716B61] mt-0.5 leading-relaxed">
              Built specifically to feed Stage 2 (Pricing), Stage 3 (Approvals), and Stage 4 (Zoho Books Sync).
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
