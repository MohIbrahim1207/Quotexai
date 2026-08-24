import React from 'react';
import { FileSpreadsheet, Sparkles, RefreshCw } from 'lucide-react';

interface HeaderProps {
  onReset: () => void;
  isBusy: boolean;
}

export const Header: React.FC<HeaderProps> = ({ onReset, isBusy }) => {
  return (
    <header className="border-b border-[#786446]/10 bg-white/70 backdrop-blur-xl sticky top-0 z-40 shadow-xs transition-colors">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-18 flex items-center justify-between">
        <div className="flex items-center space-x-3.5">
          <div className="w-10 h-10 rounded-2xl bg-[#26231F] flex items-center justify-center shadow-md shadow-[#26231F]/10 ring-1 ring-black/5">
            <FileSpreadsheet className="w-5 h-5 text-[#F5F1E8]" />
          </div>
          <div>
            <div className="flex items-center space-x-2.5">
              <span className="font-bold text-lg text-[#26231F] tracking-tight">QuotexAI</span>
              <span className="text-[10px] uppercase font-semibold tracking-wider px-2.5 py-0.5 rounded-full bg-[#C98B4A]/10 text-[#A66E32] border border-[#C98B4A]/20">
                Enterprise B2B
              </span>
            </div>
            <p className="text-xs text-[#716B61]">AI PDF to Excel Quotation Converter</p>
          </div>
        </div>

        <div className="flex items-center space-x-3.5">
          <div className="hidden sm:flex items-center space-x-2 text-xs font-medium text-[#716B61] bg-white/80 px-3.5 py-2 rounded-xl border border-[#786446]/15 shadow-2xs backdrop-blur-md">
            <Sparkles className="w-3.5 h-3.5 text-[#C98B4A] animate-pulse" />
            <span>Gemini AI Engine</span>
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
          </div>

          <button
            onClick={onReset}
            disabled={isBusy}
            className="flex items-center space-x-2 text-xs font-semibold text-[#26231F] hover:text-black px-4 py-2 rounded-xl bg-white/80 hover:bg-white border border-[#786446]/20 shadow-2xs hover:shadow-xs transition duration-150 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-[#716B61] ${isBusy ? 'animate-spin' : ''}`} />
            <span>New Conversion</span>
          </button>
        </div>
      </div>
    </header>
  );
};
