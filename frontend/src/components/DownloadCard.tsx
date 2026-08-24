import React from 'react';
import { Download, FileCheck, CheckCircle2, RefreshCw } from 'lucide-react';
import type { GenerateExcelResponse } from '../types/quotation';

interface DownloadCardProps {
  response: GenerateExcelResponse;
  onDownload: () => void;
  onReset: () => void;
  quoteNumber?: string;
  customer?: string;
}

export const DownloadCard: React.FC<DownloadCardProps> = ({
  response,
  onDownload,
  onReset,
  quoteNumber,
  customer,
}) => {
  return (
    <div className="max-w-2xl mx-auto py-12 px-4">
      <div className="bg-white/80 border border-[#786446]/15 rounded-3xl p-8 sm:p-10 shadow-xl backdrop-blur-xl text-center space-y-6">
        <div className="w-18 h-18 rounded-3xl bg-[#26231F] text-[#F5F1E8] mx-auto flex items-center justify-center shadow-lg shadow-black/10">
          <FileCheck className="w-9 h-9 text-[#C98B4A]" />
        </div>

        <div className="space-y-2">
          <span className="inline-flex items-center space-x-1.5 text-xs font-bold px-3.5 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 shadow-2xs">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Excel Generated Successfully</span>
          </span>
          <h2 className="text-2xl sm:text-3xl font-extrabold text-[#26231F] tracking-tight">{response.filename}</h2>
          <p className="text-xs sm:text-sm text-[#716B61] max-w-md mx-auto leading-relaxed">
            Your quotation data has been populated into the formatted template while strictly preserving formulas, merged headers, borders, styles, and leading zeros.
          </p>
        </div>

        <div className="grid grid-cols-3 gap-3 p-5 rounded-2xl bg-[#F5F1E8]/70 border border-[#786446]/15 text-left">
          <div>
            <p className="text-[11px] font-bold text-[#716B61] uppercase tracking-wider">Quote Reference</p>
            <p className="text-xs font-bold text-[#26231F] font-mono mt-1">{quoteNumber || '41260607'}</p>
            {customer && <p className="text-[10px] text-[#716B61] truncate mt-0.5">{customer}</p>}
          </div>
          <div>
            <p className="text-[11px] font-bold text-[#716B61] uppercase tracking-wider">Items Written</p>
            <p className="text-xs font-bold text-emerald-700 font-mono mt-1">{response.total_items_written} Items</p>
          </div>
          <div>
            <p className="text-[11px] font-bold text-[#716B61] uppercase tracking-wider">Grand Total</p>
            <p className="text-xs font-bold text-[#26231F] font-mono mt-1">
              € {response.grand_total_written.toFixed(2)}
            </p>
          </div>
        </div>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
          <button
            type="button"
            onClick={onDownload}
            className="w-full sm:w-auto inline-flex items-center justify-center space-x-2.5 px-8 py-3.5 rounded-2xl text-sm font-bold text-white bg-[#26231F] hover:bg-black shadow-lg shadow-black/10 hover:shadow-xl hover:scale-[1.02] active:scale-[0.98] transition-all duration-150 cursor-pointer"
          >
            <Download className="w-4 h-4 text-[#C98B4A]" />
            <span>Download Excel (.xlsx)</span>
          </button>

          <button
            type="button"
            onClick={onReset}
            className="w-full sm:w-auto inline-flex items-center justify-center space-x-2 px-6 py-3.5 rounded-2xl text-xs font-bold text-[#26231F] bg-white hover:bg-white/90 border border-[#786446]/20 shadow-2xs transition cursor-pointer"
          >
            <RefreshCw className="w-3.5 h-3.5 text-[#716B61]" />
            <span>Convert Another Quote</span>
          </button>
        </div>
      </div>
    </div>
  );
};
