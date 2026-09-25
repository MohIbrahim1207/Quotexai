import React from 'react';
import { FileText, Calculator, CheckCircle2, UserCheck, BookOpen, Sparkles } from 'lucide-react';

interface FutureStagesCardProps {
  currentStage?: 'upload' | 'extracting' | 'review' | 'pricing' | 'approval' | 'zoho';
  onSelectStage?: (stage: 'review' | 'pricing' | 'approval' | 'zoho') => void;
  canNavigate?: boolean;
}

export const FutureStagesCard: React.FC<FutureStagesCardProps> = ({
  currentStage,
  onSelectStage,
  canNavigate = false,
}) => {
  return (
    <div className="rounded-3xl border border-[#786446]/15 bg-white/70 backdrop-blur-xl p-6 shadow-xs space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[#786446]/10 pb-4">
        <div>
          <div className="flex items-center space-x-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-[#A66E32]">Pipeline Architecture</span>
            <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-800 border border-emerald-500/25 flex items-center space-x-1">
              <Sparkles className="w-3 h-3 text-emerald-600" />
              <span>All 4 Stages Unlocked</span>
            </span>
          </div>
          <h3 className="text-lg font-bold text-[#26231F] mt-0.5">Supplier Procurement & ERP Synchronization</h3>
        </div>
        <div className="flex items-center space-x-1.5 text-xs text-emerald-800 bg-emerald-500/10 px-3 py-1.5 rounded-xl border border-emerald-500/20 self-start sm:self-auto font-medium">
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
          <span>Extraction • Pricing • Approval • Zoho Books are Active</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* Stage 1: Extraction & Review */}
        <div
          onClick={() => canNavigate && onSelectStage && onSelectStage('review')}
          className={`p-4 rounded-2xl border transition flex flex-col justify-between space-y-3 relative ${
            canNavigate ? 'cursor-pointer hover:shadow-xs' : ''
          } ${
            currentStage === 'review' || currentStage === 'upload'
              ? 'bg-emerald-500/10 border-emerald-500/30 ring-1 ring-emerald-500/20'
              : 'bg-white/60 border-[#786446]/15 hover:border-[#C98B4A]/30'
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-800">
              Stage 1 • Active
            </span>
            <FileText className="w-4 h-4 text-emerald-600" />
          </div>
          <div>
            <h4 className="text-sm font-bold text-[#26231F]">PDF Extraction & Review</h4>
            <p className="text-xs text-[#716B61] mt-1 leading-relaxed">
              Extract 14 critical quotation parameters, audit validation issues, and edit fields.
            </p>
          </div>
          <div className="pt-2 border-t border-[#786446]/10 flex items-center justify-between text-[11px] font-medium text-emerald-700">
            <span>Validated Extraction</span>
            <span>Live</span>
          </div>
        </div>

        {/* Stage 2: Pricing Calculation */}
        <div
          onClick={() => canNavigate && onSelectStage && onSelectStage('pricing')}
          className={`p-4 rounded-2xl border transition flex flex-col justify-between space-y-3 relative ${
            canNavigate ? 'cursor-pointer hover:shadow-xs' : ''
          } ${
            currentStage === 'pricing'
              ? 'bg-emerald-500/10 border-emerald-500/30 ring-1 ring-emerald-500/20'
              : 'bg-white/60 border-[#786446]/15 hover:border-[#C98B4A]/30'
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-800">
              Stage 2 • Active
            </span>
            <Calculator className="w-4 h-4 text-emerald-600" />
          </div>
          <div>
            <h4 className="text-sm font-bold text-[#26231F]">Pricing Calculation</h4>
            <p className="text-xs text-[#716B61] mt-1 leading-relaxed">
              Excel workbook formulas, landed costs, currency conversion (EUR→IDR @ 17,500), and margins.
            </p>
          </div>
          <div className="pt-2 border-t border-[#786446]/10 flex items-center justify-between text-[11px] font-medium text-emerald-700">
            <span>Deterministic Formulas</span>
            <span>Live</span>
          </div>
        </div>

        {/* Stage 3: Procurement Approval */}
        <div
          onClick={() => canNavigate && onSelectStage && onSelectStage('approval')}
          className={`p-4 rounded-2xl border transition flex flex-col justify-between space-y-3 relative ${
            canNavigate ? 'cursor-pointer hover:shadow-xs' : ''
          } ${
            currentStage === 'approval'
              ? 'bg-amber-500/10 border-amber-500/30 ring-1 ring-amber-500/20'
              : 'bg-white/60 border-[#786446]/15 hover:border-[#C98B4A]/30'
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-900">
              Stage 3 • Active
            </span>
            <UserCheck className="w-4 h-4 text-amber-600" />
          </div>
          <div>
            <h4 className="text-sm font-bold text-[#26231F]">Procurement Approval</h4>
            <p className="text-xs text-[#716B61] mt-1 leading-relaxed">
              Management signoff with Pending, Approved, and Rejected statuses with audit notes.
            </p>
          </div>
          <div className="pt-2 border-t border-[#786446]/10 flex items-center justify-between text-[11px] text-amber-800 font-semibold">
            <span>Governance & Signoff</span>
            <span>Live</span>
          </div>
        </div>

        {/* Stage 4: Zoho Books Sync */}
        <div
          onClick={() => canNavigate && onSelectStage && onSelectStage('zoho')}
          className={`p-4 rounded-2xl border transition flex flex-col justify-between space-y-3 relative ${
            canNavigate ? 'cursor-pointer hover:shadow-xs' : ''
          } ${
            currentStage === 'zoho'
              ? 'bg-blue-500/10 border-blue-500/30 ring-1 ring-blue-500/20'
              : 'bg-white/60 border-[#786446]/15 hover:border-[#C98B4A]/30'
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-900">
              Stage 4 • Active
            </span>
            <BookOpen className="w-4 h-4 text-blue-600" />
          </div>
          <div>
            <h4 className="text-sm font-bold text-[#26231F]">Zoho Books Sync</h4>
            <p className="text-xs text-[#716B61] mt-1 leading-relaxed">
              SKU catalog matching (CREATE/UPDATE preview) with explicit user confirmation guardrail.
            </p>
          </div>
          <div className="pt-2 border-t border-[#786446]/10 flex items-center justify-between text-[11px] text-blue-800 font-semibold">
            <span>ERP Connector</span>
            <span>Live</span>
          </div>
        </div>
      </div>
    </div>
  );
};
