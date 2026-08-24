import React, { useState } from 'react';
import { X, FileSpreadsheet } from 'lucide-react';
import type { ColumnMappingConfig, TemplateAnalysisResponse } from '../types/quotation';

interface TemplateMappingModalProps {
  isOpen: boolean;
  onClose: () => void;
  analysis: TemplateAnalysisResponse | null;
  mapping?: ColumnMappingConfig;
  onSaveMapping: (newMapping: ColumnMappingConfig) => void;
}

export const TemplateMappingModal: React.FC<TemplateMappingModalProps> = ({
  isOpen,
  onClose,
  analysis,
  mapping,
  onSaveMapping,
}) => {
  const defaultMapping: ColumnMappingConfig = {
    line_number_column: 'A',
    part_number_column: 'B',
    description_column: 'C',
    quantity_column: 'E',
    unit_price_column: 'D',
    start_row: 6,
  };
  const [localMapping, setLocalMapping] = useState<ColumnMappingConfig>({ ...(mapping || analysis?.suggested_mapping || defaultMapping) });

  if (!isOpen) return null;

  const handleSave = () => {
    onSaveMapping(localMapping);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/30 backdrop-blur-md flex items-center justify-center p-4">
      <div className="bg-[#F5F1E8] border border-[#786446]/20 rounded-3xl w-full max-w-2xl overflow-hidden shadow-2xl animate-in fade-in zoom-in-95 duration-150">
        <div className="px-6 py-5 border-b border-[#786446]/10 bg-white/70 backdrop-blur-md flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 rounded-xl bg-[#26231F] text-white">
              <FileSpreadsheet className="w-5 h-5 text-[#C98B4A]" />
            </div>
            <div>
              <h3 className="text-base font-bold text-[#26231F]">Excel Template Column Mapping</h3>
              <p className="text-xs text-[#716B61]">Auto-detected headers & cell destinations</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-xl text-[#716B61] hover:text-[#26231F] hover:bg-white/80 transition cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 space-y-6 max-h-[75vh] overflow-y-auto">
          {analysis && Object.keys(analysis.detected_headers).length > 0 && (
            <div className="p-4 rounded-2xl bg-white/70 border border-[#786446]/15 space-y-2 shadow-2xs">
              <span className="text-xs font-bold text-[#26231F]">Detected Table Headers in Template:</span>
              <div className="flex flex-wrap gap-2">
                {Object.entries(analysis.detected_headers).map(([col, header]) => (
                  <span key={col} className="text-xs px-2.5 py-1 rounded-lg bg-[#F5F1E8] text-[#26231F] border border-[#786446]/15">
                    <strong className="font-mono text-[#26231F]">{col}:</strong> {header}
                  </span>
                ))}
              </div>
            </div>
          )}

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div>
              <label className="block text-xs font-bold text-[#716B61] mb-1">Item No Col</label>
              <input
                type="text"
                maxLength={2}
                value={localMapping.line_number_column || ''}
                onChange={(e) => setLocalMapping({ ...localMapping, line_number_column: e.target.value.toUpperCase() })}
                className="w-full bg-white border border-[#786446]/20 rounded-xl px-3 py-2 text-xs text-[#26231F] font-bold uppercase font-mono text-center focus:border-[#26231F] focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-[#716B61] mb-1">Part Number Col</label>
              <input
                type="text"
                maxLength={2}
                value={localMapping.part_number_column || ''}
                onChange={(e) => setLocalMapping({ ...localMapping, part_number_column: e.target.value.toUpperCase() })}
                className="w-full bg-white border border-[#786446]/20 rounded-xl px-3 py-2 text-xs text-[#26231F] font-bold uppercase font-mono text-center focus:border-[#26231F] focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-[#716B61] mb-1">Description Col</label>
              <input
                type="text"
                maxLength={2}
                value={localMapping.description_column || ''}
                onChange={(e) => setLocalMapping({ ...localMapping, description_column: e.target.value.toUpperCase() })}
                className="w-full bg-white border border-[#786446]/20 rounded-xl px-3 py-2 text-xs text-[#26231F] font-bold uppercase font-mono text-center focus:border-[#26231F] focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-[#716B61] mb-1">Quantity Col</label>
              <input
                type="text"
                maxLength={2}
                value={localMapping.quantity_column || ''}
                onChange={(e) => setLocalMapping({ ...localMapping, quantity_column: e.target.value.toUpperCase() })}
                className="w-full bg-white border border-[#786446]/20 rounded-xl px-3 py-2 text-xs text-[#26231F] font-bold uppercase font-mono text-center focus:border-[#26231F] focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-[#716B61] mb-1">Unit/UOM Col</label>
              <input
                type="text"
                maxLength={2}
                value={localMapping.unit_column || ''}
                onChange={(e) => setLocalMapping({ ...localMapping, unit_column: e.target.value.toUpperCase() })}
                className="w-full bg-white border border-[#786446]/20 rounded-xl px-3 py-2 text-xs text-[#26231F] font-bold uppercase font-mono text-center focus:border-[#26231F] focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-[#716B61] mb-1">Unit Price Col</label>
              <input
                type="text"
                maxLength={2}
                value={localMapping.unit_price_column || ''}
                onChange={(e) => setLocalMapping({ ...localMapping, unit_price_column: e.target.value.toUpperCase() })}
                className="w-full bg-white border border-[#786446]/20 rounded-xl px-3 py-2 text-xs text-[#26231F] font-bold uppercase font-mono text-center focus:border-[#26231F] focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-[#716B61] mb-1">Total Price Col</label>
              <input
                type="text"
                maxLength={2}
                value={localMapping.total_price_column || ''}
                onChange={(e) => setLocalMapping({ ...localMapping, total_price_column: e.target.value.toUpperCase() })}
                className="w-full bg-white border border-[#786446]/20 rounded-xl px-3 py-2 text-xs text-[#26231F] font-bold uppercase font-mono text-center focus:border-[#26231F] focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-[#716B61] mb-1">Start Row Number</label>
              <input
                type="number"
                min={1}
                value={localMapping.start_row}
                onChange={(e) => setLocalMapping({ ...localMapping, start_row: parseInt(e.target.value) || 11 })}
                className="w-full bg-white border border-[#786446]/20 rounded-xl px-3 py-2 text-xs text-[#26231F] font-bold font-mono text-center focus:border-[#26231F] focus:outline-none"
              />
            </div>
          </div>

          <div className="pt-4 border-t border-[#786446]/10">
            <h4 className="text-xs font-bold uppercase tracking-wider text-[#716B61] mb-3">Header Metadata Cells (Optional)</h4>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div>
                <label className="block text-[11px] font-bold text-[#716B61] mb-1">Quote # Cell</label>
                <input
                  type="text"
                  value={localMapping.quote_number_cell || ''}
                  onChange={(e) => setLocalMapping({ ...localMapping, quote_number_cell: e.target.value.toUpperCase() })}
                  className="w-full bg-white border border-[#786446]/20 rounded-xl px-3 py-1.5 text-xs text-[#26231F] font-bold uppercase font-mono focus:border-[#26231F] focus:outline-none"
                  placeholder="G5"
                />
              </div>

              <div>
                <label className="block text-[11px] font-bold text-[#716B61] mb-1">Customer Cell</label>
                <input
                  type="text"
                  value={localMapping.customer_cell || ''}
                  onChange={(e) => setLocalMapping({ ...localMapping, customer_cell: e.target.value.toUpperCase() })}
                  className="w-full bg-white border border-[#786446]/20 rounded-xl px-3 py-1.5 text-xs text-[#26231F] font-bold uppercase font-mono focus:border-[#26231F] focus:outline-none"
                  placeholder="B5"
                />
              </div>

              <div>
                <label className="block text-[11px] font-bold text-[#716B61] mb-1">Date Cell</label>
                <input
                  type="text"
                  value={localMapping.date_cell || ''}
                  onChange={(e) => setLocalMapping({ ...localMapping, date_cell: e.target.value.toUpperCase() })}
                  className="w-full bg-white border border-[#786446]/20 rounded-xl px-3 py-1.5 text-xs text-[#26231F] font-bold uppercase font-mono focus:border-[#26231F] focus:outline-none"
                  placeholder="G6"
                />
              </div>

              <div>
                <label className="block text-[11px] font-bold text-[#716B61] mb-1">Currency Cell</label>
                <input
                  type="text"
                  value={localMapping.currency_cell || ''}
                  onChange={(e) => setLocalMapping({ ...localMapping, currency_cell: e.target.value.toUpperCase() })}
                  className="w-full bg-white border border-[#786446]/20 rounded-xl px-3 py-1.5 text-xs text-[#26231F] font-bold uppercase font-mono focus:border-[#26231F] focus:outline-none"
                  placeholder="G7"
                />
              </div>
            </div>
          </div>
        </div>

        <div className="px-6 py-4 bg-white/70 border-t border-[#786446]/10 flex justify-end space-x-3">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-xl text-xs font-semibold text-[#716B61] hover:text-[#26231F] bg-white border border-[#786446]/20 shadow-2xs transition cursor-pointer"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSave}
            className="px-5 py-2 rounded-xl text-xs font-bold text-white bg-[#26231F] hover:bg-black transition shadow-sm cursor-pointer"
          >
            Apply Column Mapping
          </button>
        </div>
      </div>
    </div>
  );
};
