import React, { useState, useEffect } from 'react';
import {
  RotateCcw,
  ArrowLeft,
  ChevronDown,
  ChevronUp,
  ShieldCheck,
  Copy,
  Check,
  Info,
  ArrowRight,
} from 'lucide-react';
import type {
  SupplierQuotationData,
  PricingConfigParameters,
  CalculatedLinePrice,
  PricingSummary,
  SupplierPricingCalculationResponse,
} from '../../types/supplierPricing';
import { supplierPricingApi } from '../../services/supplierPricingApi';

interface PricingCalculationStepProps {
  quotation: SupplierQuotationData;
  onBackToReview: () => void;
  onProceedToApproval?: (calculatedItems: CalculatedLinePrice[], summary: PricingSummary) => void;
}

const DEFAULT_FX_TABLE: Record<string, Record<string, number>> = {
  EUR: {
    EUR: 1.0,
    IDR: 17500.0,
    USD: 1.08,
    SGD: 1.45,
    GBP: 0.85,
    AUD: 1.65,
  },
  USD: {
    USD: 1.0,
    IDR: 16200.0,
    EUR: 0.925,
    SGD: 1.34,
    GBP: 0.79,
    AUD: 1.53,
  },
  IDR: {
    IDR: 1.0,
    EUR: 1 / 17500.0,
    USD: 1 / 16200.0,
  },
};

const getDefaultFxRate = (fromCurr: string, toCurr: string): number => {
  const from = (fromCurr || 'EUR').toUpperCase();
  const to = (toCurr || 'EUR').toUpperCase();
  if (from === to) return 1.0;
  return DEFAULT_FX_TABLE[from]?.[to] ?? (to === 'IDR' ? 17500.0 : 1.0);
};

const formatNum = (val: number | null | undefined, curr?: string) => {
  if (val === null || val === undefined || isNaN(val)) return '0.00';
  const isZeroDec = curr === 'IDR';
  return val.toLocaleString(undefined, {
    minimumFractionDigits: isZeroDec ? 0 : 2,
    maximumFractionDigits: 2,
  });
};

export const PricingCalculationStep: React.FC<PricingCalculationStepProps> = ({
  quotation,
  onBackToReview,
  onProceedToApproval,
}) => {
  const supCurr = (quotation.currency || 'EUR').toUpperCase();
  const initialTarget = supCurr;
  const initialFx = getDefaultFxRate(supCurr, initialTarget);

  // Global pricing configuration parameters
  const [config, setConfig] = useState<PricingConfigParameters>({
    exchange_rate: initialFx,
    target_currency: initialTarget,
    default_margin_percent: 10.0,
    margin_method: 'margin_on_selling',
    freight_total: Number(quotation.freight_charges) || 0.0,
    customs_duty_percent: 0.0,
    local_handling_charge: 0.0,
  });

  // Per-line overrides (e.g. line_number -> { margin_percent, freight_charge_unit, ... })
  const [lineOverrides, setLineOverrides] = useState<Record<string, Record<string, any>>>({});

  // Calculation output state
  const [calculatedItems, setCalculatedItems] = useState<CalculatedLinePrice[]>([]);
  const [summary, setSummary] = useState<PricingSummary | null>(null);
  const [calculationNotes, setCalculationNotes] = useState<string[]>([]);
  const [isCalculating, setIsCalculating] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // UI state
  const [expandedRows, setExpandedRows] = useState<Record<number, boolean>>({});
  const [copiedSummary, setCopiedSummary] = useState(false);

  // Client-side deterministic calculation trigger
  const runCalculation = async (
    currentConfig: PricingConfigParameters,
    currentOverrides: Record<string, Record<string, any>>
  ) => {
    setIsCalculating(true);
    setErrorMsg(null);
    try {
      const res: SupplierPricingCalculationResponse = await supplierPricingApi.calculatePricing({
        quotation,
        config: currentConfig,
        line_overrides: currentOverrides,
      });

      if (res.success) {
        setCalculatedItems(res.items);
        setSummary(res.summary);
        setCalculationNotes(res.calculation_notes);
      }
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'Pricing calculation failed. Please check parameters.');
    } finally {
      setIsCalculating(false);
    }
  };

  // Run on mount or when quotation changes
  useEffect(() => {
    runCalculation(config, lineOverrides);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Handler: Target currency change automatically updates default FX rate and recalculates
  const handleTargetCurrencyChange = (newTarget: string) => {
    const newFx = getDefaultFxRate(supCurr, newTarget);
    const updated: PricingConfigParameters = {
      ...config,
      target_currency: newTarget,
      exchange_rate: newFx,
    };
    setConfig(updated);
    runCalculation(updated, lineOverrides);
  };

  // Handler: User freely edits the FX Rate and immediately recalculates
  const handleFxRateChange = (newFx: number) => {
    const updated: PricingConfigParameters = {
      ...config,
      exchange_rate: newFx,
    };
    setConfig(updated);
    runCalculation(updated, lineOverrides);
  };

  const handleConfigChange = <K extends keyof PricingConfigParameters>(
    key: K,
    value: PricingConfigParameters[K]
  ) => {
    const updated = { ...config, [key]: value };
    setConfig(updated);
    runCalculation(updated, lineOverrides);
  };

  const handleLineOverrideChange = (lineNum: number, field: string, value: any) => {
    const lineKey = String(lineNum);
    const updated = {
      ...lineOverrides,
      [lineKey]: {
        ...(lineOverrides[lineKey] || {}),
        [field]: value,
      },
    };
    setLineOverrides(updated);
    runCalculation(config, updated);
  };

  const resetAllOverrides = () => {
    setLineOverrides({});
    runCalculation(config, {});
  };

  const toggleRowExpand = (lineNum: number) => {
    setExpandedRows((prev) => ({
      ...prev,
      [lineNum]: !prev[lineNum],
    }));
  };

  const copySummaryToClipboard = () => {
    if (!summary) return;
    const text = `QuotexAI Pricing Summary (${quotation.quote_number || 'Supplier Quote'})
------------------------------------------------
Supplier: ${quotation.supplier_name || 'N/A'}
Currency: ${summary.supplier_currency} -> ${summary.target_currency} (FX Rate: ${config.exchange_rate.toLocaleString()})
Pricing Engine: Deterministic Excel Formula (${config.margin_method === 'margin_on_selling' ? 'Margin on Selling' : 'Markup on Cost'})
Total Net Supplier Cost: ${summary.target_currency} ${formatNum(summary.total_supplier_net_converted || (summary.total_supplier_net * config.exchange_rate), summary.target_currency)} (${summary.supplier_currency} ${formatNum(summary.total_supplier_net, summary.supplier_currency)})
Total Landed Cost:       ${summary.target_currency} ${formatNum(summary.total_landed_cost, summary.target_currency)}
Total Selling Price:     ${summary.target_currency} ${formatNum(summary.total_selling_price, summary.target_currency)}
Total Gross Profit:      ${summary.target_currency} ${formatNum(summary.total_gross_profit, summary.target_currency)} (${summary.overall_margin_percent}%)
------------------------------------------------`;
    navigator.clipboard.writeText(text);
    setCopiedSummary(true);
    setTimeout(() => setCopiedSummary(false), 2500);
  };

  const targetCurr = config.target_currency || 'EUR';

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Top Banner & Deterministic Engine Callout */}
      <div className="rounded-3xl border border-[#786446]/15 bg-white/75 backdrop-blur-xl p-6 shadow-xs space-y-4">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-[#786446]/10 pb-4">
          <div className="flex items-start space-x-3">
            <button
              onClick={onBackToReview}
              className="p-2 rounded-xl bg-white border border-[#786446]/20 text-[#716B61] hover:text-[#26231F] hover:bg-[#786446]/5 transition cursor-pointer shrink-0 mt-0.5"
              title="Return to Stage 1 Review"
            >
              <ArrowLeft className="w-4 h-4" />
            </button>
            <div>
              <div className="flex items-center space-x-2 flex-wrap gap-y-1">
                <span className="text-xs font-semibold uppercase tracking-wider text-[#A66E32]">
                  Stage 2 • Pricing Engine
                </span>
                <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-800 border border-emerald-500/25 flex items-center space-x-1">
                  <ShieldCheck className="w-3 h-3 text-emerald-600" />
                  <span>Deterministic Excel Formula • Zero AI Price Generation</span>
                </span>
                <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded-full bg-[#786446]/10 text-[#716B61]">
                  Ref: {quotation.quote_number || 'Quotation'}
                </span>
              </div>
              <h2 className="text-xl font-bold text-[#26231F] mt-1">
                Customer Selling Price & Landed Cost Breakdown
              </h2>
              <p className="text-xs text-[#716B61] mt-0.5">
                Calculates unit prices using the exact Excel workbook formula: Net Supplier Price + Landed Costs + Configurable Margin.
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2.5 self-start lg:self-center">
            <button
              onClick={copySummaryToClipboard}
              className="flex items-center space-x-1.5 text-xs font-semibold px-3 py-2 rounded-xl bg-white border border-[#786446]/20 text-[#716B61] hover:text-[#26231F] transition cursor-pointer shadow-2xs"
            >
              {copiedSummary ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copiedSummary ? 'Copied Summary' : 'Copy Summary'}</span>
            </button>

            <button
              onClick={() => runCalculation(config, lineOverrides)}
              disabled={isCalculating}
              className="flex items-center space-x-1.5 text-xs font-semibold px-4 py-2 rounded-xl bg-[#26231F] text-white hover:bg-[#3D3730] transition cursor-pointer shadow-xs disabled:opacity-50"
            >
              <RotateCcw className={`w-3.5 h-3.5 ${isCalculating ? 'animate-spin' : ''}`} />
              <span>{isCalculating ? 'Calculating...' : 'Recalculate'}</span>
            </button>
          </div>
        </div>

        {/* Error Display */}
        {errorMsg && (
          <div className="p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-xs text-rose-900 flex items-center justify-between">
            <span>{errorMsg}</span>
            <button onClick={() => setErrorMsg(null)} className="font-bold text-rose-700">✕</button>
          </div>
        )}

        {/* Global Config Controls Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-7 gap-3 pt-2">
          {/* Target Currency with auto FX update */}
          <div className="space-y-1">
            <label className="text-[11px] font-semibold text-[#716B61] flex items-center space-x-1">
              <span>Target Currency</span>
            </label>
            <select
              value={config.target_currency}
              onChange={(e) => handleTargetCurrencyChange(e.target.value)}
              className="w-full text-xs font-bold bg-white border border-[#786446]/20 rounded-xl px-2.5 py-1.5 text-[#26231F] focus:outline-none focus:border-[#C98B4A]"
            >
              <option value="EUR">EUR (€)</option>
              <option value="IDR">IDR (Rp)</option>
              <option value="USD">USD ($)</option>
              <option value="SGD">SGD (S$)</option>
              <option value="GBP">GBP (£)</option>
              <option value="AUD">AUD (A$)</option>
            </select>
          </div>

          {/* Exchange Rate with live instant recalculation */}
          <div className="space-y-1">
            <label className="text-[11px] font-semibold text-[#716B61] flex items-center space-x-1">
              <span>FX Rate ({supCurr}→{targetCurr})</span>
            </label>
            <input
              type="number"
              step="any"
              min="0.000001"
              value={config.exchange_rate}
              onChange={(e) => handleFxRateChange(parseFloat(e.target.value) || 0)}
              className="w-full text-xs font-mono font-bold bg-white border border-[#786446]/20 rounded-xl px-2.5 py-1.5 text-[#26231F] focus:outline-none focus:border-[#C98B4A]"
              title="Change FX Rate to immediately recalculate all pricing steps"
            />
          </div>

          {/* Default Margin % */}
          <div className="space-y-1">
            <label className="text-[11px] font-semibold text-[#716B61] flex items-center space-x-1">
              <span>Default Margin %</span>
            </label>
            <div className="relative">
              <input
                type="number"
                step="0.5"
                min="0"
                max="99"
                value={config.default_margin_percent}
                onChange={(e) => handleConfigChange('default_margin_percent', Number(e.target.value) || 0)}
                className="w-full text-xs font-mono font-bold bg-white border border-[#786446]/20 rounded-xl pl-2.5 pr-6 py-1.5 text-[#26231F] focus:outline-none focus:border-[#C98B4A]"
              />
              <span className="absolute right-2.5 top-1.5 text-xs text-[#716B61] font-bold pointer-events-none">%</span>
            </div>
          </div>

          {/* Margin Method */}
          <div className="space-y-1">
            <label className="text-[11px] font-semibold text-[#716B61] flex items-center space-x-1">
              <span>Margin Formula</span>
            </label>
            <select
              value={config.margin_method}
              onChange={(e) => handleConfigChange('margin_method', e.target.value as any)}
              className="w-full text-xs font-medium bg-white border border-[#786446]/20 rounded-xl px-2 py-1.5 text-[#26231F] focus:outline-none focus:border-[#C98B4A]"
            >
              <option value="margin_on_selling">Selling Margin: Landed / (1 - M)</option>
              <option value="markup_on_cost">Cost Markup: Landed * (1 + M)</option>
            </select>
          </div>

          {/* Freight Total */}
          <div className="space-y-1">
            <label className="text-[11px] font-semibold text-[#716B61] flex items-center space-x-1">
              <span>Freight ({supCurr})</span>
            </label>
            <input
              type="number"
              step="1"
              min="0"
              value={config.freight_total}
              onChange={(e) => handleConfigChange('freight_total', Number(e.target.value) || 0)}
              className="w-full text-xs font-mono font-medium bg-white border border-[#786446]/20 rounded-xl px-2.5 py-1.5 text-[#26231F] focus:outline-none focus:border-[#C98B4A]"
            />
          </div>

          {/* Customs Duty % */}
          <div className="space-y-1">
            <label className="text-[11px] font-semibold text-[#716B61] flex items-center space-x-1">
              <span>Customs Tariff %</span>
            </label>
            <div className="relative">
              <input
                type="number"
                step="0.5"
                min="0"
                value={config.customs_duty_percent}
                onChange={(e) => handleConfigChange('customs_duty_percent', Number(e.target.value) || 0)}
                className="w-full text-xs font-mono font-medium bg-white border border-[#786446]/20 rounded-xl pl-2.5 pr-6 py-1.5 text-[#26231F] focus:outline-none focus:border-[#C98B4A]"
              />
              <span className="absolute right-2.5 top-1.5 text-xs text-[#716B61] font-bold pointer-events-none">%</span>
            </div>
          </div>

          {/* Local Handling */}
          <div className="space-y-1">
            <label className="text-[11px] font-semibold text-[#716B61] flex items-center space-x-1">
              <span>Local Handling ({targetCurr})</span>
            </label>
            <input
              type="number"
              step="1000"
              min="0"
              value={config.local_handling_charge}
              onChange={(e) => handleConfigChange('local_handling_charge', Number(e.target.value) || 0)}
              className="w-full text-xs font-mono font-medium bg-white border border-[#786446]/20 rounded-xl px-2.5 py-1.5 text-[#26231F] focus:outline-none focus:border-[#C98B4A]"
            />
          </div>
        </div>

        {/* Quick Margin Preset Pills */}
        <div className="flex items-center space-x-2 pt-1 border-t border-[#786446]/10 flex-wrap gap-y-1 text-xs">
          <span className="text-[11px] font-semibold text-[#716B61]">Presets:</span>
          <button
            onClick={() => handleConfigChange('default_margin_percent', 10.0)}
            className={`px-2.5 py-1 rounded-lg border text-xs font-semibold cursor-pointer transition ${
              config.default_margin_percent === 10.0
                ? 'bg-[#C98B4A] text-white border-[#C98B4A]'
                : 'bg-white text-[#716B61] border-[#786446]/20 hover:border-[#C98B4A]'
            }`}
          >
            Excel Default (10%)
          </button>
          <button
            onClick={() => handleConfigChange('default_margin_percent', 15.0)}
            className={`px-2.5 py-1 rounded-lg border text-xs font-semibold cursor-pointer transition ${
              config.default_margin_percent === 15.0
                ? 'bg-[#C98B4A] text-white border-[#C98B4A]'
                : 'bg-white text-[#716B61] border-[#786446]/20 hover:border-[#C98B4A]'
            }`}
          >
            15% Target
          </button>
          <button
            onClick={() => handleConfigChange('default_margin_percent', 20.0)}
            className={`px-2.5 py-1 rounded-lg border text-xs font-semibold cursor-pointer transition ${
              config.default_margin_percent === 20.0
                ? 'bg-[#C98B4A] text-white border-[#C98B4A]'
                : 'bg-white text-[#716B61] border-[#786446]/20 hover:border-[#C98B4A]'
            }`}
          >
            20% Target
          </button>
          <button
            onClick={() => handleConfigChange('default_margin_percent', 25.0)}
            className={`px-2.5 py-1 rounded-lg border text-xs font-semibold cursor-pointer transition ${
              config.default_margin_percent === 25.0
                ? 'bg-[#C98B4A] text-white border-[#C98B4A]'
                : 'bg-white text-[#716B61] border-[#786446]/20 hover:border-[#C98B4A]'
            }`}
          >
            25% Target
          </button>

          {Object.keys(lineOverrides).length > 0 && (
            <button
              onClick={resetAllOverrides}
              className="ml-auto text-[11px] font-semibold text-rose-600 hover:text-rose-800 underline cursor-pointer"
            >
              Reset {Object.keys(lineOverrides).length} line override(s)
            </button>
          )}
        </div>
      </div>

      {/* KPI / Metric Summary Cards */}
      {summary && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          {/* Card 1: Net Supplier Total with Converted and Original currency */}
          <div className="rounded-2xl bg-white/70 border border-[#786446]/15 p-4 shadow-2xs">
            <span className="text-[11px] font-semibold text-[#716B61] uppercase tracking-wider">
              1. Net Supplier Total
            </span>
            <div className="mt-1 flex items-baseline space-x-1.5">
              <span className="text-xl font-bold font-mono text-[#26231F]">
                {targetCurr} {formatNum(summary.total_supplier_net_converted || (summary.total_supplier_net * config.exchange_rate), targetCurr)}
              </span>
            </div>
            <p className="text-[11px] text-[#716B61] mt-0.5">
              {supCurr} {formatNum(summary.total_supplier_net, supCurr)} @ FX {config.exchange_rate.toLocaleString()}
            </p>
          </div>

          {/* Card 2: Total Landed Cost */}
          <div className="rounded-2xl bg-white/70 border border-[#786446]/15 p-4 shadow-2xs">
            <span className="text-[11px] font-semibold text-[#716B61] uppercase tracking-wider">
              2. Total Landed Cost
            </span>
            <div className="mt-1 flex items-baseline space-x-1.5">
              <span className="text-xl font-bold font-mono text-[#26231F]">
                {targetCurr} {formatNum(summary.total_landed_cost, targetCurr)}
              </span>
            </div>
            <p className="text-[11px] text-[#716B61] mt-0.5">
              Incl. packing, freight & customs
            </p>
          </div>

          {/* Card 3: Final Selling Price */}
          <div className="rounded-2xl bg-white/70 border border-[#C98B4A]/30 p-4 shadow-2xs bg-gradient-to-br from-white to-[#C98B4A]/5">
            <span className="text-[11px] font-semibold text-[#A66E32] uppercase tracking-wider">
              3. Final Selling Price
            </span>
            <div className="mt-1 flex items-baseline space-x-1.5">
              <span className="text-2xl font-black font-mono text-emerald-700">
                {targetCurr} {formatNum(summary.total_selling_price, targetCurr)}
              </span>
            </div>
            <p className="text-[11px] text-[#716B61] mt-0.5">
              Total customer quote value
            </p>
          </div>

          {/* Card 4: Gross Profit */}
          <div className="rounded-2xl bg-white/70 border border-[#786446]/15 p-4 shadow-2xs">
            <span className="text-[11px] font-semibold text-[#716B61] uppercase tracking-wider">
              4. Gross Profit
            </span>
            <div className="mt-1 flex items-baseline space-x-1.5">
              <span className="text-xl font-bold font-mono text-[#26231F]">
                {targetCurr} {formatNum(summary.total_gross_profit, targetCurr)}
              </span>
            </div>
            <p className="text-[11px] text-emerald-700 font-semibold mt-0.5">
              Selling price - Landed cost
            </p>
          </div>

          {/* Card 5: Effective Margin % */}
          <div className="rounded-2xl bg-white/70 border border-[#786446]/15 p-4 shadow-2xs">
            <span className="text-[11px] font-semibold text-[#716B61] uppercase tracking-wider">
              5. Effective Margin
            </span>
            <div className="mt-1 flex items-baseline space-x-1.5">
              <span className="text-xl font-black font-mono text-[#A66E32]">
                {summary.overall_margin_percent.toFixed(1)}%
              </span>
            </div>
            <p className="text-[11px] text-[#716B61] mt-0.5">
              {config.margin_method === 'margin_on_selling' ? 'Gross margin on selling' : 'Markup on cost'}
            </p>
          </div>
        </div>
      )}

      {/* Engine Audit Notes */}
      {calculationNotes.length > 0 && (
        <div className="p-3.5 rounded-2xl bg-[#786446]/5 border border-[#786446]/15 flex items-start space-x-2.5 text-xs text-[#716B61]">
          <Info className="w-4 h-4 text-[#C98B4A] shrink-0 mt-0.5" />
          <div className="flex-1 flex flex-wrap gap-x-4 gap-y-1">
            {calculationNotes.map((note, idx) => (
              <span key={idx} className="flex items-center space-x-1 font-mono text-[11px]">
                <span>•</span>
                <span>{note}</span>
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Main Step-by-Step Calculation Table */}
      <div className="rounded-3xl border border-[#786446]/15 bg-white/75 backdrop-blur-xl p-6 shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[#786446]/10 pb-4">
          <div>
            <h3 className="text-base font-bold text-[#26231F] flex items-center space-x-2">
              <span>Item-Level Calculation Breakdown</span>
              <span className="text-xs font-normal text-[#716B61]">({calculatedItems.length} line items)</span>
            </h3>
            <p className="text-xs text-[#716B61] mt-0.5">
              Every step is calculated deterministically. Click any row to expand the step-by-step formula trace.
            </p>
          </div>
          <div className="flex items-center space-x-2 text-xs text-[#716B61]">
            <span className="inline-block w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
            <span>All values live & editable</span>
          </div>
        </div>

        {/* Responsive Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-[#786446]/15 bg-[#786446]/5 text-[#716B61]">
                <th className="py-3 px-3 font-bold w-12 text-center">#</th>
                <th className="py-3 px-3 font-bold min-w-[200px]">Part / Description</th>
                <th className="py-3 px-3 font-bold w-16 text-center">Qty</th>
                <th className="py-3 px-3 font-bold min-w-[100px] text-right">Supplier Unit</th>
                <th className="py-3 px-3 font-bold min-w-[80px] text-center">Disc %</th>
                <th className="py-3 px-3 font-bold min-w-[100px] text-right">Net Unit</th>
                <th className="py-3 px-3 font-bold min-w-[120px] text-right font-bold text-[#26231F]">Conv Unit ({targetCurr})</th>
                <th className="py-3 px-3 font-bold min-w-[90px] text-right">Pkg Unit</th>
                <th className="py-3 px-3 font-bold min-w-[110px] text-right">Landed Unit</th>
                <th className="py-3 px-3 font-bold min-w-[90px] text-center">Margin %</th>
                <th className="py-3 px-3 font-bold min-w-[130px] text-right bg-[#C98B4A]/10 text-[#26231F]">
                  Final Unit ({targetCurr})
                </th>
                <th className="py-3 px-3 font-bold min-w-[140px] text-right bg-[#C98B4A]/15 text-[#26231F]">
                  Final Total ({targetCurr})
                </th>
                <th className="py-3 px-2 font-bold w-10 text-center">Trace</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#786446]/10">
              {calculatedItems.map((item) => {
                const isExpanded = !!expandedRows[item.line_number];
                const override = lineOverrides[String(item.line_number)] || {};
                const hasMarginOverride = 'margin_percent' in override;

                return (
                  <React.Fragment key={item.line_number}>
                    <tr className="hover:bg-[#786446]/5 transition group">
                      {/* Line Number */}
                      <td className="py-3 px-3 text-center font-bold text-[#716B61]">
                        {item.line_number}
                      </td>

                      {/* Part Number & Description */}
                      <td className="py-3 px-3">
                        <div className="font-mono font-bold text-[#26231F] text-xs">
                          {item.part_number || 'N/A'}
                        </div>
                        <div className="text-[11px] text-[#716B61] line-clamp-1 mt-0.5">
                          {item.description}
                        </div>
                      </td>

                      {/* Quantity */}
                      <td className="py-3 px-3 text-center font-mono font-semibold text-[#26231F]">
                        {item.quantity} {item.unit}
                      </td>

                      {/* Supplier Unit Price */}
                      <td className="py-3 px-3 text-right font-mono text-[#716B61]">
                        {item.supplier_currency} {formatNum(item.supplier_unit_price, item.supplier_currency)}
                      </td>

                      {/* Discount % */}
                      <td className="py-3 px-3 text-center">
                        <span className="font-mono text-xs px-1.5 py-0.5 rounded-md bg-[#786446]/10 text-[#716B61] font-semibold">
                          {item.discount_percent}%
                        </span>
                      </td>

                      {/* Net Supplier Unit Price */}
                      <td className="py-3 px-3 text-right font-mono font-medium text-[#26231F]">
                        {item.supplier_currency} {formatNum(item.net_supplier_unit_price, item.supplier_currency)}
                      </td>

                      {/* Converted Unit Price */}
                      <td className="py-3 px-3 text-right font-mono font-bold text-[#26231F]">
                        {targetCurr} {formatNum(item.converted_unit_price, targetCurr)}
                      </td>

                      {/* Packing Unit */}
                      <td className="py-3 px-3 text-right font-mono text-[#716B61]">
                        +{formatNum(item.packing_charge_unit, targetCurr)}
                      </td>

                      {/* Landed Cost Unit */}
                      <td className="py-3 px-3 text-right font-mono font-bold text-[#26231F]">
                        {targetCurr} {formatNum(item.landed_cost_unit, targetCurr)}
                      </td>

                      {/* Margin % (Editable inline per line) */}
                      <td className="py-3 px-3 text-center">
                        <div className="inline-flex items-center space-x-1">
                          <input
                            type="number"
                            step="1"
                            min="0"
                            max="99"
                            value={item.margin_percent}
                            onChange={(e) =>
                              handleLineOverrideChange(
                                item.line_number,
                                'margin_percent',
                                Number(e.target.value) || 0
                              )
                            }
                            className={`w-14 text-center text-xs font-mono font-bold px-1 py-1 rounded-lg border transition ${
                              hasMarginOverride
                                ? 'bg-amber-50 border-amber-400 text-amber-900 ring-1 ring-amber-400'
                                : 'bg-white border-[#786446]/20 text-[#26231F] focus:border-[#C98B4A]'
                            }`}
                            title="Override margin for this item"
                          />
                          <span className="text-[11px] text-[#716B61] font-bold">%</span>
                        </div>
                      </td>

                      {/* Final Selling Price Unit */}
                      <td className="py-3 px-3 text-right font-mono font-bold text-emerald-800 bg-[#C98B4A]/5">
                        {targetCurr} {formatNum(item.final_unit_selling_price, targetCurr)}
                      </td>

                      {/* Final Selling Price Total */}
                      <td className="py-3 px-3 text-right font-mono font-black text-emerald-700 bg-[#C98B4A]/10">
                        {targetCurr} {formatNum(item.final_total_selling_price, targetCurr)}
                      </td>

                      {/* Expand / Collapse Trace */}
                      <td className="py-3 px-2 text-center">
                        <button
                          onClick={() => toggleRowExpand(item.line_number)}
                          className="p-1 rounded-md text-[#716B61] hover:text-[#26231F] hover:bg-[#786446]/10 transition cursor-pointer"
                          title="Show step-by-step formula breakdown"
                        >
                          {isExpanded ? (
                            <ChevronUp className="w-4 h-4 text-[#C98B4A]" />
                          ) : (
                            <ChevronDown className="w-4 h-4" />
                          )}
                        </button>
                      </td>
                    </tr>

                    {/* Step-by-Step Formula Breakdown Drawer */}
                    {isExpanded && (
                      <tr className="bg-[#FAF8F5] border-b border-[#786446]/15">
                        <td colSpan={13} className="p-4">
                          <div className="rounded-2xl bg-white border border-[#786446]/15 p-4 shadow-2xs space-y-3">
                            <div className="flex items-center justify-between border-b border-[#786446]/10 pb-2">
                              <div className="flex items-center space-x-2">
                                <span className="text-xs font-bold text-[#26231F]">
                                  Deterministic Step-by-Step Formula Trace: Line {item.line_number}
                                </span>
                                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-[#C98B4A]/10 text-[#A66E32] font-semibold">
                                  {item.part_number}
                                </span>
                              </div>
                              <span className="text-[11px] font-mono text-[#716B61]">
                                Formula: {item.margin_method === 'margin_on_selling' ? 'Landed / (1 - Margin%)' : 'Landed * (1 + Markup%)'}
                              </span>
                            </div>

                            {/* Sequential Steps List */}
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2.5">
                              {item.step_formula_breakdown.map((stepStr, sIdx) => (
                                <div
                                  key={sIdx}
                                  className="p-2.5 rounded-xl bg-[#786446]/5 border border-[#786446]/10 text-xs font-mono space-y-0.5"
                                >
                                  <div className="text-[10px] font-bold text-[#A66E32] uppercase tracking-wider">
                                    Step {sIdx + 1}
                                  </div>
                                  <div className="text-[#26231F] font-medium leading-snug">
                                    {stepStr}
                                  </div>
                                </div>
                              ))}
                            </div>

                            {/* Additional Metadata */}
                            <div className="pt-2 flex items-center justify-between text-xs text-[#716B61] border-t border-[#786446]/10 flex-wrap gap-2">
                              <span>
                                Supplier Currency: <strong>{item.supplier_currency}</strong> | Target Currency: <strong>{item.target_currency}</strong> | FX Rate: <strong>{item.exchange_rate.toLocaleString()}</strong>
                              </span>
                              <span>
                                Margin Contribution: <strong className="text-emerald-700">+{targetCurr} {formatNum(item.margin_amount_unit, targetCurr)} / unit</strong> (Total Profit: {targetCurr} {formatNum(item.profit_total, targetCurr)})
                              </span>
                              {item.lead_time && (
                                <span>
                                  Lead Time: <strong>{item.lead_time}</strong>
                                </span>
                              )}
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Footer Actions & Stage 3 Navigation */}
        <div className="pt-4 flex flex-col sm:flex-row items-center justify-between gap-4 border-t border-[#786446]/10">
          <button
            onClick={onBackToReview}
            className="flex items-center space-x-2 text-xs font-semibold text-[#716B61] hover:text-[#26231F] px-4 py-2.5 rounded-xl bg-white border border-[#786446]/15 transition cursor-pointer shadow-2xs"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Back to Stage 1 Review</span>
          </button>

          <div className="flex items-center space-x-4">
            <div className="text-right hidden sm:block">
              <div className="text-xs font-semibold text-[#716B61]">Final Customer Selling Price</div>
              <div className="text-base font-black font-mono text-emerald-700">
                {targetCurr} {formatNum(summary?.total_selling_price, targetCurr)}
              </div>
            </div>

            {/* Stage 3 Active Button */}
            {onProceedToApproval && (
              <button
                onClick={() => summary && onProceedToApproval(calculatedItems, summary)}
                className="flex items-center space-x-2 text-xs font-bold px-5 py-2.5 rounded-xl bg-[#26231F] text-white hover:bg-[#3D3730] transition cursor-pointer shadow-xs"
              >
                <span>Proceed to Procurement Approval (Stage 3)</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
