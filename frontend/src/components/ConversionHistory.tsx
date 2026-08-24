import React, { useState, useEffect } from 'react';
import {
  History,
  Search,
  FileText,
  Download,
  Trash2,
  CheckCircle2,
  AlertTriangle,
  AlertCircle,
  Clock,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  RefreshCw,
  Building2,
} from 'lucide-react';
import { quotationApi } from '../services/api';
import type { ConversionRecord } from '../types/quotation';

interface ConversionHistoryProps {
  onSelectRecord: (record: ConversionRecord) => void;
  refreshTrigger?: number;
}

export const ConversionHistory: React.FC<ConversionHistoryProps> = ({
  onSelectRecord,
  refreshTrigger = 0,
}) => {
  const [records, setRecords] = useState<ConversionRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [isLoading, setIsLoading] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const fetchHistory = async () => {
    setIsLoading(true);
    try {
      const res = await quotationApi.getHistory({
        page,
        limit: 8,
        search: search || undefined,
        status: statusFilter || undefined,
      });
      setRecords(res.records);
      setTotal(res.total);
      setTotalPages(res.total_pages);
    } catch (err) {
      console.error('Failed to load conversion history', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, [page, statusFilter, refreshTrigger]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchHistory();
  };

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!window.confirm('Delete this conversion record from history?')) return;
    setDeletingId(id);
    try {
      await quotationApi.deleteConversion(id);
      fetchHistory();
    } catch (err) {
      console.error('Failed to delete conversion', err);
    } finally {
      setDeletingId(null);
    }
  };

  const handleDownload = (fileId: string, filename: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const url = quotationApi.getDownloadUrl(fileId);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename || 'Quotation.xlsx';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const formatTimestamp = (isoStr: string) => {
    if (!isoStr) return '';
    try {
      const d = new Date(isoStr);
      return d.toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return isoStr;
    }
  };

  const renderStatusBadge = (status: string) => {
    switch (status) {
      case 'generated':
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-100 text-emerald-900 border border-emerald-300 shadow-2xs">
            <CheckCircle2 className="w-3 h-3 text-emerald-700" />
            <span>Generated</span>
          </span>
        );
      case 'verified':
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-teal-100 text-teal-900 border border-teal-300 shadow-2xs">
            <CheckCircle2 className="w-3 h-3 text-teal-700" />
            <span>Verified</span>
          </span>
        );
      case 'warning':
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-amber-100 text-amber-900 border border-amber-300 shadow-2xs">
            <AlertTriangle className="w-3 h-3 text-amber-700" />
            <span>Warnings</span>
          </span>
        );
      case 'error':
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-rose-100 text-rose-900 border border-rose-300 shadow-2xs">
            <AlertCircle className="w-3 h-3 text-rose-700" />
            <span>Errors</span>
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-stone-100 text-stone-700 border border-stone-300">
            <Clock className="w-3 h-3 text-stone-500" />
            <span>Draft</span>
          </span>
        );
    }
  };

  return (
    <div className="bg-white/75 border border-[#786446]/15 rounded-3xl p-6 shadow-sm backdrop-blur-md space-y-5">
      {/* Header & Controls */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center space-x-3">
          <div className="p-2.5 rounded-2xl bg-[#26231F] text-white shadow-md">
            <History className="w-5 h-5 text-[#C98B4A]" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h2 className="text-base font-bold text-[#26231F]">Conversion History</h2>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-[#F5F1E8] text-[#716B61] border border-[#786446]/15">
                {total} Records
              </span>
            </div>
            <p className="text-xs text-[#716B61]">Revisit, inspect, and re-download past conversions</p>
          </div>
        </div>

        {/* Search and Filters */}
        <div className="flex flex-wrap items-center gap-2">
          <form onSubmit={handleSearchSubmit} className="relative">
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search quote # or customer..."
              className="w-48 sm:w-60 bg-[#F5F1E8] border border-[#786446]/20 rounded-xl pl-8 pr-3 py-1.5 text-xs text-[#26231F] focus:border-[#26231F] focus:outline-none transition"
            />
            <Search className="w-3.5 h-3.5 text-[#716B61] absolute left-2.5 top-2.5 pointer-events-none" />
          </form>

          {/* Status Filter Chips */}
          <div className="flex items-center space-x-1 bg-[#F5F1E8] p-1 rounded-xl border border-[#786446]/15 text-xs">
            <button
              type="button"
              onClick={() => { setStatusFilter(''); setPage(1); }}
              className={`px-2.5 py-1 rounded-lg font-semibold transition cursor-pointer ${
                statusFilter === '' ? 'bg-[#26231F] text-white shadow-xs' : 'text-[#716B61] hover:text-[#26231F]'
              }`}
            >
              All
            </button>
            <button
              type="button"
              onClick={() => { setStatusFilter('generated'); setPage(1); }}
              className={`px-2.5 py-1 rounded-lg font-semibold transition cursor-pointer ${
                statusFilter === 'generated' ? 'bg-[#26231F] text-white shadow-xs' : 'text-[#716B61] hover:text-[#26231F]'
              }`}
            >
              Generated
            </button>
            <button
              type="button"
              onClick={() => { setStatusFilter('error'); setPage(1); }}
              className={`px-2.5 py-1 rounded-lg font-semibold transition cursor-pointer ${
                statusFilter === 'error' ? 'bg-[#26231F] text-white shadow-xs' : 'text-[#716B61] hover:text-[#26231F]'
              }`}
            >
              Errors
            </button>
          </div>

          <button
            type="button"
            onClick={fetchHistory}
            title="Refresh History"
            className="p-2 rounded-xl bg-[#F5F1E8] border border-[#786446]/15 text-[#716B61] hover:text-[#26231F] hover:bg-[#EAE4D7] transition cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* History Cards List */}
      {records.length === 0 ? (
        <div className="text-center py-10 bg-[#F5F1E8]/50 border border-dashed border-[#786446]/20 rounded-2xl">
          <History className="w-8 h-8 text-[#716B61]/40 mx-auto mb-2" />
          <p className="text-xs font-bold text-[#26231F]">No conversion records found</p>
          <p className="text-[11px] text-[#716B61] mt-0.5">
            {search || statusFilter ? 'Try clearing your search or status filter.' : 'Upload and extract a quotation PDF to see it saved here.'}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {records.map((record) => (
            <div
              key={record.id}
              onClick={() => onSelectRecord(record)}
              className="bg-[#F5F1E8]/60 hover:bg-[#F5F1E8] border border-[#786446]/15 hover:border-[#786446]/40 rounded-2xl p-4 transition-all duration-150 shadow-2xs hover:shadow-md cursor-pointer flex flex-col justify-between space-y-3 group"
            >
              {/* Top Row: Quote # and Status */}
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center space-x-2">
                    <span className="font-mono text-sm font-bold text-[#26231F] group-hover:text-[#C98B4A] transition">
                      Quote #{record.quote_number || 'Draft'}
                    </span>
                    {renderStatusBadge(record.status)}
                  </div>
                  <div className="flex items-center space-x-1.5 text-xs text-[#716B61] mt-1">
                    <Building2 className="w-3 h-3 text-[#C98B4A]" />
                    <span className="font-medium truncate max-w-[220px]">{record.customer || 'Unknown Client'}</span>
                  </div>
                </div>

                <div className="text-right">
                  <span className="text-[11px] font-mono text-[#716B61] flex items-center space-x-1">
                    <Clock className="w-3 h-3" />
                    <span>{formatTimestamp(record.created_at)}</span>
                  </span>
                  {record.grand_total > 0 && (
                    <p className="text-xs font-mono font-bold text-emerald-800 mt-1">
                      {record.currency || 'EUR'} {record.grand_total.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </p>
                  )}
                </div>
              </div>

              {/* Middle Row: Items & PDF Info */}
              <div className="grid grid-cols-2 gap-2 text-[11px] text-[#716B61] bg-white/60 p-2.5 rounded-xl border border-[#786446]/10">
                <div className="flex items-center space-x-1.5 truncate">
                  <FileText className="w-3.5 h-3.5 text-[#C98B4A] shrink-0" />
                  <span className="truncate">{record.source_pdf_filename || 'PDF Document'}</span>
                </div>
                <div className="text-right font-mono">
                  <strong className="text-[#26231F]">{record.items_count}</strong> line item(s)
                </div>
              </div>

              {/* Bottom Action Row */}
              <div className="flex items-center justify-between pt-1 border-t border-[#786446]/10 text-xs">
                <span className="text-[11px] text-[#716B61] group-hover:text-[#26231F] flex items-center space-x-1 font-semibold">
                  <ExternalLink className="w-3 h-3 text-[#C98B4A]" />
                  <span>Reopen & Inspect</span>
                </span>

                <div className="flex items-center space-x-2">
                  {record.excel_file_id && (
                    <button
                      type="button"
                      onClick={(e) => handleDownload(record.excel_file_id!, record.excel_filename || `${record.quote_number}_Quotation.xlsx`, e)}
                      title="Download Generated Excel"
                      className="flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border border-emerald-200 font-semibold text-[11px] transition cursor-pointer"
                    >
                      <Download className="w-3 h-3 text-emerald-700" />
                      <span>XLSX</span>
                    </button>
                  )}

                  <button
                    type="button"
                    onClick={(e) => handleDelete(record.id, e)}
                    disabled={deletingId === record.id}
                    title="Delete record"
                    className="p-1 rounded-lg text-rose-500 hover:bg-rose-50 hover:text-rose-700 transition cursor-pointer"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Pagination Footer */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between pt-3 border-t border-[#786446]/10 text-xs text-[#716B61]">
          <span>
            Page <strong className="text-[#26231F]">{page}</strong> of <strong className="text-[#26231F]">{totalPages}</strong> ({total} conversions)
          </span>

          <div className="flex items-center space-x-1">
            <button
              type="button"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="p-1.5 rounded-lg bg-[#F5F1E8] border border-[#786446]/15 hover:bg-[#EAE4D7] disabled:opacity-40 transition cursor-pointer"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button
              type="button"
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="p-1.5 rounded-lg bg-[#F5F1E8] border border-[#786446]/15 hover:bg-[#EAE4D7] disabled:opacity-40 transition cursor-pointer"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
