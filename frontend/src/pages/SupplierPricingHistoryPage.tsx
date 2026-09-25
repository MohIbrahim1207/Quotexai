import React, { useState, useEffect, useCallback } from 'react';
import {
  History,
  Search,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Calendar,
  ChevronLeft,
  ChevronRight,
  Eye,
  X,
  FileText,
  Building2,
  Package,
  RefreshCw,
  RotateCcw,
  Layers,
} from 'lucide-react';
import { supplierPricingApi } from '../services/supplierPricingApi';
import type {
  SupplierPricingHistorySummary,
  SupplierPricingHistoryDetail,
  SupplierPricingHistoryStats,
  HistoryFilterParams,
} from '../types/supplierPricing';

export const SupplierPricingHistoryPage: React.FC = () => {
  // State for data
  const [records, setRecords] = useState<SupplierPricingHistorySummary[]>([]);
  const [stats, setStats] = useState<SupplierPricingHistoryStats>({
    total_quotations: 0,
    successfully_synced: 0,
    partially_failed: 0,
    failed: 0,
  });
  const [totalPages, setTotalPages] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Search & Filter State
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [actionFilter, setActionFilter] = useState<string>('all');
  const [startDate, setStartDate] = useState<string>('');
  const [endDate, setEndDate] = useState<string>('');

  // Selected Detail Modal State
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detailData, setDetailData] = useState<SupplierPricingHistoryDetail | null>(null);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  // Debounce search input
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearch(searchQuery.trim());
      setCurrentPage(1);
    }, 350);
    return () => clearTimeout(handler);
  }, [searchQuery]);

  // Fetch History List
  const fetchHistory = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const params: HistoryFilterParams = {
        page: currentPage,
        page_size: 10,
      };
      if (debouncedSearch) params.search = debouncedSearch;
      if (statusFilter !== 'all') params.status = statusFilter;
      if (actionFilter !== 'all') params.action = actionFilter;
      if (startDate) params.start_date = startDate;
      if (endDate) params.end_date = endDate;

      const res = await supplierPricingApi.getHistory(params);
      setRecords(res.records || []);
      setTotalPages(res.total_pages || 1);
      setTotalCount(res.total_count || 0);
      setStats(
        res.summary_stats || {
          total_quotations: 0,
          successfully_synced: 0,
          partially_failed: 0,
          failed: 0,
        }
      );
    } catch (err: any) {
      setErrorMessage(
        err.response?.data?.detail || 'Failed to load supplier pricing history audit records.'
      );
    } finally {
      setIsLoading(false);
    }
  }, [currentPage, debouncedSearch, statusFilter, actionFilter, startDate, endDate]);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  // Fetch Single Record Detail
  const handleOpenDetail = async (id: string) => {
    setSelectedId(id);
    setIsLoadingDetail(true);
    setDetailError(null);
    try {
      const res = await supplierPricingApi.getHistoryDetail(id);
      setDetailData(res);
    } catch (err: any) {
      setDetailError(err.response?.data?.detail || 'Failed to load history audit detail.');
    } finally {
      setIsLoadingDetail(false);
    }
  };

  const handleCloseDetail = () => {
    setSelectedId(null);
    setDetailData(null);
    setDetailError(null);
  };

  const handleResetFilters = () => {
    setSearchQuery('');
    setDebouncedSearch('');
    setStatusFilter('all');
    setActionFilter('all');
    setStartDate('');
    setEndDate('');
    setCurrentPage(1);
  };

  const formatNumber = (val: number | null | undefined, curr = 'EUR') => {
    if (val === null || val === undefined || isNaN(val)) return '0.00';
    return val.toLocaleString(undefined, {
      minimumFractionDigits: curr === 'IDR' ? 0 : 2,
      maximumFractionDigits: 2,
    });
  };

  const formatDateTime = (isoStr: string) => {
    try {
      const d = new Date(isoStr);
      if (isNaN(d.getTime())) return isoStr;
      return d.toLocaleString(undefined, {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return isoStr;
    }
  };

  const getStatusBadge = (status: string) => {
    const s = status.toUpperCase();
    if (s === 'SUCCESS' || s === 'APPROVED') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200/60">
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
          Successful
        </span>
      );
    }
    if (s === 'PARTIAL') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-100 text-amber-800 border border-amber-200/60">
          <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
          Partial
        </span>
      );
    }
    if (s === 'FAILED') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-100 text-rose-800 border border-rose-200/60">
          <XCircle className="w-3.5 h-3.5 text-rose-600" />
          Failed
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-stone-100 text-stone-700 border border-stone-200">
        <FileText className="w-3.5 h-3.5 text-stone-500" />
        {status}
      </span>
    );
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <span className="p-2 rounded-xl bg-amber-500/10 border border-amber-500/20 text-[#A66E32]">
              <History className="w-5 h-5" />
            </span>
            <div>
              <h1 className="text-xl sm:text-2xl font-bold text-[#26231F] tracking-tight">
                Quotation & Zoho Sync Audit History
              </h1>
              <p className="text-xs sm:text-sm text-[#716B61]">
                Persistent, read-only audit trail of processed supplier quotes and real Zoho Books ERP sync records.
              </p>
            </div>
          </div>
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={() => fetchHistory()}
            disabled={isLoading}
            className="flex items-center space-x-2 px-3.5 py-2 text-xs font-semibold rounded-xl bg-white/80 hover:bg-white border border-[#786446]/20 shadow-2xs hover:shadow-xs transition text-[#26231F] cursor-pointer disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-[#716B61] ${isLoading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* 1. Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Processed */}
        <div className="rounded-2xl border border-[#786446]/15 bg-white/75 backdrop-blur-md p-5 shadow-xs flex items-center justify-between">
          <div>
            <p className="text-xs font-medium uppercase tracking-wider text-[#716B61]">
              Total Quotations Processed
            </p>
            <p className="text-2xl sm:text-3xl font-bold text-[#26231F] mt-1">
              {stats.total_quotations}
            </p>
          </div>
          <div className="w-12 h-12 rounded-2xl bg-[#786446]/10 flex items-center justify-center text-[#26231F]">
            <FileText className="w-6 h-6 text-[#716B61]" />
          </div>
        </div>

        {/* Successfully Synced */}
        <div className="rounded-2xl border border-emerald-200/60 bg-white/75 backdrop-blur-md p-5 shadow-xs flex items-center justify-between">
          <div>
            <p className="text-xs font-medium uppercase tracking-wider text-emerald-700">
              Successfully Synced
            </p>
            <p className="text-2xl sm:text-3xl font-bold text-emerald-800 mt-1">
              {stats.successfully_synced}
            </p>
          </div>
          <div className="w-12 h-12 rounded-2xl bg-emerald-500/10 flex items-center justify-center text-emerald-600">
            <CheckCircle2 className="w-6 h-6" />
          </div>
        </div>

        {/* Partially Failed */}
        <div className="rounded-2xl border border-amber-200/60 bg-white/75 backdrop-blur-md p-5 shadow-xs flex items-center justify-between">
          <div>
            <p className="text-xs font-medium uppercase tracking-wider text-amber-700">
              Partially Failed
            </p>
            <p className="text-2xl sm:text-3xl font-bold text-amber-800 mt-1">
              {stats.partially_failed}
            </p>
          </div>
          <div className="w-12 h-12 rounded-2xl bg-amber-500/10 flex items-center justify-center text-amber-600">
            <AlertTriangle className="w-6 h-6" />
          </div>
        </div>

        {/* Failed */}
        <div className="rounded-2xl border border-rose-200/60 bg-white/75 backdrop-blur-md p-5 shadow-xs flex items-center justify-between">
          <div>
            <p className="text-xs font-medium uppercase tracking-wider text-rose-700">
              Failed
            </p>
            <p className="text-2xl sm:text-3xl font-bold text-rose-800 mt-1">
              {stats.failed}
            </p>
          </div>
          <div className="w-12 h-12 rounded-2xl bg-rose-500/10 flex items-center justify-center text-rose-600">
            <XCircle className="w-6 h-6" />
          </div>
        </div>
      </div>

      {/* 2 & 3. Search and Filters Bar */}
      <div className="rounded-2xl border border-[#786446]/15 bg-white/80 backdrop-blur-xl p-4 sm:p-5 shadow-xs space-y-4">
        <div className="flex flex-col md:flex-row gap-3 items-stretch md:items-center justify-between">
          {/* Search Input: quotation number, supplier, SKU / part number */}
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-[#716B61] absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by quotation #, supplier name, or SKU / part number..."
              className="w-full pl-10 pr-4 py-2 text-xs sm:text-sm rounded-xl border border-[#786446]/20 bg-white/90 text-[#26231F] placeholder-[#716B61]/60 focus:outline-none focus:ring-2 focus:ring-[#C98B4A]/30 focus:border-[#C98B4A]"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-[#716B61] hover:text-[#26231F]"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          {/* Quick Filter Pill: Status */}
          <div className="flex items-center gap-1.5 flex-wrap">
            <div className="flex items-center gap-1 bg-[#786446]/5 p-1 rounded-xl border border-[#786446]/15 text-xs">
              <span className="text-[10px] font-bold uppercase text-[#716B61] px-2">Status:</span>
              {(['all', 'SUCCESS', 'PARTIAL', 'FAILED'] as const).map((st) => (
                <button
                  key={st}
                  type="button"
                  onClick={() => {
                    setStatusFilter(st);
                    setCurrentPage(1);
                  }}
                  className={`px-2.5 py-1 rounded-lg font-medium transition cursor-pointer ${
                    statusFilter === st
                      ? 'bg-white text-[#26231F] shadow-2xs font-semibold'
                      : 'text-[#716B61] hover:text-[#26231F]'
                  }`}
                >
                  {st === 'all'
                    ? 'All'
                    : st === 'SUCCESS'
                    ? 'Successful'
                    : st === 'PARTIAL'
                    ? 'Partial'
                    : 'Failed'}
                </button>
              ))}
            </div>

            {/* Action Filter: All / CREATE / UPDATE */}
            <div className="flex items-center gap-1 bg-[#786446]/5 p-1 rounded-xl border border-[#786446]/15 text-xs">
              <span className="text-[10px] font-bold uppercase text-[#716B61] px-2">Action:</span>
              {(['all', 'CREATE', 'UPDATE'] as const).map((act) => (
                <button
                  key={act}
                  type="button"
                  onClick={() => {
                    setActionFilter(act);
                    setCurrentPage(1);
                  }}
                  className={`px-2.5 py-1 rounded-lg font-medium transition cursor-pointer ${
                    actionFilter === act
                      ? 'bg-white text-[#26231F] shadow-2xs font-semibold'
                      : 'text-[#716B61] hover:text-[#26231F]'
                  }`}
                >
                  {act === 'all' ? 'All' : act}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Date Range & Reset Row */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-t border-[#786446]/10 pt-3 text-xs">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[#716B61] font-medium flex items-center gap-1">
              <Calendar className="w-3.5 h-3.5" /> Date Range:
            </span>
            <input
              type="date"
              value={startDate}
              onChange={(e) => {
                setStartDate(e.target.value);
                setCurrentPage(1);
              }}
              className="px-2.5 py-1 rounded-lg border border-[#786446]/20 bg-white text-[#26231F] focus:outline-none focus:ring-1 focus:ring-[#C98B4A]"
            />
            <span className="text-[#716B61]">to</span>
            <input
              type="date"
              value={endDate}
              onChange={(e) => {
                setEndDate(e.target.value);
                setCurrentPage(1);
              }}
              className="px-2.5 py-1 rounded-lg border border-[#786446]/20 bg-white text-[#26231F] focus:outline-none focus:ring-1 focus:ring-[#C98B4A]"
            />
            {(startDate || endDate || statusFilter !== 'all' || actionFilter !== 'all' || searchQuery) && (
              <button
                type="button"
                onClick={handleResetFilters}
                className="flex items-center gap-1 text-xs text-[#A66E32] hover:text-[#786446] font-medium ml-2 cursor-pointer"
              >
                <RotateCcw className="w-3 h-3" /> Reset Filters
              </button>
            )}
          </div>

          <div className="text-xs text-[#716B61]">
            Showing {records.length} of {totalCount} record{totalCount === 1 ? '' : 's'}
          </div>
        </div>
      </div>

      {/* Error Message */}
      {errorMessage && (
        <div className="rounded-2xl bg-rose-50 border border-rose-200 p-4 flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
          <div className="text-xs sm:text-sm text-rose-800">
            <p className="font-semibold">Unable to load audit history</p>
            <p>{errorMessage}</p>
          </div>
        </div>
      )}

      {/* 4. History Table */}
      <div className="rounded-2xl border border-[#786446]/15 bg-white/80 backdrop-blur-xl shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs sm:text-sm">
            <thead>
              <tr className="border-b border-[#786446]/10 bg-[#786446]/5 text-[#716B61] text-[11px] font-semibold uppercase tracking-wider">
                <th className="py-3 px-4">Date / Time</th>
                <th className="py-3 px-4">Quotation No.</th>
                <th className="py-3 px-4">Supplier</th>
                <th className="py-3 px-4 text-center">Number of SKUs</th>
                <th className="py-3 px-4 text-center">Created</th>
                <th className="py-3 px-4 text-center">Updated</th>
                <th className="py-3 px-4 text-center">Failed</th>
                <th className="py-3 px-4">Overall Status</th>
                <th className="py-3 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#786446]/10">
              {isLoading ? (
                <tr>
                  <td colSpan={9} className="py-12 text-center text-[#716B61]">
                    <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-[#C98B4A]" />
                    <p className="text-xs">Loading history records...</p>
                  </td>
                </tr>
              ) : records.length === 0 ? (
                <tr>
                  <td colSpan={9} className="py-12 text-center text-[#716B61]">
                    <History className="w-8 h-8 mx-auto mb-2 text-[#786446]/30" />
                    <p className="text-sm font-semibold text-[#26231F]">No History Records Found</p>
                    <p className="text-xs mt-1 text-[#716B61]">
                      {searchQuery || statusFilter !== 'all' || actionFilter !== 'all' || startDate || endDate
                        ? 'Try clearing or modifying your search and filter criteria.'
                        : 'Processed quotations and Zoho Books sync executions will be permanently stored here.'}
                    </p>
                  </td>
                </tr>
              ) : (
                records.map((rec) => (
                  <tr
                    key={rec.id}
                    onClick={() => handleOpenDetail(rec.id)}
                    className="hover:bg-[#786446]/5 transition cursor-pointer group"
                  >
                    <td className="py-3.5 px-4 font-mono text-xs text-[#716B61] whitespace-nowrap">
                      {formatDateTime(rec.processed_at)}
                    </td>
                    <td className="py-3.5 px-4 font-semibold text-[#26231F] whitespace-nowrap">
                      <span className="font-mono px-2 py-0.5 rounded bg-white border border-[#786446]/20">
                        {rec.quotation_number}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-[#26231F] font-medium whitespace-nowrap">
                      <div className="flex items-center gap-1.5">
                        <Building2 className="w-3.5 h-3.5 text-[#716B61]" />
                        <span>{rec.supplier_name}</span>
                      </div>
                    </td>
                    <td className="py-3.5 px-4 text-center font-mono font-medium text-[#26231F]">
                      {rec.total_items}
                    </td>
                    <td className="py-3.5 px-4 text-center">
                      <span
                        className={`inline-block px-2 py-0.5 rounded text-xs font-mono font-semibold ${
                          rec.created_count > 0
                            ? 'bg-emerald-100 text-emerald-800'
                            : 'bg-stone-100 text-stone-500'
                        }`}
                      >
                        {rec.created_count}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-center">
                      <span
                        className={`inline-block px-2 py-0.5 rounded text-xs font-mono font-semibold ${
                          rec.updated_count > 0
                            ? 'bg-blue-100 text-blue-800'
                            : 'bg-stone-100 text-stone-500'
                        }`}
                      >
                        {rec.updated_count}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-center">
                      <span
                        className={`inline-block px-2 py-0.5 rounded text-xs font-mono font-semibold ${
                          rec.failed_count > 0
                            ? 'bg-rose-100 text-rose-800'
                            : 'bg-stone-100 text-stone-500'
                        }`}
                      >
                        {rec.failed_count}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 whitespace-nowrap">
                      {getStatusBadge(rec.overall_status)}
                    </td>
                    <td className="py-3.5 px-4 text-right whitespace-nowrap">
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleOpenDetail(rec.id);
                        }}
                        className="inline-flex items-center gap-1 px-3 py-1.5 rounded-xl bg-white border border-[#786446]/20 text-xs font-semibold text-[#26231F] hover:bg-[#786446]/10 transition shadow-2xs group-hover:border-[#786446]/40 cursor-pointer"
                      >
                        <Eye className="w-3.5 h-3.5 text-[#C98B4A]" />
                        <span>View Details</span>
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Footer */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-[#786446]/10 bg-white/50 text-xs">
            <div className="text-[#716B61]">
              Page <span className="font-semibold text-[#26231F]">{currentPage}</span> of{' '}
              <span className="font-semibold text-[#26231F]">{totalPages}</span>
            </div>
            <div className="flex items-center space-x-1.5">
              <button
                type="button"
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                disabled={currentPage <= 1 || isLoading}
                className="p-1.5 rounded-lg border border-[#786446]/20 bg-white text-[#26231F] hover:bg-[#786446]/5 disabled:opacity-40 cursor-pointer disabled:cursor-not-allowed"
                title="Previous Page"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <button
                type="button"
                onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                disabled={currentPage >= totalPages || isLoading}
                className="p-1.5 rounded-lg border border-[#786446]/20 bg-white text-[#26231F] hover:bg-[#786446]/5 disabled:opacity-40 cursor-pointer disabled:cursor-not-allowed"
                title="Next Page"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* 5 & 6. Read-only Detail Modal View */}
      {selectedId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-black/40 backdrop-blur-xs animate-in fade-in duration-150">
          <div className="bg-[#FBF9F5] border border-[#786446]/20 rounded-3xl shadow-2xl max-w-5xl w-full max-h-[92vh] flex flex-col overflow-hidden">
            {/* Modal Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-[#786446]/15 bg-white/80">
              <div className="flex items-center space-x-3">
                <div className="w-9 h-9 rounded-xl bg-[#26231F] text-white flex items-center justify-center">
                  <FileText className="w-4 h-4 text-[#F5F1E8]" />
                </div>
                <div>
                  <div className="flex items-center space-x-2">
                    <h2 className="text-base sm:text-lg font-bold text-[#26231F]">
                      Quotation Audit Detail: {detailData?.quotation_number || '...'}
                    </h2>
                    <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-stone-100 text-stone-600 border border-stone-200">
                      Read-Only Audit Record
                    </span>
                  </div>
                  <p className="text-xs text-[#716B61]">
                    ID: <span className="font-mono">{selectedId}</span>
                  </p>
                </div>
              </div>

              <div className="flex items-center space-x-2">
                <button
                  type="button"
                  onClick={handleCloseDetail}
                  className="p-2 rounded-xl bg-white border border-[#786446]/20 text-[#716B61] hover:text-[#26231F] hover:bg-[#786446]/5 transition cursor-pointer"
                  title="Close Detail Modal"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Modal Body */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              {isLoadingDetail ? (
                <div className="py-20 text-center text-[#716B61]">
                  <RefreshCw className="w-8 h-8 animate-spin mx-auto mb-2 text-[#C98B4A]" />
                  <p className="text-sm">Fetching complete audit information...</p>
                </div>
              ) : detailError ? (
                <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs">
                  {detailError}
                </div>
              ) : detailData ? (
                <>
                  {/* Section A: Quotation Information */}
                  <div className="rounded-2xl border border-[#786446]/15 bg-white/80 p-5 shadow-xs space-y-3">
                    <div className="flex items-center justify-between border-b border-[#786446]/10 pb-2.5">
                      <h3 className="text-xs font-bold uppercase tracking-wider text-[#A66E32] flex items-center gap-1.5">
                        <FileText className="w-4 h-4" /> Quotation Information
                      </h3>
                      <div>{getStatusBadge(detailData.overall_status)}</div>
                    </div>

                    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4 text-xs">
                      <div>
                        <span className="text-[#716B61] block text-[11px]">Quotation Number</span>
                        <span className="font-mono font-bold text-[#26231F] text-sm">
                          {detailData.quotation_number}
                        </span>
                      </div>
                      <div>
                        <span className="text-[#716B61] block text-[11px]">Supplier</span>
                        <span className="font-semibold text-[#26231F] text-sm">
                          {detailData.supplier_name}
                        </span>
                      </div>
                      <div>
                        <span className="text-[#716B61] block text-[11px]">Quotation Date</span>
                        <span className="font-medium text-[#26231F]">
                          {detailData.quotation_date || 'N/A'}
                        </span>
                      </div>
                      <div>
                        <span className="text-[#716B61] block text-[11px]">Upload Filename</span>
                        <span className="font-medium text-[#26231F] truncate block" title={detailData.source_filename || 'N/A'}>
                          {detailData.source_filename || 'N/A'}
                        </span>
                      </div>
                      <div>
                        <span className="text-[#716B61] block text-[11px]">Processed Timestamp</span>
                        <span className="font-mono text-[#26231F]">
                          {formatDateTime(detailData.processed_at)}
                        </span>
                      </div>
                      <div>
                        <span className="text-[#716B61] block text-[11px]">Processing User</span>
                        <span className="font-medium text-[#26231F]">
                          {detailData.processed_by || 'Procurement User'}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Section B: Pricing Information */}
                  <div className="rounded-2xl border border-[#786446]/15 bg-white/80 p-5 shadow-xs space-y-3">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-[#A66E32] flex items-center gap-1.5 border-b border-[#786446]/10 pb-2.5">
                      <Layers className="w-4 h-4" /> Pricing Information & Economics
                    </h3>

                    <div className="grid grid-cols-2 sm:grid-cols-5 gap-4 text-xs">
                      <div>
                        <span className="text-[#716B61] block text-[11px]">Currency</span>
                        <span className="font-mono font-bold text-[#26231F] text-sm">
                          {detailData.currency}
                        </span>
                      </div>
                      <div>
                        <span className="text-[#716B61] block text-[11px]">Supplier Net Price</span>
                        <span className="font-mono font-semibold text-[#26231F] text-sm">
                          {formatNumber(detailData.total_supplier_net, detailData.currency)}
                        </span>
                      </div>
                      <div>
                        <span className="text-[#716B61] block text-[11px]">Total Landed Cost</span>
                        <span className="font-mono font-semibold text-[#26231F] text-sm">
                          {formatNumber(detailData.total_landed_cost, detailData.currency)}
                        </span>
                      </div>
                      <div>
                        <span className="text-[#716B61] block text-[11px]">Total Selling Price</span>
                        <span className="font-mono font-bold text-[#C98B4A] text-sm">
                          {formatNumber(detailData.total_selling_price, detailData.currency)}
                        </span>
                      </div>
                      <div>
                        <span className="text-[#716B61] block text-[11px]">Margin % / Gross Profit</span>
                        <span className="font-mono font-semibold text-emerald-700 text-sm">
                          {(detailData.overall_margin_percent || 0).toFixed(1)}% ({formatNumber(detailData.total_gross_profit, detailData.currency)})
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Section C: Zoho Books Synchronization */}
                  <div className="rounded-2xl border border-[#786446]/15 bg-white/80 p-5 shadow-xs space-y-4">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[#786446]/10 pb-2.5">
                      <h3 className="text-xs font-bold uppercase tracking-wider text-[#A66E32] flex items-center gap-1.5">
                        <Package className="w-4 h-4" /> Zoho Books Synchronization Details
                      </h3>
                      <div className="flex items-center gap-3 text-xs text-[#716B61]">
                        <span>
                          Org ID: <strong className="font-mono text-[#26231F]">{detailData.zoho_organization_id || '741367552'}</strong>
                        </span>
                        <span>
                          Environment: <strong className="font-mono text-[#26231F]">{detailData.zoho_environment || 'production'}</strong>
                        </span>
                      </div>
                    </div>

                    {detailData.sync_message && (
                      <p className="text-xs bg-[#786446]/5 p-2.5 rounded-xl text-[#716B61] border border-[#786446]/10">
                        {detailData.sync_message}
                      </p>
                    )}

                    {/* Items Table */}
                    <div className="overflow-x-auto rounded-xl border border-[#786446]/15">
                      <table className="w-full text-left border-collapse text-xs">
                        <thead>
                          <tr className="bg-[#786446]/5 text-[#716B61] text-[10px] font-semibold uppercase tracking-wider border-b border-[#786446]/10">
                            <th className="py-2.5 px-3">#</th>
                            <th className="py-2.5 px-3">SKU / Part Number</th>
                            <th className="py-2.5 px-3">Description</th>
                            <th className="py-2.5 px-3">Action</th>
                            <th className="py-2.5 px-3">Zoho Item ID</th>
                            <th className="py-2.5 px-3 text-right">Purchase Rate</th>
                            <th className="py-2.5 px-3 text-right">Selling Rate</th>
                            <th className="py-2.5 px-3">Sync Status</th>
                            <th className="py-2.5 px-3">Zoho Response / Message</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-[#786446]/10">
                          {detailData.items.length === 0 ? (
                            <tr>
                              <td colSpan={9} className="py-6 text-center text-[#716B61]">
                                No item breakdown recorded for this quotation.
                              </td>
                            </tr>
                          ) : (
                            detailData.items.map((it) => (
                              <tr key={it.id} className="hover:bg-[#786446]/5">
                                <td className="py-2.5 px-3 font-mono text-[#716B61]">{it.line_number}</td>
                                <td className="py-2.5 px-3 font-mono font-bold text-[#26231F] whitespace-nowrap">
                                  {it.sku}
                                </td>
                                <td className="py-2.5 px-3 text-[#716B61] max-w-[200px] truncate" title={it.description || ''}>
                                  {it.description || '-'}
                                </td>
                                <td className="py-2.5 px-3 whitespace-nowrap">
                                  <span
                                    className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                      it.action === 'CREATE'
                                        ? 'bg-emerald-100 text-emerald-800'
                                        : 'bg-blue-100 text-blue-800'
                                    }`}
                                  >
                                    {it.action}
                                  </span>
                                </td>
                                <td className="py-2.5 px-3 font-mono whitespace-nowrap">
                                  {it.zoho_item_id ? (
                                    <span className="font-semibold px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200">
                                      {it.zoho_item_id}
                                    </span>
                                  ) : (
                                    <span className="text-stone-400 italic">None</span>
                                  )}
                                </td>
                                <td className="py-2.5 px-3 text-right font-mono whitespace-nowrap">
                                  {formatNumber(it.supplier_unit_price, detailData.currency)}
                                </td>
                                <td className="py-2.5 px-3 text-right font-mono font-semibold text-[#C98B4A] whitespace-nowrap">
                                  {formatNumber(it.selling_price, detailData.currency)}
                                </td>
                                <td className="py-2.5 px-3 whitespace-nowrap">
                                  <span
                                    className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                                      it.zoho_status === 'synced'
                                        ? 'bg-emerald-100 text-emerald-800'
                                        : it.zoho_status === 'failed'
                                        ? 'bg-rose-100 text-rose-800'
                                        : 'bg-stone-100 text-stone-600'
                                    }`}
                                  >
                                    {it.zoho_status}
                                  </span>
                                </td>
                                <td className="py-2.5 px-3 text-xs text-[#716B61]">
                                  {it.error_message ? (
                                    <span className="text-rose-600 font-medium">{it.error_message}</span>
                                  ) : (
                                    it.zoho_message || '-'
                                  )}
                                </td>
                              </tr>
                            ))
                          )}
                        </tbody>
                      </table>
                    </div>
                  </div>

                  {/* Section D: Raw Audit Log */}
                  {detailData.audit_log && detailData.audit_log.length > 0 && (
                    <div className="rounded-2xl border border-[#786446]/15 bg-stone-900 text-stone-100 p-5 shadow-xs space-y-2 font-mono text-xs">
                      <div className="flex items-center justify-between text-stone-400 text-[11px] border-b border-stone-800 pb-2">
                        <span>Immutable Audit Trail Execution Log</span>
                        <span>{detailData.audit_log.length} events logged</span>
                      </div>
                      <div className="max-h-40 overflow-y-auto space-y-1 text-[11px] leading-relaxed">
                        {detailData.audit_log.map((logLine, idx) => (
                          <div key={idx} className="text-stone-300">
                            {logLine}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              ) : null}
            </div>

            {/* Modal Footer: Strictly Read-Only */}
            <div className="flex items-center justify-between px-6 py-4 border-t border-[#786446]/15 bg-white/90">
              <span className="text-xs text-[#716B61] italic">
                * Audit entries are permanently locked and cannot be modified or deleted.
              </span>
              <button
                type="button"
                onClick={handleCloseDetail}
                className="px-4 py-2 rounded-xl bg-[#26231F] text-white text-xs font-semibold hover:bg-black transition cursor-pointer"
              >
                Close Audit Record
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
