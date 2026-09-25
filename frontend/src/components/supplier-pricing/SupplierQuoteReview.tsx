import React, { useState } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  AlertCircle,
  Plus,
  Trash2,
  RotateCcw,
  RefreshCw,
  Building2,
  DollarSign,
  Package,
  Truck,
  Layers,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import type {
  SupplierQuotationData,
  SupplierQuoteItem,
  SupplierValidationSummary,
} from '../../types/supplierPricing';

interface SupplierQuoteReviewProps {
  quotation: SupplierQuotationData;
  validation: SupplierValidationSummary;
  onChange: (updated: SupplierQuotationData) => void;
  onRevalidate: () => void;
  onReset: () => void;
  isValidating: boolean;
  onProceedToPricing?: () => void;
}

export const SupplierQuoteReview: React.FC<SupplierQuoteReviewProps> = ({
  quotation,
  validation,
  onChange,
  onRevalidate,
  onReset,
  isValidating,
  onProceedToPricing,
}) => {
  const [showIssuesList, setShowIssuesList] = useState(false);
  const [showAdditionalMeta, setShowAdditionalMeta] = useState(false);

  // Helper to update a header-level field
  const updateHeaderField = <K extends keyof SupplierQuotationData>(key: K, value: SupplierQuotationData[K]) => {
    const updated = { ...quotation, [key]: value };

    // Auto-update grand total if charges or lines total change
    if (key === 'packing_charges' || key === 'freight_charges' || key === 'other_charges' || key === 'lines_total') {
      const packing = Number(key === 'packing_charges' ? value : quotation.packing_charges) || 0;
      const freight = Number(key === 'freight_charges' ? value : quotation.freight_charges) || 0;
      const other = Number(key === 'other_charges' ? value : quotation.other_charges) || 0;
      const lines = Number(key === 'lines_total' ? value : quotation.lines_total) || 0;
      updated.grand_total = Math.round((lines + packing + freight + other) * 100) / 100;
    }

    onChange(updated);
  };

  // Helper to update a specific line item field
  const updateItemField = <K extends keyof SupplierQuoteItem>(
    index: number,
    field: K,
    value: SupplierQuoteItem[K]
  ) => {
    const newItems = [...quotation.items];
    const item = { ...newItems[index], [field]: value };

    // Recalculate item total if qty or unit price changes
    if (field === 'quantity' || field === 'unit_price' || field === 'discount') {
      const q = Number(field === 'quantity' ? value : item.quantity) || 0;
      const p = Number(field === 'unit_price' ? value : item.unit_price) || 0;
      const d = Number(field === 'discount' ? value : item.discount) || 0;
      const subtotal = q * p;
      const discountAmount = d > 0 && d <= 100 ? subtotal * (d / 100) : d;
      item.total = Math.round(Math.max(0, subtotal - discountAmount) * 100) / 100;
    }

    newItems[index] = item;

    // Recalculate lines total
    const sumLines = newItems.reduce((acc, curr) => acc + (Number(curr.total) || 0), 0);
    const packing = Number(quotation.packing_charges) || 0;
    const freight = Number(quotation.freight_charges) || 0;
    const other = Number(quotation.other_charges) || 0;

    onChange({
      ...quotation,
      items: newItems,
      lines_total: Math.round(sumLines * 100) / 100,
      grand_total: Math.round((sumLines + packing + freight + other) * 100) / 100,
    });
  };

  // Add new blank item
  const handleAddItem = () => {
    const nextLineNum = quotation.items.length > 0 ? Math.max(...quotation.items.map((i) => i.line_number)) + 1 : 1;
    const newItem: SupplierQuoteItem = {
      line_number: nextLineNum,
      part_number: '',
      description: '',
      quantity: 1,
      unit: 'PCS',
      currency: quotation.currency || 'USD',
      unit_price: 0,
      discount: 0,
      packing_charges: 0,
      freight_charges: 0,
      total: 0,
      delivery_lead_time: quotation.delivery_lead_time || '2-3 weeks',
      validation_status: 'warning',
      validation_notes: ['Newly added line'],
    };
    onChange({
      ...quotation,
      items: [...quotation.items, newItem],
    });
  };

  // Remove item
  const handleDeleteItem = (index: number) => {
    const newItems = quotation.items.filter((_, i) => i !== index);
    const sumLines = newItems.reduce((acc, curr) => acc + (Number(curr.total) || 0), 0);
    const packing = Number(quotation.packing_charges) || 0;
    const freight = Number(quotation.freight_charges) || 0;
    const other = Number(quotation.other_charges) || 0;

    onChange({
      ...quotation,
      items: newItems,
      lines_total: Math.round(sumLines * 100) / 100,
      grand_total: Math.round((sumLines + packing + freight + other) * 100) / 100,
    });
  };

  const hasErrors = validation.errors_count > 0;
  const hasWarnings = validation.warnings_count > 0;

  return (
    <div className="space-y-6">
      {/* Validation Status & Summary Bar */}
      <div
        className={`rounded-3xl border p-6 transition-all backdrop-blur-xl ${
          hasErrors
            ? 'border-rose-200 bg-rose-50/70'
            : hasWarnings
            ? 'border-amber-200 bg-amber-50/70'
            : 'border-emerald-200 bg-emerald-50/70'
        }`}
      >
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-start space-x-3.5">
            <div
              className={`w-10 h-10 rounded-2xl flex items-center justify-center shrink-0 shadow-2xs ${
                hasErrors
                  ? 'bg-rose-100 text-rose-700'
                  : hasWarnings
                  ? 'bg-amber-100 text-amber-800'
                  : 'bg-emerald-100 text-emerald-800'
              }`}
            >
              {hasErrors ? (
                <AlertCircle className="w-5 h-5" />
              ) : hasWarnings ? (
                <AlertTriangle className="w-5 h-5" />
              ) : (
                <CheckCircle2 className="w-5 h-5" />
              )}
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h3 className="font-bold text-base text-[#26231F]">
                  {hasErrors
                    ? 'Action Required: Incomplete or Missing Fields'
                    : hasWarnings
                    ? 'Review Needed: Uncertain Fields Detected'
                    : 'Quotation Data Verified'}
                </h3>
                <span
                  className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full ${
                    hasErrors
                      ? 'bg-rose-200/60 text-rose-900'
                      : hasWarnings
                      ? 'bg-amber-200/60 text-amber-900'
                      : 'bg-emerald-200/60 text-emerald-900'
                  }`}
                >
                  {validation.overall_confidence * 100}% Confidence
                </span>
              </div>
              <p className="text-xs text-[#716B61] mt-0.5">
                {hasErrors
                  ? `${validation.errors_count} critical missing fields must be resolved before proceeding.`
                  : hasWarnings
                  ? `${validation.warnings_count} fields flagged with warnings. Please review prices and lead times below.`
                  : 'All 14 required procurement parameters verified with zero missing fields.'}
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-3 self-end md:self-auto">
            <button
              type="button"
              onClick={onRevalidate}
              disabled={isValidating}
              className="flex items-center space-x-2 text-xs font-semibold px-4 py-2.5 rounded-xl bg-white/90 hover:bg-white text-[#26231F] border border-[#786446]/20 shadow-2xs hover:shadow-xs transition duration-150 cursor-pointer disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 text-[#C98B4A] ${isValidating ? 'animate-spin' : ''}`} />
              <span>{isValidating ? 'Validating...' : 'Re-Validate'}</span>
            </button>

            {validation.issues.length > 0 && (
              <button
                type="button"
                onClick={() => setShowIssuesList(!showIssuesList)}
                className="flex items-center space-x-1.5 text-xs font-semibold px-3 py-2.5 rounded-xl bg-white/70 hover:bg-white text-[#716B61] border border-[#786446]/15 transition cursor-pointer"
              >
                <span>{validation.issues.length} Issues</span>
                {showIssuesList ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
              </button>
            )}
          </div>
        </div>

        {/* Expandable Issues / Uncertainties Drawer */}
        {showIssuesList && validation.issues.length > 0 && (
          <div className="mt-4 pt-4 border-t border-black/5 space-y-2 animate-in fade-in duration-150">
            <p className="text-xs font-bold text-[#26231F]">Validation Findings:</p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              {validation.issues.map((issue, idx) => (
                <div
                  key={idx}
                  className={`p-2.5 rounded-xl text-xs flex items-start space-x-2 ${
                    issue.issue_type === 'error'
                      ? 'bg-rose-100/70 text-rose-900 border border-rose-200'
                      : 'bg-amber-100/70 text-amber-900 border border-amber-200'
                  }`}
                >
                  <span className="font-bold shrink-0">{issue.field}:</span>
                  <div className="flex-1">
                    <p>{issue.message}</p>
                    {issue.suggested_fix && (
                      <p className="text-[11px] opacity-80 mt-0.5">Tip: {issue.suggested_fix}</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Header-Level Editable Details (Supports all header fields, charges, and totals) */}
      <div className="rounded-3xl border border-[#786446]/15 bg-white/80 backdrop-blur-xl p-6 shadow-xs space-y-6">
        <div className="flex items-center justify-between border-b border-[#786446]/10 pb-4">
          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded-xl bg-[#26231F] flex items-center justify-center text-[#F5F1E8]">
              <Building2 className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-[#26231F]">Supplier & Quotation Information</h3>
              <p className="text-xs text-[#716B61]">Editable header-level parameters, charges, and totals</p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => setShowAdditionalMeta(!showAdditionalMeta)}
            className="text-xs font-semibold text-[#A66E32] hover:text-[#786446] flex items-center space-x-1 cursor-pointer"
          >
            <span>{showAdditionalMeta ? 'Hide Extra Terms' : 'Show Extra Terms'}</span>
            {showAdditionalMeta ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>
        </div>

        {/* 2-Row Grid for Primary Header Fields */}
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
          {/* Supplier Name */}
          <div className="space-y-1.5">
            <label className="block text-xs font-semibold text-[#26231F]">
              Supplier Name <span className="text-rose-500">*</span>
            </label>
            <input
              type="text"
              value={quotation.supplier_name || ''}
              onChange={(e) => updateHeaderField('supplier_name', e.target.value)}
              placeholder="e.g. DMN INDIA PRIVATE LIMITED"
              className={`w-full px-3.5 py-2 text-xs rounded-xl bg-white border ${
                validation.field_status?.supplier_name === 'missing'
                  ? 'border-rose-400 focus:ring-rose-200'
                  : 'border-[#786446]/20 focus:border-[#C98B4A]'
              } focus:outline-none focus:ring-2`}
            />
          </div>

          {/* Customer Name */}
          <div className="space-y-1.5">
            <label className="block text-xs font-semibold text-[#26231F]">
              Customer
            </label>
            <input
              type="text"
              value={quotation.customer || ''}
              onChange={(e) => updateHeaderField('customer', e.target.value)}
              placeholder="e.g. PT. Flow Force Indonesia"
              className="w-full px-3.5 py-2 text-xs rounded-xl bg-white border border-[#786446]/20 focus:border-[#C98B4A] focus:outline-none focus:ring-2"
            />
          </div>

          {/* Quote Number */}
          <div className="space-y-1.5">
            <label className="block text-xs font-semibold text-[#26231F]">
              Quote Number <span className="text-rose-500">*</span>
            </label>
            <input
              type="text"
              value={quotation.quote_number || ''}
              onChange={(e) => updateHeaderField('quote_number', e.target.value)}
              placeholder="e.g. QU-2026-991"
              className={`w-full px-3.5 py-2 text-xs font-mono rounded-xl bg-white border ${
                validation.field_status?.quote_number === 'missing'
                  ? 'border-rose-400 focus:ring-rose-200'
                  : 'border-[#786446]/20 focus:border-[#C98B4A]'
              } focus:outline-none focus:ring-2`}
            />
          </div>

          {/* Quote Date */}
          <div className="space-y-1.5">
            <label className="block text-xs font-semibold text-[#26231F]">
              Quote Date <span className="text-rose-500">*</span>
            </label>
            <input
              type="text"
              value={quotation.quote_date || ''}
              onChange={(e) => updateHeaderField('quote_date', e.target.value)}
              placeholder="YYYY-MM-DD"
              className="w-full px-3.5 py-2 text-xs rounded-xl bg-white border border-[#786446]/20 focus:border-[#C98B4A] focus:outline-none focus:ring-2"
            />
          </div>

          {/* Delivery / Lead Time (Header) */}
          <div className="space-y-1.5">
            <label className="block text-xs font-semibold text-[#26231F]">Delivery / Lead Time</label>
            <input
              type="text"
              value={quotation.delivery_lead_time || ''}
              onChange={(e) => updateHeaderField('delivery_lead_time', e.target.value)}
              placeholder="e.g. 2-3 Weeks or Ex-Stock"
              className="w-full px-3.5 py-2 text-xs rounded-xl bg-white border border-[#786446]/20 focus:border-[#C98B4A] focus:outline-none focus:ring-2"
            />
          </div>

          {/* Currency */}
          <div className="space-y-1.5">
            <label className="block text-xs font-semibold text-[#26231F]">Currency</label>
            <input
              type="text"
              value={quotation.currency || 'USD'}
              onChange={(e) => updateHeaderField('currency', e.target.value.toUpperCase())}
              placeholder="USD, EUR, GBP, INR"
              className="w-full px-3.5 py-2 text-xs font-mono rounded-xl bg-white border border-[#786446]/20 focus:border-[#C98B4A] focus:outline-none focus:ring-2"
            />
          </div>

          {/* Packing / Packaging Charges */}
          <div className="space-y-1.5">
            <label className="block text-xs font-semibold text-[#26231F] flex items-center space-x-1">
              <Package className="w-3.5 h-3.5 text-[#C98B4A]" />
              <span>Packing Charges</span>
            </label>
            <input
              type="number"
              step="0.01"
              value={quotation.packing_charges ?? 0}
              onChange={(e) => updateHeaderField('packing_charges', parseFloat(e.target.value) || 0)}
              className="w-full px-3.5 py-2 text-xs rounded-xl bg-white border border-[#786446]/20 focus:border-[#C98B4A] focus:outline-none focus:ring-2"
            />
          </div>

          {/* Freight / Other Charges */}
          <div className="space-y-1.5">
            <label className="block text-xs font-semibold text-[#26231F] flex items-center space-x-1">
              <Truck className="w-3.5 h-3.5 text-[#C98B4A]" />
              <span>Freight / Other Charges</span>
            </label>
            <input
              type="number"
              step="0.01"
              value={quotation.freight_charges ?? 0}
              onChange={(e) => updateHeaderField('freight_charges', parseFloat(e.target.value) || 0)}
              className="w-full px-3.5 py-2 text-xs rounded-xl bg-white border border-[#786446]/20 focus:border-[#C98B4A] focus:outline-none focus:ring-2"
            />
          </div>

          {/* Grand Total */}
          <div className="space-y-1.5">
            <label className="block text-xs font-bold text-[#26231F] flex items-center space-x-1">
              <DollarSign className="w-3.5 h-3.5 text-emerald-600" />
              <span>Grand Total ({quotation.currency || 'USD'})</span>
            </label>
            <input
              type="number"
              step="0.01"
              value={quotation.grand_total ?? 0}
              onChange={(e) => updateHeaderField('grand_total', parseFloat(e.target.value) || 0)}
              className="w-full px-3.5 py-2 text-xs font-bold font-mono rounded-xl bg-emerald-50/50 border border-emerald-300 text-emerald-950 focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-200"
            />
          </div>
        </div>

        {/* Collapsible Extra Metadata */}
        {showAdditionalMeta && (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-4 border-t border-[#786446]/10 animate-in fade-in duration-150">
            <div className="space-y-1.5">
              <label className="block text-xs font-semibold text-[#716B61]">Payment Terms</label>
              <input
                type="text"
                value={quotation.payment_terms || ''}
                onChange={(e) => updateHeaderField('payment_terms', e.target.value)}
                placeholder="e.g. Net 30 days"
                className="w-full px-3.5 py-2 text-xs rounded-xl bg-white border border-[#786446]/20 focus:border-[#C98B4A] focus:outline-none"
              />
            </div>
            <div className="space-y-1.5">
              <label className="block text-xs font-semibold text-[#716B61]">Validity Date</label>
              <input
                type="text"
                value={quotation.valid_until || ''}
                onChange={(e) => updateHeaderField('valid_until', e.target.value)}
                placeholder="YYYY-MM-DD"
                className="w-full px-3.5 py-2 text-xs rounded-xl bg-white border border-[#786446]/20 focus:border-[#C98B4A] focus:outline-none"
              />
            </div>
            <div className="space-y-1.5">
              <label className="block text-xs font-semibold text-[#716B61]">Notes / Comments</label>
              <input
                type="text"
                value={quotation.notes || ''}
                onChange={(e) => updateHeaderField('notes', e.target.value)}
                placeholder="Special instructions or vendor notes"
                className="w-full px-3.5 py-2 text-xs rounded-xl bg-white border border-[#786446]/20 focus:border-[#C98B4A] focus:outline-none"
              />
            </div>
          </div>
        )}
      </div>

      {/* Editable Line Items Review Table */}
      <div className="rounded-3xl border border-[#786446]/15 bg-white/80 backdrop-blur-xl p-6 shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#786446]/10 pb-4">
          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded-xl bg-[#C98B4A]/15 flex items-center justify-center text-[#C98B4A]">
              <Layers className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-[#26231F]">
                Quotation Line Items ({quotation.items.length})
              </h3>
              <p className="text-xs text-[#716B61]">
                All fields editable inline with live price & subtotal calculations
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={handleAddItem}
            className="flex items-center space-x-1.5 text-xs font-semibold px-3.5 py-2 rounded-xl bg-[#26231F] text-[#F5F1E8] hover:bg-black transition cursor-pointer self-start sm:self-auto"
          >
            <Plus className="w-3.5 h-3.5 text-[#C98B4A]" />
            <span>Add Line Item</span>
          </button>
        </div>

        {/* Scrollable Table Container */}
        <div className="overflow-x-auto border border-[#786446]/10 rounded-2xl">
          <table className="w-full text-left border-collapse min-w-[1200px]">
            <thead>
              <tr className="bg-[#786446]/5 text-[#26231F] text-[11px] uppercase tracking-wider font-semibold border-b border-[#786446]/10">
                <th className="py-3 px-2 text-center w-10">#</th>
                <th className="py-3 px-2.5 w-36">Part Number</th>
                <th className="py-3 px-2.5 w-56">Description</th>
                <th className="py-3 px-2 w-20">Option</th>
                <th className="py-3 px-2 w-16 text-right">Qty</th>
                <th className="py-3 px-2 w-16">Unit</th>
                <th className="py-3 px-2 w-24 text-right">Unit Price</th>
                <th className="py-3 px-2 w-16 text-right">Disc %</th>
                <th className="py-3 px-2 w-24 text-right">Total</th>
                <th className="py-3 px-2 w-24 text-right">Packaging</th>
                <th className="py-3 px-2.5 w-32">Lead Time</th>
                <th className="py-3 px-2 text-center w-12">Status</th>
                <th className="py-3 px-2 text-center w-10"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#786446]/10 text-xs">
              {quotation.items.map((item, idx) => {
                const isItemError = item.validation_status === 'error';
                const isItemWarning = item.validation_status === 'warning';

                return (
                  <tr
                    key={idx}
                    className={`hover:bg-[#C98B4A]/5 transition-colors ${
                      isItemError ? 'bg-rose-50/40' : isItemWarning ? 'bg-amber-50/40' : ''
                    }`}
                  >
                    {/* Line Number */}
                    <td className="py-2.5 px-2 text-center text-[#716B61] font-mono text-[11px]">
                      {item.line_number}
                    </td>

                    {/* Part Number */}
                    <td className="py-2 px-2">
                      <input
                        type="text"
                        value={item.part_number}
                        onChange={(e) => updateItemField(idx, 'part_number', e.target.value)}
                        placeholder="e.g. RV BL 200 4TS"
                        className={`w-full px-2.5 py-1.5 text-xs font-mono rounded-lg border ${
                          !item.part_number
                            ? 'border-rose-400 bg-rose-50/70'
                            : 'border-[#786446]/20 bg-white'
                        } focus:outline-none focus:border-[#C98B4A]`}
                      />
                    </td>

                    {/* Description */}
                    <td className="py-2 px-2">
                      <input
                        type="text"
                        value={item.description}
                        onChange={(e) => updateItemField(idx, 'description', e.target.value)}
                        placeholder="Item description"
                        className="w-full px-2.5 py-1.5 text-xs rounded-lg border border-[#786446]/20 bg-white focus:outline-none focus:border-[#C98B4A]"
                      />
                    </td>

                    {/* Option */}
                    <td className="py-2 px-2">
                      <input
                        type="text"
                        value={item.option || ''}
                        onChange={(e) => updateItemField(idx, 'option', e.target.value)}
                        placeholder="e.g. 1"
                        className="w-full px-2 py-1.5 text-xs text-center font-mono rounded-lg border border-[#786446]/20 bg-white focus:outline-none focus:border-[#C98B4A]"
                      />
                    </td>

                    {/* Quantity */}
                    <td className="py-2 px-2">
                      <input
                        type="number"
                        step="any"
                        value={item.quantity ?? ''}
                        onChange={(e) =>
                          updateItemField(
                            idx,
                            'quantity',
                            e.target.value === '' ? null : parseFloat(e.target.value)
                          )
                        }
                        placeholder="1.0"
                        className={`w-full px-2 py-1.5 text-xs text-right font-mono rounded-lg border ${
                          item.quantity === null || item.quantity === undefined
                            ? 'border-rose-400 bg-rose-50/70'
                            : 'border-[#786446]/20 bg-white'
                        } focus:outline-none focus:border-[#C98B4A]`}
                      />
                    </td>

                    {/* Unit */}
                    <td className="py-2 px-2">
                      <input
                        type="text"
                        value={item.unit || ''}
                        onChange={(e) => updateItemField(idx, 'unit', e.target.value)}
                        placeholder="NOS"
                        className="w-full px-2 py-1.5 text-xs uppercase font-mono rounded-lg border border-[#786446]/20 bg-white focus:outline-none focus:border-[#C98B4A]"
                      />
                    </td>

                    {/* Unit Price */}
                    <td className="py-2 px-2">
                      <input
                        type="number"
                        step="0.01"
                        value={item.unit_price ?? ''}
                        onChange={(e) =>
                          updateItemField(
                            idx,
                            'unit_price',
                            e.target.value === '' ? null : parseFloat(e.target.value)
                          )
                        }
                        placeholder="0.00"
                        className={`w-full px-2 py-1.5 text-xs text-right font-mono rounded-lg border ${
                          item.unit_price === null || item.unit_price === undefined
                            ? 'border-rose-400 bg-rose-50/70'
                            : 'border-[#786446]/20 bg-white'
                        } focus:outline-none focus:border-[#C98B4A]`}
                      />
                    </td>

                    {/* Discount */}
                    <td className="py-2 px-2">
                      <input
                        type="number"
                        step="any"
                        value={item.discount ?? 0}
                        onChange={(e) =>
                          updateItemField(
                            idx,
                            'discount',
                            e.target.value === '' ? 0 : parseFloat(e.target.value)
                          )
                        }
                        placeholder="0"
                        className="w-full px-2 py-1.5 text-xs text-right font-mono rounded-lg border border-[#786446]/20 bg-white focus:outline-none focus:border-[#C98B4A]"
                      />
                    </td>

                    {/* Total */}
                    <td className="py-2 px-2">
                      <input
                        type="number"
                        step="0.01"
                        value={item.total ?? ''}
                        onChange={(e) =>
                          updateItemField(
                            idx,
                            'total',
                            e.target.value === '' ? null : parseFloat(e.target.value)
                          )
                        }
                        placeholder="0.00"
                        className="w-full px-2 py-1.5 text-xs text-right font-mono font-semibold rounded-lg border border-[#786446]/20 bg-[#F5F1E8]/50 focus:outline-none focus:border-[#C98B4A]"
                      />
                    </td>

                    {/* Packaging Cost */}
                    <td className="py-2 px-2">
                      <input
                        type="number"
                        step="0.01"
                        value={item.packing_charges ?? 0}
                        onChange={(e) =>
                          updateItemField(
                            idx,
                            'packing_charges',
                            e.target.value === '' ? 0 : parseFloat(e.target.value)
                          )
                        }
                        placeholder="0.00"
                        className="w-full px-2 py-1.5 text-xs text-right font-mono rounded-lg border border-[#786446]/20 bg-white focus:outline-none focus:border-[#C98B4A]"
                      />
                    </td>

                    {/* Delivery / Lead Time */}
                    <td className="py-2 px-2">
                      <input
                        type="text"
                        value={item.delivery_lead_time || ''}
                        onChange={(e) => updateItemField(idx, 'delivery_lead_time', e.target.value)}
                        placeholder="e.g. 20 weeks a.r.o"
                        className="w-full px-2 py-1.5 text-xs rounded-lg border border-[#786446]/20 bg-white focus:outline-none focus:border-[#C98B4A]"
                      />
                    </td>

                    {/* Status Badge */}
                    <td className="py-2.5 px-2 text-center">
                      <span
                        className={`inline-block w-2.5 h-2.5 rounded-full ${
                          isItemError
                            ? 'bg-rose-500 ring-2 ring-rose-200'
                            : isItemWarning
                            ? 'bg-amber-500 ring-2 ring-amber-200'
                            : 'bg-emerald-500 ring-2 ring-emerald-200'
                        }`}
                        title={
                          isItemError
                            ? 'Error: Missing part number or price'
                            : isItemWarning
                            ? 'Warning: Please review item'
                            : 'Verified'
                        }
                      />
                    </td>

                    {/* Actions */}
                    <td className="py-2.5 px-2 text-center">
                      <button
                        type="button"
                        onClick={() => handleDeleteItem(idx)}
                        className="text-[#716B61] hover:text-rose-600 transition cursor-pointer p-1 rounded-md hover:bg-rose-50"
                        title="Delete row"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Footer Summary / Navigation Actions */}
        <div className="pt-4 flex flex-col sm:flex-row items-center justify-between gap-4 border-t border-[#786446]/10">
          <button
            type="button"
            onClick={onReset}
            className="flex items-center space-x-2 text-xs font-semibold text-[#716B61] hover:text-[#26231F] px-4 py-2.5 rounded-xl bg-white border border-[#786446]/15 transition cursor-pointer"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Upload Another PDF</span>
          </button>

          <div className="flex flex-wrap items-center gap-4 text-xs font-semibold">
            <span className="text-[#716B61]">
              Lines Total: <strong className="text-[#26231F]">{quotation.currency || 'USD'} {quotation.lines_total?.toFixed(2) || '0.00'}</strong>
            </span>
            <span className="text-[#716B61]">
              Grand Total: <strong className="text-emerald-700 text-sm font-mono">{quotation.currency || 'USD'} {quotation.grand_total?.toFixed(2) || '0.00'}</strong>
            </span>

            {onProceedToPricing && (
              <button
                type="button"
                onClick={onProceedToPricing}
                className="flex items-center space-x-2 text-xs font-bold text-white px-5 py-2.5 rounded-xl bg-[#26231F] hover:bg-[#3D3730] transition cursor-pointer shadow-xs"
              >
                <span>Calculate Pricing (Stage 2) →</span>
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
