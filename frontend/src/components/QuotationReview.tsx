import React, { useState } from 'react';
import {
  CheckCircle2,
  AlertTriangle,
  AlertCircle,
  Info,
  XCircle,
  Plus,
  Trash2,
  FileSpreadsheet,
  ArrowRight,
  Tag,
} from 'lucide-react';
import type { QuotationData, QuoteItem, ValidationSummary } from '../types/quotation';
import { EquipmentGrouping } from './EquipmentGrouping';
import { PricingConfig } from './PricingConfig';

interface QuotationReviewProps {
  quotation: QuotationData;
  validation: ValidationSummary;
  onChange: (updated: QuotationData) => void;
  onGenerate: () => void;
  pricingMode: 'quoted_price' | 'supplier_discount' | 'add_margin';
  marginPercent: number;
  supplierDiscountPercent: number;
  onPricingModeChange: (mode: 'quoted_price' | 'supplier_discount' | 'add_margin') => void;
  onMarginChange: (m: number) => void;
  onSupplierDiscountChange: (d: number) => void;
  isGenerating: boolean;
}

export const QuotationReview: React.FC<QuotationReviewProps> = ({
  quotation,
  validation,
  onChange,
  onGenerate,
  pricingMode,
  marginPercent,
  supplierDiscountPercent,
  onPricingModeChange,
  onMarginChange,
  onSupplierDiscountChange,
  isGenerating,
}) => {
  const [selectedGroup, setSelectedGroup] = useState<string | null>(null);

  const handleHeaderChange = (field: keyof QuotationData, value: any) => {
    onChange({
      ...quotation,
      [field]: value,
    });
  };

  const handleItemChange = (index: number, field: keyof QuoteItem, value: any) => {
    const updatedItems = [...quotation.items];
    const item = { ...updatedItems[index], [field]: value };

    if (field === 'quantity' || field === 'unit_price' || field === 'discount_percent') {
      const q = field === 'quantity' ? (value === '' ? null : parseFloat(value)) : item.quantity;
      const p = field === 'unit_price' ? (value === '' ? null : parseFloat(value)) : item.unit_price;
      const d = field === 'discount_percent' ? (value === '' ? null : parseFloat(value)) : item.discount_percent || 0;
      
      if (q !== null && q !== undefined && p !== null && p !== undefined) {
        item.total_price = Math.round(q * p * (1 - (d || 0) / 100) * 100) / 100;
      }
    }

    updatedItems[index] = item;

    const linesTotal = updatedItems.reduce((sum, it) => sum + (it.total_price || 0), 0);
    const grandTotal = Math.round((linesTotal + (quotation.packaging_cost || 0) + (quotation.miscellaneous_charges || 0)) * 100) / 100;

    onChange({
      ...quotation,
      items: updatedItems,
      lines_total: Math.round(linesTotal * 100) / 100,
      grand_total: grandTotal,
    });
  };

  const handleAddItem = () => {
    const nextLine = quotation.items.length > 0 ? Math.max(...quotation.items.map((i) => i.line_number)) + 1 : 1;
    const newItem: QuoteItem = {
      line_number: nextLine,
      part_number: '',
      description: '',
      quantity: 1,
      unit: 'NOS',
      unit_price: null,
      discount_percent: 0,
      total_price: null,
      commodity_code: null,
      equipment_group: selectedGroup || undefined,
      status: 'warning',
      validation_notes: ['Manually added item'],
    };

    onChange({
      ...quotation,
      items: [...quotation.items, newItem],
    });
  };

  const handleDeleteItem = (index: number) => {
    const updatedItems = quotation.items.filter((_, i) => i !== index);
    const linesTotal = updatedItems.reduce((sum, it) => sum + (it.total_price || 0), 0);
    const grandTotal = Math.round((linesTotal + (quotation.packaging_cost || 0) + (quotation.miscellaneous_charges || 0)) * 100) / 100;

    onChange({
      ...quotation,
      items: updatedItems,
      lines_total: Math.round(linesTotal * 100) / 100,
      grand_total: grandTotal,
    });
  };

  const filteredItems = selectedGroup
    ? quotation.items.filter((it) => it.equipment_group === selectedGroup)
    : quotation.items;

  const samplePrice = quotation.items.length > 0 && quotation.items[0].unit_price !== null && quotation.items[0].unit_price !== undefined
    ? quotation.items[0].unit_price
    : 100.0;

  const hasWarnings = validation.warnings_count > 0;
  const hasErrors = validation.errors_count > 0;

  return (
    <div className="space-y-6 max-w-7xl mx-auto py-6">
      {/* Top Banner Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white/75 border border-[#786446]/15 rounded-3xl p-6 shadow-sm backdrop-blur-xl">
        <div>
          <div className="flex items-center space-x-3">
            <h2 className="text-2xl font-bold text-[#26231F] tracking-tight">Quotation Review & Verification</h2>
            <span
              className={`inline-flex items-center space-x-1.5 text-xs font-bold px-3 py-1 rounded-full border shadow-2xs ${
                !hasErrors && !hasWarnings
                  ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                  : hasErrors
                  ? 'bg-rose-50 text-rose-800 border-rose-200'
                  : 'bg-amber-50 text-amber-800 border-amber-200'
              }`}
            >
              {!hasErrors && !hasWarnings ? (
                <>
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>100% Verified</span>
                </>
              ) : hasErrors ? (
                <>
                  <XCircle className="w-3.5 h-3.5" />
                  <span>{validation.errors_count} Critical Error(s)</span>
                </>
              ) : (
                <>
                  <AlertTriangle className="w-3.5 h-3.5" />
                  <span>{validation.warnings_count} Note(s) for Review</span>
                </>
              )}
            </span>
          </div>
          <p className="text-xs text-[#716B61] mt-1.5">
            PDF is 100% data authority. Leading zeros and exact prices are preserved. Review and edit before generating Excel.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            type="button"
            onClick={onGenerate}
            disabled={isGenerating || quotation.items.length === 0 || hasErrors}
            className="flex items-center space-x-2 px-6 py-2.5 rounded-xl text-xs font-bold text-white bg-[#26231F] hover:bg-black disabled:bg-[#716B61]/30 disabled:text-[#716B61] shadow-md hover:shadow-lg transition-all duration-150 hover:scale-[1.02] active:scale-[0.98] cursor-pointer"
          >
            <FileSpreadsheet className="w-4 h-4 text-[#C98B4A]" />
            <span>{isGenerating ? 'Generating...' : 'Approve & Generate Excel'}</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Validation Summary Metrics Bar (Rule 12) */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 bg-white/80 border border-[#786446]/15 rounded-2xl p-4 shadow-2xs backdrop-blur-md">
        <div className="space-y-0.5">
          <p className="text-[10px] font-bold uppercase tracking-wider text-[#716B61]">PDF Items</p>
          <p className="text-sm font-mono font-bold text-[#26231F]">{validation.pdf_item_count || quotation.items.length}</p>
        </div>
        <div className="space-y-0.5">
          <p className="text-[10px] font-bold uppercase tracking-wider text-[#716B61]">Extracted</p>
          <p className="text-sm font-mono font-bold text-[#26231F]">{validation.extracted_item_count || quotation.items.length}</p>
        </div>
        <div className="space-y-0.5">
          <p className="text-[10px] font-bold uppercase tracking-wider text-[#716B61]">Ready for Excel</p>
          <p className="text-sm font-mono font-bold text-emerald-700">{quotation.items.length}</p>
        </div>
        <div className="space-y-0.5">
          <p className="text-[10px] font-bold uppercase tracking-wider text-[#716B61]">Currency</p>
          <p className="text-sm font-mono font-bold text-[#26231F]">{quotation.currency || 'EUR'}</p>
        </div>
        <div className="space-y-0.5">
          <p className="text-[10px] font-bold uppercase tracking-wider text-[#716B61]">Price Validation</p>
          <p className="text-sm font-mono font-semibold text-[#26231F]">
            {validation.price_validation_passed}/{quotation.items.length} verified
          </p>
        </div>
        <div className="space-y-0.5">
          <p className="text-[10px] font-bold uppercase tracking-wider text-[#716B61]">Total Validation</p>
          <p className="text-sm font-semibold text-emerald-700 flex items-center space-x-1">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Verified</span>
          </p>
        </div>
      </div>


      {/* Validation Issue Alerts categorized by severity */}
      {validation.issues.length > 0 && (
        <div className="space-y-2">
          {/* Critical Errors if any */}
          {validation.issues.some((i) => i.issue_type === 'error') && (
            <div className="p-4 rounded-2xl bg-rose-50/90 border border-rose-200/90 space-y-1.5 shadow-2xs backdrop-blur-md">
              <div className="flex items-center space-x-2 text-xs font-bold text-rose-950">
                <AlertCircle className="w-4 h-4 text-rose-600" />
                <span>Critical Errors ({validation.issues.filter((i) => i.issue_type === 'error').length}) — Requires Resolution:</span>
              </div>
              <ul className="text-xs text-rose-900/90 space-y-1 pl-6 list-disc">
                {validation.issues
                  .filter((i) => i.issue_type === 'error')
                  .map((issue, idx) => (
                    <li key={idx}>{issue.message}</li>
                  ))}
              </ul>
            </div>
          )}

          {/* Warnings if any */}
          {validation.issues.some((i) => i.issue_type === 'warning') && (
            <div className="p-4 rounded-2xl bg-amber-50/80 border border-amber-200/80 space-y-1.5 shadow-2xs backdrop-blur-md">
              <div className="flex items-center space-x-2 text-xs font-bold text-amber-900">
                <AlertTriangle className="w-4 h-4 text-amber-600" />
                <span>Warnings & Discrepancies ({validation.issues.filter((i) => i.issue_type === 'warning').length}):</span>
              </div>
              <ul className="text-xs text-amber-900/90 space-y-1 pl-6 list-disc">
                {validation.issues
                  .filter((i) => i.issue_type === 'warning')
                  .map((issue, idx) => (
                    <li key={idx}>{issue.message}</li>
                  ))}
              </ul>
            </div>
          )}

          {/* Non-Inventory Charges & Informational Notes */}
          {validation.issues.some((i) => i.issue_type === 'info') && (
            <div className="p-3.5 rounded-2xl bg-blue-50/80 border border-blue-200/80 space-y-1 shadow-2xs backdrop-blur-md">
              <div className="flex items-center space-x-2 text-xs font-bold text-blue-950">
                <Info className="w-4 h-4 text-blue-600" />
                <span>Non-Inventory & Charges Info ({validation.issues.filter((i) => i.issue_type === 'info').length}):</span>
              </div>
              <ul className="text-xs text-blue-900/90 space-y-1 pl-6 list-disc">
                {validation.issues
                  .filter((i) => i.issue_type === 'info')
                  .map((issue, idx) => (
                    <li key={idx}>{issue.message}</li>
                  ))}
              </ul>
            </div>
          )}
        </div>
      )}


      {/* Top Metadata Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white/65 border border-[#786446]/15 rounded-2xl p-4 shadow-2xs backdrop-blur-md">
          <label className="block text-[11px] font-bold uppercase tracking-wider text-[#716B61] mb-1.5">Quote Reference #</label>
          <input
            type="text"
            value={quotation.quote_number || ''}
            onChange={(e) => handleHeaderChange('quote_number', e.target.value)}
            className="w-full bg-[#F5F1E8] border border-[#786446]/20 rounded-xl px-3 py-1.5 text-xs text-[#26231F] font-mono font-bold focus:border-[#26231F] focus:outline-none"
            placeholder="e.g. 41260607"
          />
        </div>

        <div className="bg-white/65 border border-[#786446]/15 rounded-2xl p-4 shadow-2xs backdrop-blur-md">
          <label className="block text-[11px] font-bold uppercase tracking-wider text-[#716B61] mb-1.5">Customer / Client</label>
          <input
            type="text"
            value={quotation.customer || ''}
            onChange={(e) => handleHeaderChange('customer', e.target.value)}
            className="w-full bg-[#F5F1E8] border border-[#786446]/20 rounded-xl px-3 py-1.5 text-xs text-[#26231F] font-semibold focus:border-[#26231F] focus:outline-none"
            placeholder="e.g. PT. Flow Force Indonesia"
          />
        </div>

        <div className="bg-white/65 border border-[#786446]/15 rounded-2xl p-4 shadow-2xs backdrop-blur-md">
          <label className="block text-[11px] font-bold uppercase tracking-wider text-[#716B61] mb-1.5">Quote Date</label>
          <input
            type="text"
            value={quotation.quote_date || ''}
            onChange={(e) => handleHeaderChange('quote_date', e.target.value)}
            className="w-full bg-[#F5F1E8] border border-[#786446]/20 rounded-xl px-3 py-1.5 text-xs text-[#26231F] font-mono font-semibold focus:border-[#26231F] focus:outline-none"
            placeholder="7/30/2026"
          />
        </div>

        <div className="bg-white/65 border border-[#786446]/15 rounded-2xl p-4 shadow-2xs backdrop-blur-md">
          <label className="block text-[11px] font-bold uppercase tracking-wider text-[#716B61] mb-1.5">Currency</label>
          <input
            type="text"
            value={quotation.currency || 'EUR'}
            onChange={(e) => handleHeaderChange('currency', e.target.value.toUpperCase())}
            className="w-full bg-[#F5F1E8] border border-[#786446]/20 rounded-xl px-3 py-1.5 text-xs text-[#26231F] font-mono font-bold focus:border-[#26231F] focus:outline-none uppercase"
            placeholder="EUR"
          />
        </div>
      </div>

      {/* Equipment Groupings view */}
      <EquipmentGrouping
        groups={quotation.equipment_groups}
        selectedGroup={selectedGroup}
        onSelectGroup={setSelectedGroup}
        totalItemsCount={quotation.items.length}
      />

      {/* Pricing & Margin Config */}
      <PricingConfig
        pricingMode={pricingMode}
        marginPercent={marginPercent}
        supplierDiscountPercent={supplierDiscountPercent}
        onModeChange={onPricingModeChange}
        onMarginChange={onMarginChange}
        onSupplierDiscountChange={onSupplierDiscountChange}
        currency={quotation.currency || 'EUR'}
        sampleUnitPrice={samplePrice}
      />

      {/* Interactive Line Items Table */}
      <div className="bg-white/75 border border-[#786446]/15 rounded-3xl overflow-hidden shadow-sm backdrop-blur-xl">
        <div className="px-6 py-4 border-b border-[#786446]/10 flex items-center justify-between bg-white/60">
          <div className="flex items-center space-x-2.5">
            <span className="text-xs font-bold uppercase tracking-wider text-[#26231F]">Quotation Line Items</span>
            <span className="text-xs bg-[#F5F1E8] text-[#26231F] font-bold font-mono px-2.5 py-0.5 rounded-full border border-[#786446]/15">
              {filteredItems.length} items
            </span>
          </div>

          <button
            type="button"
            onClick={handleAddItem}
            className="flex items-center space-x-1.5 px-3.5 py-1.5 rounded-xl text-xs font-semibold text-[#26231F] hover:text-black bg-white hover:bg-white/90 border border-[#786446]/20 shadow-2xs transition cursor-pointer"
          >
            <Plus className="w-3.5 h-3.5 text-[#C98B4A]" />
            <span>Add Line Item</span>
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse min-w-[1000px]">
            <thead>
              <tr className="border-b border-[#786446]/10 bg-[#F5F1E8]/70 text-[11px] font-bold text-[#716B61] uppercase tracking-wider">
                <th className="py-3 px-3 text-center w-12">#</th>
                <th className="py-3 px-3 w-36">Part Number</th>
                <th className="py-3 px-3">Description & Metadata</th>
                <th className="py-3 px-3 w-20 text-right">Qty</th>
                <th className="py-3 px-3 w-20 text-center">Unit</th>
                <th className="py-3 px-3 w-28 text-right">Unit Price</th>
                <th className="py-3 px-3 w-20 text-right">Disc %</th>
                <th className="py-3 px-3 w-32 text-right">Total Price</th>
                <th className="py-3 px-3 w-28 text-center">Status</th>
                <th className="py-3 px-2 w-12 text-center"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#786446]/10 text-xs">
              {filteredItems.map((item, originalIdx) => {
                const itemIndex = quotation.items.findIndex((i) => i.line_number === item.line_number);
                const isWarning = item.status === 'warning';
                const isError = item.status === 'error';

                return (
                  <tr
                    key={item.line_number || originalIdx}
                    className={`hover:bg-[#F5F1E8]/50 transition-colors group ${
                      isError ? 'bg-rose-50/50' : isWarning ? 'bg-amber-50/40' : ''
                    }`}
                  >
                    <td className="py-3 px-3 text-center font-mono text-[#716B61]">
                      <input
                        type="number"
                        value={item.line_number}
                        onChange={(e) => handleItemChange(itemIndex, 'line_number', parseInt(e.target.value) || 0)}
                        className="w-10 bg-transparent text-center font-mono text-xs text-[#26231F] font-semibold focus:bg-white focus:outline-none rounded"
                      />
                    </td>

                    <td className="py-3 px-3 font-mono">
                      <div className="relative">
                        <input
                          type="text"
                          value={item.part_number}
                          onChange={(e) => handleItemChange(itemIndex, 'part_number', e.target.value)}
                          className="w-full bg-[#F5F1E8]/80 border border-[#786446]/15 rounded-lg px-2.5 py-1 text-xs text-[#26231F] font-mono font-bold focus:border-[#26231F] focus:outline-none"
                          placeholder="e.g. 00138737"
                        />
                        {item.part_number.startsWith('0') && item.part_number.length > 1 && (
                          <span
                            title="Leading zeros preserved"
                            className="absolute right-2 top-1.5 text-[10px] text-emerald-700 font-mono font-bold"
                          >
                            0✓
                          </span>
                        )}
                      </div>
                    </td>

                    <td className="py-3 px-3 space-y-1">
                      <div className="flex items-center space-x-2">
                        <input
                          type="text"
                          value={item.description}
                          onChange={(e) => handleItemChange(itemIndex, 'description', e.target.value)}
                          className="w-full bg-transparent border-b border-transparent focus:border-[#26231F] hover:border-[#786446]/20 px-1.5 py-1 text-xs text-[#26231F] focus:outline-none rounded transition"
                        />
                        {(item.item_type === 'charge' || ['S&H', 'SHIPPING', 'HANDLING', 'FREIGHT', 'PACKAGING', 'MISC'].includes((item.part_number || '').toUpperCase()) || (item.description || '').toUpperCase().includes('SHIPPING & HANDLING')) && (
                          <span className="shrink-0 text-[10px] bg-blue-50 text-blue-800 border border-blue-200 px-1.5 py-0.5 rounded font-sans font-semibold">
                            Charge Line
                          </span>
                        )}
                      </div>
                      {item.commodity_code && (
                        <div className="flex items-center space-x-1.5 text-[10px] font-semibold text-[#716B61] bg-[#F5F1E8] border border-[#786446]/15 px-2 py-0.5 rounded-md w-fit">
                          <Tag className="w-3 h-3 text-[#C98B4A]" />
                          <span>Commodity Code: <strong className="font-mono text-[#26231F]">{item.commodity_code}</strong></span>
                        </div>
                      )}
                    </td>


                    <td className="py-3 px-3 text-right">
                      <input
                        type="number"
                        step="any"
                        value={item.quantity !== null && item.quantity !== undefined ? item.quantity : ''}
                        onChange={(e) => handleItemChange(itemIndex, 'quantity', e.target.value)}
                        placeholder="0"
                        className="w-16 bg-[#F5F1E8]/80 border border-[#786446]/15 rounded-lg px-2 py-1 text-xs text-right font-mono font-bold text-[#26231F] focus:border-[#26231F] focus:outline-none"
                      />
                    </td>

                    <td className="py-3 px-3 text-center">
                      <input
                        type="text"
                        value={item.unit || ''}
                        onChange={(e) => handleItemChange(itemIndex, 'unit', e.target.value.toUpperCase())}
                        placeholder="NOS"
                        className="w-14 bg-transparent text-center font-mono text-xs text-[#716B61] font-semibold focus:bg-white focus:outline-none rounded uppercase"
                      />
                    </td>

                    <td className="py-3 px-3 text-right">
                      <input
                        type="number"
                        step="0.01"
                        value={item.unit_price !== null && item.unit_price !== undefined ? item.unit_price : ''}
                        onChange={(e) => handleItemChange(itemIndex, 'unit_price', e.target.value)}
                        placeholder="0.00"
                        className="w-24 bg-[#F5F1E8]/80 border border-[#786446]/15 rounded-lg px-2 py-1 text-xs text-right font-mono font-bold text-[#26231F] focus:border-[#26231F] focus:outline-none"
                      />
                    </td>

                    <td className="py-3 px-3 text-right">
                      <input
                        type="number"
                        step="0.1"
                        value={item.discount_percent !== null && item.discount_percent !== undefined ? item.discount_percent : ''}
                        onChange={(e) => handleItemChange(itemIndex, 'discount_percent', e.target.value)}
                        placeholder="0"
                        className="w-14 bg-transparent text-right font-mono text-xs text-[#716B61] focus:bg-white focus:outline-none rounded"
                      />
                    </td>

                    <td className="py-3 px-3 text-right font-mono font-bold text-[#26231F]">
                      {item.total_price !== null && item.total_price !== undefined
                        ? item.total_price.toFixed(2)
                        : (item.quantity !== null && item.unit_price !== null && item.quantity !== undefined && item.unit_price !== undefined
                          ? (item.quantity * item.unit_price * (1 - (item.discount_percent || 0) / 100)).toFixed(2)
                          : '-')}
                    </td>

                    <td className="py-3 px-3 text-center">
                      {item.status === 'verified' ? (
                        <span className="inline-flex items-center space-x-1 text-[11px] font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2.5 py-0.5 rounded-full shadow-2xs">
                          <CheckCircle2 className="w-3 h-3" />
                          <span>Verified</span>
                        </span>
                      ) : item.status === 'warning' ? (
                        <span
                          title={item.validation_notes?.join('; ') || 'Needs review'}
                          className="inline-flex items-center space-x-1 text-[11px] font-semibold text-amber-800 bg-amber-50 border border-amber-200 px-2.5 py-0.5 rounded-full shadow-2xs cursor-help"
                        >
                          <AlertTriangle className="w-3 h-3" />
                          <span>Review</span>
                        </span>
                      ) : (
                        <span className="inline-flex items-center space-x-1 text-[11px] font-semibold text-rose-700 bg-rose-50 border border-rose-200 px-2.5 py-0.5 rounded-full shadow-2xs">
                          <XCircle className="w-3 h-3" />
                          <span>Error</span>
                        </span>
                      )}
                    </td>

                    <td className="py-3 px-2 text-center">
                      <button
                        type="button"
                        onClick={() => handleDeleteItem(itemIndex)}
                        className="opacity-0 group-hover:opacity-100 text-[#716B61] hover:text-rose-600 transition p-1 cursor-pointer"
                        title="Remove row"
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

        {/* Footer Summary */}
        <div className="p-5 bg-white/90 border-t border-[#786446]/10 flex flex-wrap items-center justify-between gap-4 text-xs">
          <div className="text-[#716B61] font-medium">
            Showing {filteredItems.length} of {quotation.items.length} items
          </div>

          <div className="flex flex-wrap items-center gap-5 sm:gap-8">
            <div className="text-right">
              <span className="text-[#716B61] mr-2 font-medium">Packaging Costs:</span>
              <span className="font-mono font-bold text-[#26231F]">
                {quotation.currency || 'EUR'} {(quotation.packaging_cost || 0).toFixed(2)}
              </span>
            </div>
            <div className="text-right">
              <span className="text-[#716B61] mr-2 font-medium">Lines Total:</span>
              <span className="font-mono font-bold text-[#26231F] text-sm">
                {quotation.currency || 'EUR'} {(quotation.lines_total || 0).toFixed(2)}
              </span>
            </div>
            <div className="text-right pl-5 border-l border-[#786446]/20">
              <span className="text-[#716B61] mr-2 font-medium">Grand Total:</span>
              <span className="font-mono font-extrabold text-[#26231F] text-base">
                {quotation.currency || 'EUR'} {(quotation.grand_total || quotation.lines_total || 0).toFixed(2)}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
