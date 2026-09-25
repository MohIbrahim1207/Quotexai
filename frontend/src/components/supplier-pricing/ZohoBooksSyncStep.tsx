import React, { useState, useEffect } from 'react';
import {
  BookOpen,
  ArrowLeft,
  ShieldAlert,
  CheckCircle2,
  RefreshCw,
  Search,
  AlertTriangle,
  Send,
  Layers,
} from 'lucide-react';
import type {
  SupplierQuotationData,
  CalculatedLinePrice,
  PricingSummary,
  ZohoSyncConfig,
  ZohoPreviewResponse,
  ZohoExecuteSyncResponse,
} from '../../types/supplierPricing';
import { supplierPricingApi } from '../../services/supplierPricingApi';
import { CompositeItemsSection } from './CompositeItemsSection';

interface ZohoBooksSyncStepProps {
  quotation: SupplierQuotationData;
  calculatedItems: CalculatedLinePrice[];
  pricingSummary: PricingSummary;
  onBackToApproval: () => void;
}

const formatNum = (val: number | null | undefined, curr?: string) => {
  if (val === null || val === undefined || isNaN(val)) return '0.00';
  const isZeroDec = curr === 'IDR';
  return val.toLocaleString(undefined, {
    minimumFractionDigits: isZeroDec ? 0 : 2,
    maximumFractionDigits: 2,
  });
};

export const ZohoBooksSyncStep: React.FC<ZohoBooksSyncStepProps> = ({
  quotation,
  calculatedItems,
  pricingSummary,
  onBackToApproval,
}) => {
  const [zohoConfig, setZohoConfig] = useState<ZohoSyncConfig>({
    organization_id: '741367552',
    environment: 'production',
    sync_mode: 'items_only',
  });

  const [skuQuery, setSkuQuery] = useState('');
  const [previewData, setPreviewData] = useState<ZohoPreviewResponse | null>(null);
  const [isLoadingPreview, setIsLoadingPreview] = useState(false);
  const [isExecutingSync, setIsExecutingSync] = useState(false);
  const [userConfirmed, setUserConfirmed] = useState(false);
  const [confirmedByUser, setConfirmedByUser] = useState('Procurement Lead');
  const [syncResult, setSyncResult] = useState<ZohoExecuteSyncResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [catalogView, setCatalogView] = useState<'both' | 'normal' | 'composite'>('both');

  const targetCurr = pricingSummary.target_currency || 'EUR';

  // Fetch preview categorization
  const loadPreview = async (configToUse: ZohoSyncConfig, queryStr: string) => {
    setIsLoadingPreview(true);
    setErrorMsg(null);
    try {
      const res = await supplierPricingApi.previewZohoSync({
        quotation,
        pricing_summary: pricingSummary,
        calculated_items: calculatedItems,
        zoho_config: configToUse,
        sku_search_query: queryStr,
      });
      setPreviewData(res);
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'Failed to preview Zoho Books synchronization.');
    } finally {
      setIsLoadingPreview(false);
    }
  };

  useEffect(() => {
    loadPreview(zohoConfig, skuQuery);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleConfigChange = <K extends keyof ZohoSyncConfig>(key: K, value: ZohoSyncConfig[K]) => {
    const updated = { ...zohoConfig, [key]: value };
    setZohoConfig(updated);
    loadPreview(updated, skuQuery);
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    loadPreview(zohoConfig, skuQuery);
  };

  const handleExecuteSync = async () => {
    if (!userConfirmed) {
      setErrorMsg('Safety Requirement: Please check the explicit confirmation box before syncing.');
      return;
    }
    if (!previewData) return;

    setIsExecutingSync(true);
    setErrorMsg(null);

    try {
      const allItems = [...previewData.items_to_create, ...previewData.items_to_update];
      const res = await supplierPricingApi.executeZohoSync({
        zoho_config: zohoConfig,
        items: allItems,
        user_confirmed: true,
        confirmed_by_user: confirmedByUser,
        quotation_number: quotation.quote_number || 'UNKNOWN-QUOTE',
        supplier_name: quotation.supplier_name || 'UNKNOWN-SUPPLIER',
        quotation_date: quotation.quote_date,
        source_filename: quotation.source_filename,
        currency: pricingSummary.target_currency || quotation.currency || 'EUR',
        pricing_summary: pricingSummary,
      });

      setSyncResult(res);
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'Zoho Books synchronization failed.');
    } finally {
      setIsExecutingSync(false);
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Top Banner Card */}
      <div className="rounded-3xl border border-[#786446]/15 bg-white/75 backdrop-blur-xl p-6 shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#786446]/10 pb-4">
          <div className="flex items-start space-x-3">
            <button
              onClick={onBackToApproval}
              className="p-2 rounded-xl bg-white border border-[#786446]/20 text-[#716B61] hover:text-[#26231F] hover:bg-[#786446]/5 transition cursor-pointer shrink-0 mt-0.5"
              title="Return to Stage 3 Approval"
            >
              <ArrowLeft className="w-4 h-4" />
            </button>
            <div>
              <div className="flex items-center space-x-2 flex-wrap gap-y-1">
                <span className="text-xs font-semibold uppercase tracking-wider text-[#A66E32]">
                  Stage 4 • ERP Integration
                </span>
                <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-blue-500/15 text-blue-800 border border-blue-500/25 flex items-center space-x-1">
                  <BookOpen className="w-3 h-3 text-blue-600" />
                  <span>Zoho Books Sync • Explicit User Confirmation</span>
                </span>
                <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded-full ${
                  zohoConfig.environment === 'production'
                    ? 'bg-rose-500/15 text-rose-800 border border-rose-500/30'
                    : 'bg-amber-500/15 text-amber-800 border border-amber-500/30'
                }`}>
                  {zohoConfig.environment.toUpperCase()} MODE
                </span>
              </div>
              <h2 className="text-xl font-bold text-[#26231F] mt-1">
                Zoho Books Item Synchronization
              </h2>
              <p className="text-xs text-[#716B61] mt-0.5">
                Automatically maps quotation items into CREATE (new SKU) or UPDATE (existing catalog SKU).
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={() => loadPreview(zohoConfig, skuQuery)}
              disabled={isLoadingPreview}
              className="flex items-center space-x-1.5 text-xs font-semibold px-4 py-2 rounded-xl bg-white border border-[#786446]/20 text-[#716B61] hover:text-[#26231F] transition cursor-pointer shadow-2xs disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isLoadingPreview ? 'animate-spin' : ''}`} />
              <span>Refresh Catalog</span>
            </button>
          </div>
        </div>

        {/* Error / Alert Display */}
        {errorMsg && (
          <div className="p-3.5 rounded-2xl bg-rose-50 border border-rose-200 text-xs text-rose-900 flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
              <span>{errorMsg}</span>
            </div>
            <button onClick={() => setErrorMsg(null)} className="font-bold text-rose-700">✕</button>
          </div>
        )}

        {/* Zoho Connection Configuration Controls */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-1">
          <div className="space-y-1">
            <label className="text-[11px] font-semibold text-[#716B61]">Organization ID</label>
            <input
              type="text"
              value={zohoConfig.organization_id}
              onChange={(e) => handleConfigChange('organization_id', e.target.value)}
              className="w-full text-xs font-mono font-bold bg-white border border-[#786446]/20 rounded-xl px-3 py-1.5 text-[#26231F] focus:outline-none focus:border-[#C98B4A]"
            />
          </div>

          <div className="space-y-1">
            <label className="text-[11px] font-semibold text-[#716B61]">Environment</label>
            <select
              value={zohoConfig.environment}
              onChange={(e) => handleConfigChange('environment', e.target.value as any)}
              className="w-full text-xs font-semibold bg-white border border-[#786446]/20 rounded-xl px-2.5 py-1.5 text-[#26231F] focus:outline-none focus:border-[#C98B4A]"
            >
              <option value="sandbox">Sandbox (Test Instance)</option>
              <option value="production">Production (Live ERP)</option>
            </select>
          </div>

          <div className="space-y-1">
            <label className="text-[11px] font-semibold text-[#716B61]">Sync Scope</label>
            <select
              value={zohoConfig.sync_mode}
              onChange={(e) => handleConfigChange('sync_mode', e.target.value as any)}
              className="w-full text-xs font-semibold bg-white border border-[#786446]/20 rounded-xl px-2.5 py-1.5 text-[#26231F] focus:outline-none focus:border-[#C98B4A]"
            >
              <option value="items_only">Items Master Only (Selling & Purchase Rates)</option>
              <option value="items_and_po">Items + Draft Purchase Order</option>
            </select>
          </div>
        </div>

        {/* Search Bar */}
        <form onSubmit={handleSearchSubmit} className="pt-2 flex items-center space-x-2">
          <div className="relative flex-1">
            <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-[#716B61]" />
            <input
              type="text"
              value={skuQuery}
              onChange={(e) => setSkuQuery(e.target.value)}
              placeholder="Search by Part Number or Description to filter..."
              className="w-full text-xs bg-white border border-[#786446]/20 rounded-xl pl-9 pr-3 py-2 text-[#26231F] focus:outline-none focus:border-[#C98B4A]"
            />
          </div>
          <button
            type="submit"
            className="px-4 py-2 rounded-xl bg-[#786446]/10 hover:bg-[#786446]/20 text-[#26231F] font-semibold text-xs transition cursor-pointer"
          >
            Filter
          </button>
        </form>
      </div>

      {/* Sync Execution Results Banner */}
      {syncResult && (
        <div className="rounded-3xl border border-emerald-500/30 bg-emerald-500/10 backdrop-blur-xl p-6 shadow-xs space-y-3">
          <div className="flex items-center space-x-2">
            <CheckCircle2 className="w-5 h-5 text-emerald-600" />
            <h3 className="text-base font-bold text-emerald-950">Zoho Books Synchronization Succeeded</h3>
          </div>
          <p className="text-xs text-emerald-900">
            {syncResult.message} (Logged at {syncResult.synced_at}).
          </p>
          <div className="rounded-xl bg-white/80 border border-emerald-500/20 p-3 max-h-36 overflow-y-auto space-y-1">
            {syncResult.audit_log.map((log, idx) => (
              <div key={idx} className="font-mono text-[11px] text-[#26231F]">
                {log}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Sub-Navigation: Normal Items vs Composite Items */}
      <div className="flex flex-wrap items-center gap-2 border-b border-[#786446]/15 pb-2">
        <button
          type="button"
          onClick={() => setCatalogView('normal')}
          className={`px-4 py-2 rounded-xl text-xs font-bold transition flex items-center space-x-2 cursor-pointer ${
            catalogView === 'normal'
              ? 'bg-[#26231F] text-white shadow-xs'
              : 'bg-white/80 text-[#716B61] hover:text-[#26231F] border border-[#786446]/20'
          }`}
        >
          <BookOpen className="w-3.5 h-3.5" />
          <span>Normal Items ({previewData?.total_items || 0})</span>
        </button>

        <button
          type="button"
          onClick={() => setCatalogView('composite')}
          className={`px-4 py-2 rounded-xl text-xs font-bold transition flex items-center space-x-2 cursor-pointer ${
            catalogView === 'composite'
              ? 'bg-[#26231F] text-white shadow-xs'
              : 'bg-white/80 text-[#716B61] hover:text-[#26231F] border border-[#786446]/20'
          }`}
        >
          <Layers className="w-3.5 h-3.5 text-[#C98B4A]" />
          <span>Composite Items</span>
        </button>

        <button
          type="button"
          onClick={() => setCatalogView('both')}
          className={`px-4 py-2 rounded-xl text-xs font-bold transition flex items-center space-x-2 cursor-pointer ${
            catalogView === 'both'
              ? 'bg-[#26231F] text-white shadow-xs'
              : 'bg-white/80 text-[#716B61] hover:text-[#26231F] border border-[#786446]/20'
          }`}
        >
          <span>View Both (Stacked)</span>
        </button>
      </div>

      {/* Action Breakdown Cards & Tables for Normal Items */}
      {(catalogView === 'normal' || catalogView === 'both') && previewData && (
        <div className="space-y-6">
          {/* Summary counters */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="p-4 rounded-2xl bg-white/70 border border-[#786446]/15 shadow-2xs">
              <span className="text-[11px] font-semibold text-[#716B61] uppercase tracking-wider">Total SKUs in Scope</span>
              <div className="text-2xl font-black font-mono text-[#26231F] mt-1">{previewData.total_items}</div>
              <p className="text-[11px] text-[#716B61] mt-0.5">Line items ready for Zoho Books</p>
            </div>
            <div className="p-4 rounded-2xl bg-blue-500/10 border border-blue-500/20 shadow-2xs">
              <span className="text-[11px] font-semibold text-blue-800 uppercase tracking-wider">Existing SKUs (UPDATE)</span>
              <div className="text-2xl font-black font-mono text-blue-900 mt-1">{previewData.matched_existing_count}</div>
              <p className="text-[11px] text-blue-700 mt-0.5">Rates will be updated in catalog</p>
            </div>
            <div className="p-4 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 shadow-2xs">
              <span className="text-[11px] font-semibold text-emerald-800 uppercase tracking-wider">New SKUs (CREATE)</span>
              <div className="text-2xl font-black font-mono text-emerald-900 mt-1">{previewData.new_sku_count}</div>
              <p className="text-[11px] text-emerald-700 mt-0.5">New item records will be created</p>
            </div>
          </div>

          {/* Section 1: Items to UPDATE */}
          {previewData.items_to_update.length > 0 && (
            <div className="rounded-3xl border border-blue-500/20 bg-white/75 backdrop-blur-xl p-6 shadow-xs space-y-4">
              <div className="flex items-center justify-between border-b border-[#786446]/10 pb-3">
                <div className="flex items-center space-x-2">
                  <span className="text-xs font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-900">
                    UPDATE Action ({previewData.items_to_update.length})
                  </span>
                  <h3 className="text-sm font-bold text-[#26231F]">Existing SKUs Found in Zoho Catalog</h3>
                </div>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-[#786446]/15 bg-[#786446]/5 text-[#716B61]">
                      <th className="py-2.5 px-3 font-bold">Part Number / SKU</th>
                      <th className="py-2.5 px-3 font-bold">Zoho Item ID</th>
                      <th className="py-2.5 px-3 font-bold">Description</th>
                      <th className="py-2.5 px-3 font-bold text-right">Selling Rate ({targetCurr})</th>
                      <th className="py-2.5 px-3 font-bold text-right">Cost Price ({targetCurr})</th>
                      <th className="py-2.5 px-3 font-bold">Audit Note</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#786446]/10">
                    {previewData.items_to_update.map((it, idx) => (
                      <tr key={idx} className="hover:bg-[#786446]/5">
                        <td className="py-2.5 px-3 font-mono font-bold text-blue-900">{it.part_number}</td>
                        <td className="py-2.5 px-3 font-mono text-xs text-[#716B61]">{it.existing_item_id}</td>
                        <td className="py-2.5 px-3 text-[#26231F]">{it.description}</td>
                        <td className="py-2.5 px-3 text-right font-mono font-bold text-emerald-800">
                          {targetCurr} {formatNum(it.rate, targetCurr)}
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono text-[#716B61]">
                          {targetCurr} {formatNum(it.purchase_rate, targetCurr)}
                        </td>
                        <td className="py-2.5 px-3 text-[11px] text-[#716B61]">{it.notes}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Section 2: Items to CREATE */}
          {previewData.items_to_create.length > 0 && (
            <div className="rounded-3xl border border-emerald-500/20 bg-white/75 backdrop-blur-xl p-6 shadow-xs space-y-4">
              <div className="flex items-center justify-between border-b border-[#786446]/10 pb-3">
                <div className="flex items-center space-x-2">
                  <span className="text-xs font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-900">
                    CREATE Action ({previewData.items_to_create.length})
                  </span>
                  <h3 className="text-sm font-bold text-[#26231F]">New SKUs to Register in Zoho Books</h3>
                </div>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-[#786446]/15 bg-[#786446]/5 text-[#716B61]">
                      <th className="py-2.5 px-3 font-bold">Part Number / SKU</th>
                      <th className="py-2.5 px-3 font-bold">Description</th>
                      <th className="py-2.5 px-3 font-bold text-right">Selling Rate ({targetCurr})</th>
                      <th className="py-2.5 px-3 font-bold text-right">Cost Price ({targetCurr})</th>
                      <th className="py-2.5 px-3 font-bold">Planned Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#786446]/10">
                    {previewData.items_to_create.map((it, idx) => (
                      <tr key={idx} className="hover:bg-[#786446]/5">
                        <td className="py-2.5 px-3 font-mono font-bold text-emerald-900">{it.part_number}</td>
                        <td className="py-2.5 px-3 text-[#26231F]">{it.description}</td>
                        <td className="py-2.5 px-3 text-right font-mono font-bold text-emerald-800">
                          {targetCurr} {formatNum(it.rate, targetCurr)}
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono text-[#716B61]">
                          {targetCurr} {formatNum(it.purchase_rate, targetCurr)}
                        </td>
                        <td className="py-2.5 px-3 text-[11px] text-[#716B61]">{it.notes}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* CRITICAL SAFETY GUARDRAIL & CONFIRMATION BOX */}
          <div className="rounded-3xl border-2 border-[#C98B4A]/40 bg-gradient-to-br from-white to-[#C98B4A]/5 p-6 shadow-sm space-y-4">
            <div className="flex items-start space-x-3">
              <ShieldAlert className="w-6 h-6 text-[#C98B4A] shrink-0 mt-0.5" />
              <div>
                <h3 className="text-sm font-bold text-[#26231F]">
                  Required Confirmation: Explicit Authorization for Zoho Books Sync
                </h3>
                <p className="text-xs text-[#716B61] mt-0.5">
                  Never silently modify ERP production data. You must review the actions above and explicitly check the authorization checkbox below.
                </p>
              </div>
            </div>

            <div className="p-4 rounded-2xl bg-white border border-[#786446]/20 space-y-3">
              <label className="flex items-start space-x-3 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={userConfirmed}
                  onChange={(e) => setUserConfirmed(e.target.checked)}
                  className="w-4 h-4 text-emerald-600 rounded mt-0.5 focus:ring-emerald-500"
                />
                <span className="text-xs text-[#26231F] font-semibold leading-relaxed">
                  I have reviewed all {previewData.total_items} items, their final selling rates ({targetCurr}), and confirm synchronization to Zoho Books ({zohoConfig.environment} environment, Org ID: {zohoConfig.organization_id}).
                </span>
              </label>

              <div className="pt-2 border-t border-[#786446]/10 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="flex items-center space-x-2 text-xs">
                  <span className="text-[#716B61] font-medium">Authorized by:</span>
                  <input
                    type="text"
                    value={confirmedByUser}
                    onChange={(e) => setConfirmedByUser(e.target.value)}
                    className="text-xs font-semibold bg-white border border-[#786446]/20 rounded-lg px-2 py-1 text-[#26231F]"
                  />
                </div>

                <button
                  type="button"
                  onClick={handleExecuteSync}
                  disabled={!userConfirmed || isExecutingSync}
                  className={`flex items-center space-x-2 text-xs font-bold px-6 py-2.5 rounded-xl transition cursor-pointer shadow-xs ${
                    userConfirmed
                      ? 'bg-emerald-700 text-white hover:bg-emerald-800'
                      : 'bg-[#786446]/20 text-[#716B61] cursor-not-allowed opacity-70'
                  }`}
                >
                  <Send className={`w-3.5 h-3.5 ${isExecutingSync ? 'animate-spin' : ''}`} />
                  <span>{isExecutingSync ? 'Writing to Zoho...' : 'Execute Zoho Books Sync'}</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Composite Items Section */}
      {(catalogView === 'composite' || catalogView === 'both') && (
        <CompositeItemsSection
          organizationId={zohoConfig.organization_id}
          quotation={quotation}
          calculatedItems={calculatedItems}
        />
      )}
    </div>
  );
};
