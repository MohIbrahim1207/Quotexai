import React, { useState } from 'react';
import {
  ShieldAlert,
  CheckCircle2,
  XCircle,
  Clock,
  ArrowLeft,
  ArrowRight,
  UserCheck,
  Save,
} from 'lucide-react';
import type {
  SupplierQuotationData,
  CalculatedLinePrice,
  PricingSummary,
  ProcurementApprovalResponse,
} from '../../types/supplierPricing';
import { supplierPricingApi } from '../../services/supplierPricingApi';

interface ProcurementApprovalStepProps {
  quotation: SupplierQuotationData;
  calculatedItems: CalculatedLinePrice[];
  pricingSummary: PricingSummary;
  approvalStatus: 'pending' | 'approved' | 'rejected';
  approverName: string;
  approvalNotes: string;
  onApprovalUpdate: (status: 'pending' | 'approved' | 'rejected', approver: string, notes: string) => void;
  onBackToPricing: () => void;
  onProceedToZoho: () => void;
}

const formatNum = (val: number | null | undefined, curr?: string) => {
  if (val === null || val === undefined || isNaN(val)) return '0.00';
  const isZeroDec = curr === 'IDR';
  return val.toLocaleString(undefined, {
    minimumFractionDigits: isZeroDec ? 0 : 2,
    maximumFractionDigits: 2,
  });
};

export const ProcurementApprovalStep: React.FC<ProcurementApprovalStepProps> = ({
  quotation,
  calculatedItems,
  pricingSummary,
  approvalStatus: initialStatus,
  approverName: initialApprover,
  approvalNotes: initialNotes,
  onApprovalUpdate,
  onBackToPricing,
  onProceedToZoho,
}) => {
  const [status, setStatus] = useState<'pending' | 'approved' | 'rejected'>(initialStatus || 'pending');
  const [approverName, setApproverName] = useState<string>(initialApprover || 'Procurement Lead');
  const [approvalNotes, setApprovalNotes] = useState<string>(initialNotes || '');
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccessMsg, setSaveSuccessMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const targetCurr = pricingSummary.target_currency || 'EUR';

  const handleSaveApproval = async () => {
    setIsSaving(true);
    setErrorMsg(null);
    setSaveSuccessMsg(null);

    try {
      const res: ProcurementApprovalResponse = await supplierPricingApi.submitApproval({
        quote_number: quotation.quote_number || 'N/A',
        supplier_name: quotation.supplier_name || 'N/A',
        total_selling_price: pricingSummary.total_selling_price,
        currency: targetCurr,
        effective_margin_percent: pricingSummary.overall_margin_percent,
        status,
        approver_name: approverName,
        approval_notes: approvalNotes,
      });

      if (res.success) {
        onApprovalUpdate(status, approverName, approvalNotes);
        setSaveSuccessMsg(res.message);
      }
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'Failed to record approval decision.');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Top Header Card */}
      <div className="rounded-3xl border border-[#786446]/15 bg-white/75 backdrop-blur-xl p-6 shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#786446]/10 pb-4">
          <div className="flex items-start space-x-3">
            <button
              onClick={onBackToPricing}
              className="p-2 rounded-xl bg-white border border-[#786446]/20 text-[#716B61] hover:text-[#26231F] hover:bg-[#786446]/5 transition cursor-pointer shrink-0 mt-0.5"
              title="Return to Stage 2 Pricing"
            >
              <ArrowLeft className="w-4 h-4" />
            </button>
            <div>
              <div className="flex items-center space-x-2 flex-wrap gap-y-1">
                <span className="text-xs font-semibold uppercase tracking-wider text-[#A66E32]">
                  Stage 3 • Governance & Audit
                </span>
                <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-800 border border-amber-500/25 flex items-center space-x-1">
                  <UserCheck className="w-3 h-3 text-amber-600" />
                  <span>Explicit Approval Required • No Auto-Signoff</span>
                </span>
              </div>
              <h2 className="text-xl font-bold text-[#26231F] mt-1">
                Procurement Management Sign-Off
              </h2>
              <p className="text-xs text-[#716B61] mt-0.5">
                Review deterministic margins, set approval status (Pending, Approved, Rejected), and attach signoff notes.
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <span
              className={`px-3 py-1.5 rounded-xl text-xs font-bold flex items-center space-x-1.5 ${
                status === 'approved'
                  ? 'bg-emerald-500/15 text-emerald-850 border border-emerald-500/30'
                  : status === 'rejected'
                  ? 'bg-rose-500/15 text-rose-850 border border-rose-500/30'
                  : 'bg-amber-500/15 text-amber-850 border border-amber-500/30'
              }`}
            >
              {status === 'approved' ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              ) : status === 'rejected' ? (
                <XCircle className="w-4 h-4 text-rose-600" />
              ) : (
                <Clock className="w-4 h-4 text-amber-600" />
              )}
              <span className="capitalize">{status} Decision</span>
            </span>
          </div>
        </div>

        {/* Success or Error Notice */}
        {saveSuccessMsg && (
          <div className="p-3.5 rounded-2xl bg-emerald-50 border border-emerald-200 text-xs text-emerald-900 flex items-center justify-between">
            <span>{saveSuccessMsg}</span>
            <button onClick={() => setSaveSuccessMsg(null)} className="font-bold text-emerald-700">✕</button>
          </div>
        )}
        {errorMsg && (
          <div className="p-3.5 rounded-2xl bg-rose-50 border border-rose-200 text-xs text-rose-900 flex items-center justify-between">
            <span>{errorMsg}</span>
            <button onClick={() => setErrorMsg(null)} className="font-bold text-rose-700">✕</button>
          </div>
        )}

        {/* Quotation Metadata Summary Header */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-2">
          <div className="p-3.5 rounded-2xl bg-[#786446]/5 border border-[#786446]/10 text-xs space-y-0.5">
            <div className="text-[10px] uppercase font-bold text-[#716B61]">Supplier</div>
            <div className="font-bold text-[#26231F] truncate">{quotation.supplier_name || 'N/A'}</div>
          </div>
          <div className="p-3.5 rounded-2xl bg-[#786446]/5 border border-[#786446]/10 text-xs space-y-0.5">
            <div className="text-[10px] uppercase font-bold text-[#716B61]">Quote Reference</div>
            <div className="font-mono font-bold text-[#26231F]">{quotation.quote_number || 'N/A'}</div>
          </div>
          <div className="p-3.5 rounded-2xl bg-[#786446]/5 border border-[#786446]/10 text-xs space-y-0.5">
            <div className="text-[10px] uppercase font-bold text-[#716B61]">Effective Margin</div>
            <div className="font-mono font-black text-emerald-700">{pricingSummary.overall_margin_percent.toFixed(1)}%</div>
          </div>
          <div className="p-3.5 rounded-2xl bg-[#786446]/5 border border-[#786446]/10 text-xs space-y-0.5">
            <div className="text-[10px] uppercase font-bold text-[#716B61]">Total Selling Value</div>
            <div className="font-mono font-black text-emerald-700">{targetCurr} {formatNum(pricingSummary.total_selling_price, targetCurr)}</div>
          </div>
        </div>
      </div>

      {/* Decision Workflow Form Card */}
      <div className="rounded-3xl border border-[#786446]/15 bg-white/75 backdrop-blur-xl p-6 shadow-xs space-y-5">
        <h3 className="text-base font-bold text-[#26231F] flex items-center space-x-2">
          <UserCheck className="w-4 h-4 text-[#C98B4A]" />
          <span>Procurement Decision & Audit Sign-Off</span>
        </h3>

        {/* 3 Status Selection Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {/* Pending */}
          <button
            type="button"
            onClick={() => setStatus('pending')}
            className={`p-4 rounded-2xl border text-left transition cursor-pointer flex items-start space-x-3 ${
              status === 'pending'
                ? 'bg-amber-500/10 border-amber-500 ring-2 ring-amber-500/30'
                : 'bg-white border-[#786446]/15 hover:border-[#786446]/30'
            }`}
          >
            <Clock className={`w-5 h-5 mt-0.5 shrink-0 ${status === 'pending' ? 'text-amber-600' : 'text-[#716B61]'}`} />
            <div>
              <div className="text-xs font-bold text-[#26231F]">Pending Review</div>
              <p className="text-[11px] text-[#716B61] mt-0.5">
                Quotation remains in deliberation. Zoho Books sync remains disabled.
              </p>
            </div>
          </button>

          {/* Approved */}
          <button
            type="button"
            onClick={() => setStatus('approved')}
            className={`p-4 rounded-2xl border text-left transition cursor-pointer flex items-start space-x-3 ${
              status === 'approved'
                ? 'bg-emerald-500/10 border-emerald-500 ring-2 ring-emerald-500/30'
                : 'bg-white border-[#786446]/15 hover:border-emerald-500/30'
            }`}
          >
            <CheckCircle2 className={`w-5 h-5 mt-0.5 shrink-0 ${status === 'approved' ? 'text-emerald-600' : 'text-[#716B61]'}`} />
            <div>
              <div className="text-xs font-bold text-emerald-950">Approve Pricing</div>
              <p className="text-[11px] text-[#716B61] mt-0.5">
                Margins satisfy company policy. Authorizes transition to Stage 4 Zoho Books.
              </p>
            </div>
          </button>

          {/* Rejected */}
          <button
            type="button"
            onClick={() => setStatus('rejected')}
            className={`p-4 rounded-2xl border text-left transition cursor-pointer flex items-start space-x-3 ${
              status === 'rejected'
                ? 'bg-rose-500/10 border-rose-500 ring-2 ring-rose-500/30'
                : 'bg-white border-[#786446]/15 hover:border-rose-500/30'
            }`}
          >
            <XCircle className={`w-5 h-5 mt-0.5 shrink-0 ${status === 'rejected' ? 'text-rose-600' : 'text-[#716B61]'}`} />
            <div>
              <div className="text-xs font-bold text-rose-950">Reject Quotation</div>
              <p className="text-[11px] text-[#716B61] mt-0.5">
                Margin inadequate or supplier price disputed. Prevents Zoho Books sync.
              </p>
            </div>
          </button>
        </div>

        {/* Approver Inputs */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-[#716B61]">Approver Full Name / Role</label>
            <input
              type="text"
              value={approverName}
              onChange={(e) => setApproverName(e.target.value)}
              placeholder="e.g. Jane Doe (Head of Procurement)"
              className="w-full text-xs bg-white border border-[#786446]/20 rounded-xl px-3 py-2 text-[#26231F] font-semibold focus:outline-none focus:border-[#C98B4A]"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-[#716B61]">Approval Notes & Audit Trail</label>
            <textarea
              rows={2}
              value={approvalNotes}
              onChange={(e) => setApprovalNotes(e.target.value)}
              placeholder="Provide context, e.g.: Margin meets 10% threshold; customer PO anticipated."
              className="w-full text-xs bg-white border border-[#786446]/20 rounded-xl px-3 py-2 text-[#26231F] focus:outline-none focus:border-[#C98B4A]"
            />
          </div>
        </div>

        {/* Action Buttons */}
        <div className="pt-3 border-t border-[#786446]/10 flex flex-col sm:flex-row items-center justify-between gap-3">
          <button
            onClick={handleSaveApproval}
            disabled={isSaving}
            className="flex items-center space-x-2 text-xs font-bold px-4 py-2.5 rounded-xl bg-[#26231F] text-white hover:bg-[#3D3730] transition cursor-pointer shadow-xs disabled:opacity-50"
          >
            <Save className="w-3.5 h-3.5" />
            <span>{isSaving ? 'Saving...' : 'Save Decision'}</span>
          </button>

          {status === 'approved' ? (
            <button
              onClick={onProceedToZoho}
              className="flex items-center space-x-2 text-xs font-bold px-5 py-2.5 rounded-xl bg-emerald-700 text-white hover:bg-emerald-800 transition cursor-pointer shadow-xs"
            >
              <span>Proceed to Zoho Books Sync (Stage 4)</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          ) : (
            <div className="text-xs text-[#716B61] italic flex items-center space-x-1.5">
              <ShieldAlert className="w-3.5 h-3.5 text-amber-600" />
              <span>Select "Approve Pricing" and save to unlock Zoho Books Sync.</span>
            </div>
          )}
        </div>
      </div>

      {/* Approved Line Items Summary Table */}
      <div className="rounded-3xl border border-[#786446]/15 bg-white/75 backdrop-blur-xl p-6 shadow-xs space-y-4">
        <h3 className="text-sm font-bold text-[#26231F]">Approved Item Pricing Reference</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-[#786446]/15 bg-[#786446]/5 text-[#716B61]">
                <th className="py-2.5 px-3 font-bold w-12 text-center">#</th>
                <th className="py-2.5 px-3 font-bold">Part Number / Description</th>
                <th className="py-2.5 px-3 font-bold text-center">Qty</th>
                <th className="py-2.5 px-3 font-bold text-right">Landed Unit ({targetCurr})</th>
                <th className="py-2.5 px-3 font-bold text-center">Margin %</th>
                <th className="py-2.5 px-3 font-bold text-right bg-[#C98B4A]/10 text-[#26231F]">Final Selling Price ({targetCurr})</th>
                <th className="py-2.5 px-3 font-bold text-right bg-[#C98B4A]/15 text-[#26231F]">Line Total ({targetCurr})</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#786446]/10">
              {calculatedItems.map((it) => (
                <tr key={it.line_number} className="hover:bg-[#786446]/5">
                  <td className="py-2.5 px-3 text-center font-bold text-[#716B61]">{it.line_number}</td>
                  <td className="py-2.5 px-3">
                    <span className="font-mono font-bold text-[#26231F]">{it.part_number}</span>
                    <span className="text-[11px] text-[#716B61] block">{it.description}</span>
                  </td>
                  <td className="py-2.5 px-3 text-center font-mono">{it.quantity} {it.unit}</td>
                  <td className="py-2.5 px-3 text-right font-mono">{targetCurr} {formatNum(it.landed_cost_unit, targetCurr)}</td>
                  <td className="py-2.5 px-3 text-center font-mono font-bold text-amber-900">{it.margin_percent}%</td>
                  <td className="py-2.5 px-3 text-right font-mono font-bold text-emerald-800 bg-[#C98B4A]/5">
                    {targetCurr} {formatNum(it.final_unit_selling_price, targetCurr)}
                  </td>
                  <td className="py-2.5 px-3 text-right font-mono font-black text-emerald-700 bg-[#C98B4A]/10">
                    {targetCurr} {formatNum(it.final_total_selling_price, targetCurr)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
