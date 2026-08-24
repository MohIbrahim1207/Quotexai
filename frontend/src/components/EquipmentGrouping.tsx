import React from 'react';
import { Layers, Cpu } from 'lucide-react';
import type { EquipmentGroup } from '../types/quotation';

interface EquipmentGroupingProps {
  groups: EquipmentGroup[];
  selectedGroup: string | null;
  onSelectGroup: (groupName: string | null) => void;
  totalItemsCount: number;
}

export const EquipmentGrouping: React.FC<EquipmentGroupingProps> = ({
  groups,
  selectedGroup,
  onSelectGroup,
  totalItemsCount,
}) => {
  if (!groups || groups.length === 0) return null;

  return (
    <div className="bg-white/60 border border-[#786446]/15 rounded-2xl p-4 mb-4 backdrop-blur-md shadow-2xs">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-2">
          <Layers className="w-4 h-4 text-[#C98B4A]" />
          <span className="text-xs font-bold text-[#26231F]">Equipment & Machine Groupings</span>
          <span className="text-[11px] text-[#716B61]">({groups.length} detected)</span>
        </div>
        <span className="text-[11px] text-[#716B61]">Filter line items:</span>
      </div>

      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => onSelectGroup(null)}
          className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-all duration-150 flex items-center space-x-1.5 cursor-pointer ${
            selectedGroup === null
              ? 'bg-[#26231F] text-white shadow-xs'
              : 'bg-white/80 text-[#716B61] hover:text-[#26231F] hover:bg-white border border-[#786446]/15 shadow-2xs'
          }`}
        >
          <span>All Items</span>
          <span className={`px-1.5 py-0.2 rounded-full text-[10px] ${selectedGroup === null ? 'bg-white/20 text-white' : 'bg-[#F5F1E8] text-[#716B61]'}`}>
            {totalItemsCount}
          </span>
        </button>

        {groups.map((group, idx) => {
          const isSelected = selectedGroup === group.name;
          return (
            <button
              key={idx}
              type="button"
              onClick={() => onSelectGroup(isSelected ? null : group.name)}
              className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-all duration-150 flex items-center space-x-2 cursor-pointer ${
                isSelected
                  ? 'bg-[#26231F] text-white shadow-xs'
                  : 'bg-white/80 text-[#716B61] hover:text-[#26231F] hover:bg-white border border-[#786446]/15 shadow-2xs'
              }`}
            >
              <Cpu className={`w-3.5 h-3.5 ${isSelected ? 'text-[#C98B4A]' : 'text-[#716B61]'}`} />
              <span className="max-w-[220px] truncate">{group.name}</span>
              {group.serial_numbers && group.serial_numbers.length > 0 && (
                <span className={`text-[10px] px-1.5 py-0.5 rounded font-mono ${isSelected ? 'bg-white/15 text-[#F5F1E8]' : 'bg-[#F5F1E8] text-[#716B61]'}`}>
                  S/N: {group.serial_numbers[0]}
                </span>
              )}
              <span className={`px-1.5 py-0.2 rounded-full text-[10px] ${isSelected ? 'bg-white/20 text-white' : 'bg-[#F5F1E8] text-[#716B61]'}`}>
                {group.line_numbers.length}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
};
