import React, { useState, useEffect, useMemo, useCallback } from 'react';
import {
  Layers,
  Search,
  RefreshCw,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Package,
  Layers2,
  CheckCircle2,
  Box,
  SlidersHorizontal,
} from 'lucide-react';
import type {
  ZohoCompositeItem,
  ZohoCompositeMappedComponent,
  SupplierQuotationData,
  CalculatedLinePrice,
} from '../../types/supplierPricing';
import { supplierPricingApi } from '../../services/supplierPricingApi';

interface CompositeItemsSectionProps {
  organizationId?: string;
  quotation?: SupplierQuotationData | null;
  calculatedItems?: CalculatedLinePrice[];
}

const formatPrice = (val: number | null | undefined, curr: string = 'IDR') => {
  if (val === null || val === undefined || isNaN(val)) return '0.00';
  const isZeroDec = curr.toUpperCase() === 'IDR';
  return val.toLocaleString(undefined, {
    minimumFractionDigits: isZeroDec ? 0 : 2,
    maximumFractionDigits: 2,
  });
};

export const CompositeItemsSection: React.FC<CompositeItemsSectionProps> = ({
  organizationId = '741367552',
  quotation: _quotation,
  calculatedItems = [],
}) => {
  const [compositeItems, setCompositeItems] = useState<ZohoCompositeItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [typeFilter, setTypeFilter] = useState<'ALL' | 'Assembly' | 'Kit'>('ALL');

  // Expanded component details cache by composite_item_id
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [componentCache, setComponentCache] = useState<Record<string, ZohoCompositeMappedComponent[]>>({});
  const [loadingComponentId, setLoadingComponentId] = useState<string | null>(null);
  const [componentError, setComponentError] = useState<Record<string, string>>({});

  const fetchCompositeItems = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await supplierPricingApi.listCompositeItems(undefined, organizationId);
      if (res && Array.isArray(res.composite_items)) {
        setCompositeItems(res.composite_items);
      } else {
        setCompositeItems([]);
      }
    } catch (err: any) {
      console.error('Failed to load composite items:', err);
      const detail = err.response?.data?.detail || err.message || 'Unable to load Composite Items';
      setError(detail);
    } finally {
      setIsLoading(false);
    }
  }, [organizationId]);

  useEffect(() => {
    fetchCompositeItems();
  }, [fetchCompositeItems]);

  // Merge Zoho Composite Items with any quotation items identified as kits / new composite items
  const combinedItems: ZohoCompositeItem[] = useMemo(() => {
    const existingSkuSet = new Set<string>();
    const items: ZohoCompositeItem[] = [];

    // 1. Existing items from Zoho Books (always Action = UPDATE)
    compositeItems.forEach((ci) => {
      const sku = (ci.sku || ci.part_number || '').trim();
      if (sku) {
        existingSkuSet.add(sku.toLowerCase());
      }
      items.push({
        ...ci,
        action: 'UPDATE',
      });
    });

    // 2. If quotation has calculated items, check if any represent new composite items
    // (e.g. if part of quotation or kit not in Zoho)
    if (calculatedItems && calculatedItems.length > 0) {
      calculatedItems.forEach((calc) => {
        const pn = (calc.part_number || '').trim();
        const desc = (calc.description || '').toLowerCase();
        const isKitOrAssembly = desc.includes('assembly') || desc.includes('kit') || desc.includes('set') || desc.includes('system');

        if (pn && isKitOrAssembly && !existingSkuSet.has(pn.toLowerCase())) {
          existingSkuSet.add(pn.toLowerCase());
          items.push({
            composite_item_id: null,
            name: calc.description || pn,
            sku: pn,
            part_number: pn,
            description: calc.description,
            rate: calc.final_unit_selling_price || 0,
            unit: calc.unit || 'Set',
            status: 'draft',
            item_type: 'kit',
            combo_type: 'kit',
            action: 'CREATE',
            mapped_items: [],
          });
        }
      });
    }

    return items;
  }, [compositeItems, calculatedItems]);

  // Filtered items based on search query and type filter
  const filteredItems = useMemo(() => {
    return combinedItems.filter((item) => {
      const q = searchQuery.toLowerCase().trim();
      const sku = (item.sku || item.part_number || '').toLowerCase();
      const name = (item.name || item.item_name || '').toLowerCase();
      const desc = (item.description || '').toLowerCase();

      const matchesSearch = !q || sku.includes(q) || name.includes(q) || desc.includes(q);

      // Map Type to Assembly or Kit
      const rawType = (item.combo_type || item.item_type || '').toLowerCase();
      const mappedType = rawType === 'kit' ? 'Kit' : 'Assembly';

      const matchesType = typeFilter === 'ALL' || mappedType === typeFilter;

      return matchesSearch && matchesType;
    });
  }, [combinedItems, searchQuery, typeFilter]);

  // Summary counts
  const summary = useMemo(() => {
    const total = combinedItems.length;
    const existing = combinedItems.filter((it) => it.action === 'UPDATE' && it.composite_item_id).length;
    const newSkus = combinedItems.filter((it) => it.action === 'CREATE' || !it.composite_item_id).length;
    return { total, existing, newSkus };
  }, [combinedItems]);

  // Handle expanding row to fetch and display component details
  const handleToggleExpand = async (item: ZohoCompositeItem) => {
    const id = item.composite_item_id;
    if (!id) return; // New composite items don't have components in Zoho yet

    if (expandedId === id) {
      setExpandedId(null);
      return;
    }

    setExpandedId(id);

    // If already in cache, skip API call
    if (componentCache[id]) {
      return;
    }

    // Call GET /api/supplier-pricing/zoho/composite-items/{composite_item_id}
    setLoadingComponentId(id);
    setComponentError((prev) => ({ ...prev, [id]: '' }));

    try {
      const res = await supplierPricingApi.getCompositeItem(id, organizationId);
      const mapped = res?.composite_item?.mapped_items || [];
      setComponentCache((prev) => ({
        ...prev,
        [id]: mapped,
      }));
    } catch (err: any) {
      console.error(`Failed to load components for ${id}:`, err);
      const msg = err.response?.data?.detail || err.message || 'Unable to fetch components from Zoho Books';
      setComponentError((prev) => ({
        ...prev,
        [id]: msg,
      }));
    } finally {
      setLoadingComponentId(null);
    }
  };

  return (
    <div className="rounded-3xl border border-[#786446]/20 bg-white/80 backdrop-blur-xl p-6 shadow-xs space-y-6 animate-in fade-in duration-200">
      {/* Section Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#786446]/10 pb-4">
        <div className="flex items-start space-x-3">
          <div className="p-2.5 rounded-2xl bg-[#C98B4A]/10 text-[#C98B4A] border border-[#C98B4A]/25 shrink-0 mt-0.5">
            <Layers className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-[#A66E32]">
                Zoho Books • Composite Items
              </span>
              <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-[#C98B4A]/15 text-[#8F5E24] border border-[#C98B4A]/25">
                Assemblies & Kits
              </span>
            </div>
            <h3 className="text-lg font-bold text-[#26231F] mt-0.5">
              Composite Item Management
            </h3>
            <p className="text-xs text-[#716B61] mt-0.5">
              Catalog of multi-component kits and assemblies in Zoho Books (Org ID: {organizationId}).
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2 self-start sm:self-auto">
          <button
            onClick={fetchCompositeItems}
            disabled={isLoading}
            className="flex items-center space-x-1.5 text-xs font-semibold px-4 py-2 rounded-xl bg-white border border-[#786446]/20 text-[#716B61] hover:text-[#26231F] hover:bg-[#786446]/5 transition cursor-pointer shadow-2xs disabled:opacity-50"
            title="Refresh Composite Items from Zoho"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* 1. Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="p-4 rounded-2xl bg-white/70 border border-[#786446]/15 shadow-2xs">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold text-[#716B61] uppercase tracking-wider">
              Total Composite Items
            </span>
            <Layers className="w-4 h-4 text-[#716B61]" />
          </div>
          <div className="text-2xl font-black font-mono text-[#26231F] mt-1">
            {isLoading ? '...' : summary.total}
          </div>
          <p className="text-[11px] text-[#716B61] mt-0.5">
            Total assemblies & kits in scope
          </p>
        </div>

        <div className="p-4 rounded-2xl bg-blue-500/10 border border-blue-500/20 shadow-2xs">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold text-blue-800 uppercase tracking-wider">
              Existing Composite SKUs
            </span>
            <CheckCircle2 className="w-4 h-4 text-blue-600" />
          </div>
          <div className="text-2xl font-black font-mono text-blue-900 mt-1">
            {isLoading ? '...' : summary.existing}
          </div>
          <p className="text-[11px] text-blue-700 mt-0.5">
            Verified in Zoho Books (Action: UPDATE)
          </p>
        </div>

        <div className="p-4 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 shadow-2xs">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold text-emerald-800 uppercase tracking-wider">
              New Composite SKUs
            </span>
            <Package className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="text-2xl font-black font-mono text-emerald-900 mt-1">
            {isLoading ? '...' : summary.newSkus}
          </div>
          <p className="text-[11px] text-emerald-700 mt-0.5">
            Not yet registered (Action: CREATE)
          </p>
        </div>
      </div>

      {/* 2. Search / Filter Controls */}
      <div className="flex flex-col sm:flex-row items-center gap-3">
        <div className="relative flex-1 w-full">
          <Search className="w-4 h-4 absolute left-3.5 top-3 text-[#716B61]" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search composite items by SKU, Name, or Description..."
            className="w-full text-xs bg-white border border-[#786446]/20 rounded-xl pl-10 pr-4 py-2.5 text-[#26231F] placeholder:text-[#716B61]/60 focus:outline-none focus:border-[#C98B4A]"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-3 top-2.5 text-xs text-[#716B61] hover:text-[#26231F]"
            >
              ✕
            </button>
          )}
        </div>

        <div className="flex items-center space-x-2 self-start sm:self-auto shrink-0">
          <SlidersHorizontal className="w-3.5 h-3.5 text-[#716B61]" />
          <span className="text-xs font-medium text-[#716B61]">Type:</span>
          {(['ALL', 'Assembly', 'Kit'] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTypeFilter(t)}
              className={`text-xs px-3 py-1.5 rounded-xl font-semibold transition cursor-pointer ${
                typeFilter === t
                  ? 'bg-[#26231F] text-white shadow-2xs'
                  : 'bg-white border border-[#786446]/20 text-[#716B61] hover:text-[#26231F]'
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {/* 8. Loading State */}
      {isLoading && (
        <div className="p-12 text-center rounded-2xl bg-white/50 border border-[#786446]/10 space-y-3">
          <RefreshCw className="w-6 h-6 text-[#C98B4A] animate-spin mx-auto" />
          <p className="text-sm font-semibold text-[#26231F]">Loading composite items...</p>
          <p className="text-xs text-[#716B61]">Fetching assemblies and component maps from Zoho Books.</p>
        </div>
      )}

      {/* 8. Error State with Retry Button */}
      {!isLoading && error && (
        <div className="p-6 rounded-2xl bg-rose-50 border border-rose-200 text-rose-900 space-y-3">
          <div className="flex items-start space-x-3">
            <AlertTriangle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
            <div className="space-y-1">
              <h4 className="text-sm font-bold text-rose-950">Unable to load Composite Items</h4>
              <p className="text-xs text-rose-800 leading-relaxed">{error}</p>
            </div>
          </div>
          <div className="pt-2">
            <button
              onClick={fetchCompositeItems}
              className="px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-700 text-white text-xs font-semibold transition cursor-pointer shadow-xs inline-flex items-center space-x-1.5"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Retry</span>
            </button>
          </div>
        </div>
      )}

      {/* 9. Empty State */}
      {!isLoading && !error && filteredItems.length === 0 && (
        <div className="p-12 text-center rounded-2xl bg-white/50 border border-[#786446]/15 space-y-2">
          <Box className="w-8 h-8 text-[#716B61]/50 mx-auto" />
          <h4 className="text-sm font-bold text-[#26231F]">No Composite Items found.</h4>
          <p className="text-xs text-[#716B61]">
            {searchQuery
              ? `No items match query "${searchQuery}". Try a different SKU or part description.`
              : 'No composite items currently recorded in Zoho Books.'}
          </p>
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="mt-2 text-xs font-bold text-[#C98B4A] hover:underline cursor-pointer"
            >
              Clear Search Filter
            </button>
          )}
        </div>
      )}

      {/* 3. Composite Item Table */}
      {!isLoading && !error && filteredItems.length > 0 && (
        <div className="overflow-x-auto rounded-2xl border border-[#786446]/15 bg-white">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-[#786446]/15 bg-[#786446]/5 text-[#716B61]">
                <th className="py-3 px-3.5 font-bold">SKU</th>
                <th className="py-3 px-3.5 font-bold">Name</th>
                <th className="py-3 px-3.5 font-bold">Type</th>
                <th className="py-3 px-3.5 font-bold">Unit</th>
                <th className="py-3 px-3.5 font-bold text-right">Selling Rate</th>
                <th className="py-3 px-3.5 font-bold">Status</th>
                <th className="py-3 px-3.5 font-bold">Components</th>
                <th className="py-3 px-3.5 font-bold">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#786446]/10">
              {filteredItems.map((item, idx) => {
                const sku = item.sku || item.part_number || '-';
                const name = item.name || item.item_name || 'Unnamed Composite Item';
                const rawType = (item.combo_type || item.item_type || '').toLowerCase();
                const displayType = rawType === 'kit' ? 'Kit' : 'Assembly';
                const isExisting = item.action === 'UPDATE' && Boolean(item.composite_item_id);
                const isExpanded = expandedId === item.composite_item_id;

                return (
                  <React.Fragment key={item.composite_item_id || `new-${idx}`}>
                    <tr
                      onClick={() => item.composite_item_id && handleToggleExpand(item)}
                      className={`transition cursor-pointer ${
                        isExpanded ? 'bg-[#786446]/8' : 'hover:bg-[#786446]/5'
                      }`}
                    >
                      {/* SKU */}
                      <td className="py-3 px-3.5 font-mono font-bold text-[#26231F]">
                        <div className="flex items-center space-x-1.5">
                          {item.composite_item_id ? (
                            isExpanded ? (
                              <ChevronUp className="w-3.5 h-3.5 text-[#C98B4A]" />
                            ) : (
                              <ChevronDown className="w-3.5 h-3.5 text-[#716B61]" />
                            )
                          ) : (
                            <span className="w-3.5" />
                          )}
                          <span>{sku}</span>
                        </div>
                        {isExisting && item.composite_item_id ? (
                          <div className="text-[10px] font-mono text-[#716B61] mt-0.5 ml-5">
                            ID: <span className="font-semibold">{item.composite_item_id}</span>
                          </div>
                        ) : (
                          <div className="text-[10px] text-amber-700 italic ml-5">
                            No Zoho ID yet (New)
                          </div>
                        )}
                      </td>

                      {/* Name */}
                      <td className="py-3 px-3.5 text-[#26231F] max-w-xs">
                        <div className="font-medium line-clamp-2">{name}</div>
                        {item.description && item.description !== name && (
                          <div className="text-[11px] text-[#716B61] line-clamp-1 mt-0.5">
                            {item.description}
                          </div>
                        )}
                      </td>

                      {/* Type (Assembly / Kit) */}
                      <td className="py-3 px-3.5">
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-bold ${
                            displayType === 'Kit'
                              ? 'bg-purple-500/10 text-purple-800 border border-purple-500/25'
                              : 'bg-blue-500/10 text-blue-800 border border-blue-500/25'
                          }`}
                        >
                          {displayType}
                        </span>
                      </td>

                      {/* Unit */}
                      <td className="py-3 px-3.5 text-[#716B61] font-mono">
                        {item.unit || 'Set'}
                      </td>

                      {/* Selling Rate */}
                      <td className="py-3 px-3.5 text-right font-mono font-bold text-[#26231F]">
                        {formatPrice(item.rate, 'IDR')}
                      </td>

                      {/* Status */}
                      <td className="py-3 px-3.5">
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                            item.status === 'active' || item.status === 'ACTIVE'
                              ? 'bg-emerald-500/15 text-emerald-800 border border-emerald-500/25'
                              : 'bg-zinc-500/15 text-zinc-700 border border-zinc-500/25'
                          }`}
                        >
                          {item.status || 'Active'}
                        </span>
                      </td>

                      {/* Components column */}
                      <td className="py-3 px-3.5">
                        {item.composite_item_id ? (
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleToggleExpand(item);
                            }}
                            className="inline-flex items-center space-x-1 text-xs text-[#C98B4A] hover:text-[#A66E32] font-semibold hover:underline"
                          >
                            <Layers2 className="w-3.5 h-3.5" />
                            <span>
                              {componentCache[item.composite_item_id]
                                ? `${componentCache[item.composite_item_id].length} items`
                                : 'View components'}
                            </span>
                          </button>
                        ) : (
                          <span className="text-[#716B61] text-[11px] italic">Pending creation</span>
                        )}
                      </td>

                      {/* Action column (Verified & protected by Stage 4 confirmation guardrail) */}
                      <td className="py-3 px-3.5">
                        {isExisting ? (
                          <span
                            className="inline-flex items-center px-3 py-1 rounded-lg text-xs font-bold bg-blue-500/15 text-blue-900 border border-blue-500/30 cursor-not-allowed select-none"
                            title="Protected: Requires Stage 4 explicit confirmation before syncing"
                          >
                            UPDATE
                          </span>
                        ) : (
                          <span
                            className="inline-flex items-center px-3 py-1 rounded-lg text-xs font-bold bg-emerald-500/15 text-emerald-900 border border-emerald-500/30 cursor-not-allowed select-none"
                            title="Protected: Requires Stage 4 explicit confirmation before syncing"
                          >
                            CREATE
                          </span>
                        )}
                      </td>
                    </tr>

                    {/* 6. Expandable Component Details Row */}
                    {isExpanded && item.composite_item_id && (
                      <tr className="bg-[#786446]/5 border-t border-b border-[#786446]/15">
                        <td colSpan={8} className="p-4 pl-10">
                          <div className="rounded-2xl border border-[#786446]/20 bg-white p-4 space-y-3 shadow-2xs">
                            <div className="flex items-center justify-between border-b border-[#786446]/10 pb-2">
                              <div className="flex items-center space-x-2">
                                <Layers2 className="w-4 h-4 text-[#C98B4A]" />
                                <h5 className="text-xs font-bold text-[#26231F]">
                                  Component Breakdown for {name}
                                </h5>
                                <span className="text-[10px] font-mono text-[#716B61] bg-[#786446]/10 px-2 py-0.5 rounded">
                                  ID: {item.composite_item_id}
                                </span>
                              </div>
                              <span className="text-[11px] text-[#716B61]">
                                GET /api/supplier-pricing/zoho/composite-items/{item.composite_item_id}
                              </span>
                            </div>

                            {/* Loading components */}
                            {loadingComponentId === item.composite_item_id && (
                              <div className="py-6 text-center text-xs text-[#716B61] flex items-center justify-center space-x-2">
                                <RefreshCw className="w-4 h-4 animate-spin text-[#C98B4A]" />
                                <span>Loading component mapped items from Zoho Books...</span>
                              </div>
                            )}

                            {/* Component error */}
                            {componentError[item.composite_item_id] && (
                              <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-xs text-rose-800">
                                {componentError[item.composite_item_id]}
                              </div>
                            )}

                            {/* Components Table */}
                            {componentCache[item.composite_item_id] && (
                              <>
                                {componentCache[item.composite_item_id].length === 0 ? (
                                  <div className="py-4 text-center text-xs text-[#716B61] italic">
                                    No component items mapped to this composite item in Zoho Books.
                                  </div>
                                ) : (
                                  <div className="overflow-x-auto">
                                    <table className="w-full text-left text-[11px] border-collapse">
                                      <thead>
                                        <tr className="border-b border-[#786446]/10 text-[#716B61] font-semibold">
                                          <th className="py-1.5 px-2.5">Component SKU</th>
                                          <th className="py-1.5 px-2.5">Component Name</th>
                                          <th className="py-1.5 px-2.5">Zoho Item ID</th>
                                          <th className="py-1.5 px-2.5">Product Type</th>
                                          <th className="py-1.5 px-2.5 text-right">Quantity</th>
                                          <th className="py-1.5 px-2.5">Unit</th>
                                          <th className="py-1.5 px-2.5 text-right">Rate</th>
                                        </tr>
                                      </thead>
                                      <tbody className="divide-y divide-[#786446]/10">
                                        {componentCache[item.composite_item_id].map((comp, cIdx) => (
                                          <tr key={comp.item_id || cIdx} className="hover:bg-[#786446]/5">
                                            <td className="py-2 px-2.5 font-mono font-bold text-blue-900">
                                              {comp.sku || '-'}
                                            </td>
                                            <td className="py-2 px-2.5 text-[#26231F] font-medium">
                                              {comp.name || comp.item_name || 'Component Item'}
                                            </td>
                                            <td className="py-2 px-2.5 font-mono text-[#716B61]">
                                              {comp.item_id}
                                            </td>
                                            <td className="py-2 px-2.5">
                                              <span className="px-1.5 py-0.5 rounded bg-zinc-100 text-zinc-700 text-[10px]">
                                                {comp.product_type || 'goods'}
                                              </span>
                                            </td>
                                            <td className="py-2 px-2.5 text-right font-mono font-bold text-[#26231F]">
                                              {comp.quantity || 1}
                                            </td>
                                            <td className="py-2 px-2.5 text-[#716B61]">
                                              {comp.unit || 'NOS'}
                                            </td>
                                            <td className="py-2 px-2.5 text-right font-mono text-emerald-800">
                                              {comp.rate !== undefined ? formatPrice(comp.rate, 'IDR') : '-'}
                                            </td>
                                          </tr>
                                        ))}
                                      </tbody>
                                    </table>
                                  </div>
                                )}
                              </>
                            )}
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
      )}
    </div>
  );
};
