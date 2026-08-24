import React from 'react';
import { Calculator, Percent, Tag } from 'lucide-react';

interface PricingConfigProps {
  pricingMode: 'quoted_price' | 'supplier_discount' | 'add_margin';
  marginPercent: number;
  supplierDiscountPercent: number;
  onModeChange: (mode: 'quoted_price' | 'supplier_discount' | 'add_margin') => void;
  onMarginChange: (margin: number) => void;
  onSupplierDiscountChange: (discount: number) => void;
  currency: string;
  sampleUnitPrice: number;
}

export const PricingConfig: React.FC<PricingConfigProps> = ({
  pricingMode,
  marginPercent,
  supplierDiscountPercent,
  onModeChange,
  onMarginChange,
  onSupplierDiscountChange,
  currency,
  sampleUnitPrice,
}) => {
  let previewPrice = sampleUnitPrice;
  if (pricingMode === 'supplier_discount') {
    previewPrice = sampleUnitPrice * (1 - supplierDiscountPercent / 100);
  } else if (pricingMode === 'add_margin' && marginPercent > 0) {
    if (marginPercent < 100) {
      previewPrice = sampleUnitPrice / (1 - marginPercent / 100);
    } else {
      previewPrice = sampleUnitPrice * (1 + marginPercent / 100);
    }
  }

  return (
    <div className="bg-white/60 border border-[#786446]/15 rounded-2xl p-5 backdrop-blur-md shadow-2xs">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4">
        <div className="flex items-center space-x-2.5">
          <div className="p-2 rounded-xl bg-[#C98B4A]/10 text-[#C98B4A] border border-[#C98B4A]/20">
            <Calculator className="w-4 h-4" />
          </div>
          <div>
            <h4 className="text-xs font-bold text-[#26231F] uppercase tracking-wider">Pricing & Margin Strategy</h4>
            <p className="text-xs text-[#716B61]">Configure how unit prices are populated into the Excel template</p>
          </div>
        </div>

        <div className="text-left sm:text-right bg-white/80 px-3 py-1.5 rounded-xl border border-[#786446]/10 shadow-2xs">
          <span className="text-xs text-[#716B61]">Preview: </span>
          <span className="text-xs font-bold text-[#26231F] font-mono">
            {currency} {sampleUnitPrice.toFixed(2)} → {currency} {previewPrice.toFixed(2)}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <label
          onClick={() => onModeChange('quoted_price')}
          className={`relative flex items-center p-3.5 rounded-2xl border cursor-pointer transition-all duration-150 ${
            pricingMode === 'quoted_price'
              ? 'border-[#26231F] bg-white text-[#26231F] shadow-xs ring-1 ring-black/5'
              : 'border-[#786446]/15 hover:border-[#786446]/30 bg-white/40 hover:bg-white/70 text-[#716B61]'
          }`}
        >
          <input
            type="radio"
            name="pricingMode"
            checked={pricingMode === 'quoted_price'}
            onChange={() => onModeChange('quoted_price')}
            className="text-[#26231F] focus:ring-[#26231F] h-4 w-4 mr-3 accent-[#26231F]"
          />
          <div>
            <p className="text-xs font-bold text-[#26231F]">1. Quoted PDF Price</p>
            <p className="text-[11px] text-[#716B61] mt-0.5">Use exact unit prices extracted from supplier PDF</p>
          </div>
        </label>

        <label
          onClick={() => onModeChange('supplier_discount')}
          className={`relative flex items-center p-3.5 rounded-2xl border cursor-pointer transition-all duration-150 ${
            pricingMode === 'supplier_discount'
              ? 'border-[#26231F] bg-white text-[#26231F] shadow-xs ring-1 ring-black/5'
              : 'border-[#786446]/15 hover:border-[#786446]/30 bg-white/40 hover:bg-white/70 text-[#716B61]'
          }`}
        >
          <input
            type="radio"
            name="pricingMode"
            checked={pricingMode === 'supplier_discount'}
            onChange={() => onModeChange('supplier_discount')}
            className="text-[#26231F] focus:ring-[#26231F] h-4 w-4 mr-3 accent-[#26231F]"
          />
          <div className="flex-1">
            <p className="text-xs font-bold text-[#26231F]">2. Apply Discount</p>
            <p className="text-[11px] text-[#716B61] mt-0.5">Deduct supplier discount from unit price</p>
          </div>
        </label>

        <label
          onClick={() => onModeChange('add_margin')}
          className={`relative flex items-center p-3.5 rounded-2xl border cursor-pointer transition-all duration-150 ${
            pricingMode === 'add_margin'
              ? 'border-[#26231F] bg-white text-[#26231F] shadow-xs ring-1 ring-black/5'
              : 'border-[#786446]/15 hover:border-[#786446]/30 bg-white/40 hover:bg-white/70 text-[#716B61]'
          }`}
        >
          <input
            type="radio"
            name="pricingMode"
            checked={pricingMode === 'add_margin'}
            onChange={() => onModeChange('add_margin')}
            className="text-[#26231F] focus:ring-[#26231F] h-4 w-4 mr-3 accent-[#26231F]"
          />
          <div className="flex-1">
            <p className="text-xs font-bold text-[#26231F]">3. Add Target Margin</p>
            <p className="text-[11px] text-[#716B61] mt-0.5">Calculate customer selling price with margin</p>
          </div>
        </label>
      </div>

      {pricingMode === 'add_margin' && (
        <div className="mt-4 p-4 rounded-2xl bg-white/80 border border-[#786446]/15 flex flex-wrap items-center justify-between gap-4 shadow-2xs">
          <div className="flex items-center space-x-3">
            <Percent className="w-4 h-4 text-[#C98B4A]" />
            <span className="text-xs font-bold text-[#26231F]">Target Profit Margin:</span>
            <div className="relative w-28">
              <input
                type="number"
                min="0"
                max="99"
                step="0.5"
                value={marginPercent}
                onChange={(e) => onMarginChange(parseFloat(e.target.value) || 0)}
                className="w-full bg-[#F5F1E8] border border-[#786446]/20 rounded-xl px-3 py-1.5 text-xs text-[#26231F] font-semibold focus:outline-none focus:border-[#26231F]"
              />
              <span className="absolute right-3 top-1.5 text-xs text-[#716B61] font-semibold">%</span>
            </div>
          </div>

          <div className="text-xs text-[#716B61] font-mono">
            Selling Price = Cost / (1 - {marginPercent}%)
          </div>
        </div>
      )}

      {pricingMode === 'supplier_discount' && (
        <div className="mt-4 p-4 rounded-2xl bg-white/80 border border-[#786446]/15 flex flex-wrap items-center justify-between gap-4 shadow-2xs">
          <div className="flex items-center space-x-3">
            <Tag className="w-4 h-4 text-[#C98B4A]" />
            <span className="text-xs font-bold text-[#26231F]">Supplier Discount:</span>
            <div className="relative w-28">
              <input
                type="number"
                min="0"
                max="100"
                step="0.5"
                value={supplierDiscountPercent}
                onChange={(e) => onSupplierDiscountChange(parseFloat(e.target.value) || 0)}
                className="w-full bg-[#F5F1E8] border border-[#786446]/20 rounded-xl px-3 py-1.5 text-xs text-[#26231F] font-semibold focus:outline-none focus:border-[#26231F]"
              />
              <span className="absolute right-3 top-1.5 text-xs text-[#716B61] font-semibold">%</span>
            </div>
          </div>
          <div className="text-xs text-[#716B61] font-mono">
            Net Price = Quoted Price × (1 - {supplierDiscountPercent}%)
          </div>
        </div>
      )}
    </div>
  );
};
