import sqlite3
import json
import uuid
import time
import logging
from pathlib import Path
from typing import Optional, Any
from datetime import datetime, timezone

from app.config import BASE_DIR, OUTPUT_DIR
from app.schemas.supplier_pricing import (
    ZohoExecuteSyncRequest,
    ZohoExecuteSyncResponse,
    SupplierPricingCalculationResponse,
    ProcurementApprovalRequest,
    ProcurementApprovalResponse,
)

logger = logging.getLogger(__name__)

DB_PATH = BASE_DIR.parent / "outputs" / "supplier_pricing_history.db"


class SupplierPricingHistoryService:
    """Persistent SQLite-backed audit and history layer for Supplier Pricing and Zoho Books Sync."""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Initializes tables and indexes if they do not exist."""
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS supplier_pricing_history (
                    id TEXT PRIMARY KEY,
                    quotation_number TEXT NOT NULL,
                    supplier_name TEXT NOT NULL,
                    quotation_date TEXT,
                    source_filename TEXT,
                    currency TEXT NOT NULL DEFAULT 'EUR',
                    processed_at TEXT NOT NULL,
                    processed_by TEXT,
                    overall_status TEXT NOT NULL,
                    total_items INTEGER NOT NULL DEFAULT 0,
                    created_count INTEGER NOT NULL DEFAULT 0,
                    updated_count INTEGER NOT NULL DEFAULT 0,
                    failed_count INTEGER NOT NULL DEFAULT 0,
                    total_supplier_net REAL DEFAULT 0.0,
                    total_landed_cost REAL DEFAULT 0.0,
                    total_selling_price REAL DEFAULT 0.0,
                    total_gross_profit REAL DEFAULT 0.0,
                    overall_margin_percent REAL DEFAULT 0.0,
                    zoho_organization_id TEXT,
                    zoho_environment TEXT,
                    sync_message TEXT,
                    audit_log TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS supplier_pricing_history_items (
                    id TEXT PRIMARY KEY,
                    history_id TEXT NOT NULL,
                    line_number INTEGER NOT NULL DEFAULT 1,
                    sku TEXT NOT NULL,
                    description TEXT,
                    quantity REAL NOT NULL DEFAULT 1.0,
                    unit TEXT DEFAULT 'NOS',
                    supplier_unit_price REAL DEFAULT 0.0,
                    discount_percent REAL DEFAULT 0.0,
                    landed_cost REAL DEFAULT 0.0,
                    selling_price REAL DEFAULT 0.0,
                    action TEXT NOT NULL DEFAULT 'CREATE',
                    zoho_item_id TEXT,
                    zoho_status TEXT NOT NULL DEFAULT 'ready',
                    zoho_message TEXT,
                    error_message TEXT,
                    FOREIGN KEY (history_id) REFERENCES supplier_pricing_history(id) ON DELETE CASCADE
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sph_processed ON supplier_pricing_history(processed_at DESC)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sph_quote ON supplier_pricing_history(quotation_number)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sph_supplier ON supplier_pricing_history(supplier_name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sph_status ON supplier_pricing_history(overall_status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sphi_hid ON supplier_pricing_history_items(history_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sphi_sku ON supplier_pricing_history_items(sku)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sphi_action ON supplier_pricing_history_items(action)")
            # Normalize any legacy status values
            conn.execute("UPDATE supplier_pricing_history SET overall_status = 'SUCCESS' WHERE overall_status = 'synced'")
            conn.execute("UPDATE supplier_pricing_history SET overall_status = 'PARTIAL' WHERE overall_status = 'partially_synced'")
            conn.execute("UPDATE supplier_pricing_history SET overall_status = 'FAILED' WHERE overall_status = 'failed'")
            conn.commit()

    def record_sync_result(
        self,
        req: ZohoExecuteSyncRequest,
        resp: ZohoExecuteSyncResponse,
        overall_status: str,
    ) -> str:
        """
        Persists a complete Stage 4 Zoho Books synchronization result to history.
        Ensures zoho_item_id contains only real numeric Zoho Books IDs, never fake ZB-NEW- IDs.
        """
        history_id = str(uuid.uuid4())
        now_iso = datetime.now(timezone.utc).isoformat()

        # Standardize overall_status
        status_raw = (overall_status or "").strip().lower()
        if status_raw in ("synced", "success", "successful"):
            norm_status = "SUCCESS"
        elif status_raw in ("partially_synced", "partial", "partially_failed"):
            norm_status = "PARTIAL"
        elif status_raw in ("failed", "fail"):
            norm_status = "FAILED"
        elif status_raw in ("approved",):
            norm_status = "APPROVED"
        elif status_raw in ("calculated",):
            norm_status = "CALCULATED"
        else:
            norm_status = overall_status.upper()

        # Extract metadata from request
        quote_no = (getattr(req, "quotation_number", None) or req.items[0].part_number if req.items else "N/A").strip()
        if hasattr(req, "quotation_number") and req.quotation_number:
            quote_no = req.quotation_number.strip()

        supplier = getattr(req, "supplier_name", "Supplier").strip() if hasattr(req, "supplier_name") and req.supplier_name else "Supplier"
        quote_date = getattr(req, "quotation_date", "") or ""
        source_file = getattr(req, "source_filename", "") or ""
        currency = getattr(req, "currency", "EUR") or (req.items[0].currency if req.items else "EUR")
        user = (req.confirmed_by_user or "User").strip()

        pricing_summary = getattr(req, "pricing_summary", None)
        tot_supplier_net = getattr(pricing_summary, "total_supplier_net", 0.0) if pricing_summary else 0.0
        tot_landed_cost = getattr(pricing_summary, "total_landed_cost", 0.0) if pricing_summary else 0.0
        tot_selling_price = getattr(pricing_summary, "total_selling_price", sum(it.rate for it in req.items)) if pricing_summary else sum(it.rate for it in req.items)
        tot_profit = getattr(pricing_summary, "total_gross_profit", 0.0) if pricing_summary else 0.0
        overall_margin = getattr(pricing_summary, "overall_margin_percent", 0.0) if pricing_summary else 0.0

        failed_count = len(resp.records) - (resp.created_count + resp.updated_count)

        audit_log_json = json.dumps(resp.audit_log)

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO supplier_pricing_history (
                    id, quotation_number, supplier_name, quotation_date, source_filename,
                    currency, processed_at, processed_by, overall_status, total_items,
                    created_count, updated_count, failed_count, total_supplier_net,
                    total_landed_cost, total_selling_price, total_gross_profit,
                    overall_margin_percent, zoho_organization_id, zoho_environment,
                    sync_message, audit_log, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    history_id,
                    quote_no,
                    supplier,
                    quote_date,
                    source_file,
                    currency,
                    now_iso,
                    user,
                    norm_status,
                    len(resp.records),
                    resp.created_count,
                    resp.updated_count,
                    max(0, failed_count),
                    float(tot_supplier_net or 0.0),
                    float(tot_landed_cost or 0.0),
                    float(tot_selling_price or 0.0),
                    float(tot_profit or 0.0),
                    float(overall_margin or 0.0),
                    req.zoho_config.organization_id,
                    req.zoho_config.environment,
                    resp.message,
                    audit_log_json,
                    now_iso,
                ),
            )

            # Insert each synchronized line item
            for idx, rec in enumerate(resp.records, start=1):
                item_id = str(uuid.uuid4())
                raw_zoho_id = (rec.existing_item_id or "").strip()
                # Strict verification: zoho_item_id MUST be numeric or None; reject fake strings
                clean_zoho_id = raw_zoho_id if raw_zoho_id.isdigit() else None

                err_msg = rec.notes if rec.status == "failed" else None

                conn.execute(
                    """
                    INSERT INTO supplier_pricing_history_items (
                        id, history_id, line_number, sku, description, quantity,
                        unit, supplier_unit_price, discount_percent, landed_cost,
                        selling_price, action, zoho_item_id, zoho_status,
                        zoho_message, error_message
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        item_id,
                        history_id,
                        idx,
                        rec.part_number,
                        rec.description,
                        1.0,
                        rec.unit or "NOS",
                        float(rec.purchase_rate or 0.0),
                        0.0,
                        float(rec.purchase_rate or 0.0),
                        float(rec.rate or 0.0),
                        rec.action,
                        clean_zoho_id,
                        rec.status,
                        rec.notes,
                        err_msg,
                    ),
                )
            conn.commit()

        logger.info(f"Recorded supplier pricing sync history: {history_id} (Quote: {quote_no}, Status: {overall_status})")
        return history_id

    def record_pricing_calculation(
        self,
        quote_number: str,
        supplier_name: str,
        quote_date: Optional[str],
        source_filename: Optional[str],
        calc_resp: SupplierPricingCalculationResponse,
        user: str = "Procurement Specialist",
        status: str = "calculated",
    ) -> str:
        """
        Persists a Stage 2/3 pricing calculation or approval to history so History is useful
        even before Zoho Books synchronization is triggered.
        """
        history_id = str(uuid.uuid4())
        now_iso = datetime.now(timezone.utc).isoformat()
        summary = calc_resp.summary

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO supplier_pricing_history (
                    id, quotation_number, supplier_name, quotation_date, source_filename,
                    currency, processed_at, processed_by, overall_status, total_items,
                    created_count, updated_count, failed_count, total_supplier_net,
                    total_landed_cost, total_selling_price, total_gross_profit,
                    overall_margin_percent, zoho_organization_id, zoho_environment,
                    sync_message, audit_log, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    history_id,
                    quote_number or "N/A",
                    supplier_name or "Supplier",
                    quote_date or "",
                    source_filename or "",
                    summary.target_currency or "EUR",
                    now_iso,
                    user,
                    status,
                    len(calc_resp.items),
                    0,
                    0,
                    0,
                    float(summary.total_supplier_net),
                    float(summary.total_landed_cost),
                    float(summary.total_selling_price),
                    float(summary.total_gross_profit),
                    float(summary.overall_margin_percent),
                    None,
                    None,
                    f"Pricing calculated ({len(calc_resp.items)} items, margin {summary.overall_margin_percent:.1f}%).",
                    json.dumps([f"[{now_iso}] Pricing calculated by {user}."]),
                    now_iso,
                ),
            )

            for it in calc_resp.items:
                conn.execute(
                    """
                    INSERT INTO supplier_pricing_history_items (
                        id, history_id, line_number, sku, description, quantity,
                        unit, supplier_unit_price, discount_percent, landed_cost,
                        selling_price, action, zoho_item_id, zoho_status,
                        zoho_message, error_message
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid.uuid4()),
                        history_id,
                        it.line_number,
                        it.part_number,
                        it.description,
                        float(it.quantity),
                        it.unit,
                        float(it.net_supplier_unit_price),
                        float(it.discount_percent),
                        float(it.landed_cost_unit),
                        float(it.final_unit_selling_price),
                        "PENDING",
                        None,
                        "ready",
                        "Calculated selling price ready for sync review.",
                        None,
                    ),
                )
            conn.commit()

        return history_id

    def list_history(
        self,
        page: int = 1,
        page_size: int = 15,
        search: Optional[str] = None,
        status: Optional[str] = None,
        action: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> tuple[list[dict[str, Any]], int, int, dict[str, int]]:
        """
        Retrieves paginated history records with search and filters, along with summary statistics.
        Read-only query.
        """
        offset = (page - 1) * page_size
        where_clauses = ["1=1"]
        params: list[Any] = []

        # Search by quotation number, supplier name, or sku
        if search and search.strip():
            st = f"%{search.strip()}%"
            where_clauses.append(
                """(
                    h.quotation_number LIKE ?
                    OR h.supplier_name LIKE ?
                    OR h.id IN (SELECT history_id FROM supplier_pricing_history_items WHERE sku LIKE ?)
                )"""
            )
            params.extend([st, st, st])

        # Filter by status
        if status and status.strip() and status.lower() != "all":
            norm_status = status.strip().upper()
            if norm_status in ("SUCCESS", "SUCCESSFUL", "SYNCED"):
                where_clauses.append("h.overall_status IN ('SUCCESS', 'synced')")
            elif norm_status in ("PARTIAL", "PARTIALLY_SYNCED", "PARTIALLY_FAILED"):
                where_clauses.append("h.overall_status IN ('PARTIAL', 'partially_synced')")
            elif norm_status in ("FAILED", "FAIL"):
                where_clauses.append("h.overall_status IN ('FAILED', 'failed')")
            elif norm_status in ("APPROVED",):
                where_clauses.append("h.overall_status IN ('APPROVED', 'approved')")
            elif norm_status in ("CALCULATED",):
                where_clauses.append("h.overall_status IN ('CALCULATED', 'calculated')")
            else:
                where_clauses.append("h.overall_status = ?")
                params.append(norm_status)

        # Filter by action (CREATE or UPDATE)
        if action and action.strip() and action.upper() in ("CREATE", "UPDATE"):
            where_clauses.append(
                "h.id IN (SELECT history_id FROM supplier_pricing_history_items WHERE action = ?)"
            )
            params.append(action.strip().upper())

        # Date range filters
        if start_date and start_date.strip():
            where_clauses.append("h.processed_at >= ?")
            params.append(start_date.strip())
        if end_date and end_date.strip():
            where_clauses.append("h.processed_at <= ?")
            params.append(end_date.strip() + "T23:59:59")

        where_sql = " AND ".join(where_clauses)

        with self._get_connection() as conn:
            # 1. Compute summary stats over all records
            stats_row = conn.execute(
                """
                SELECT
                    COUNT(*) as total_quotations,
                    SUM(CASE WHEN overall_status IN ('SUCCESS', 'synced', 'APPROVED', 'approved') THEN 1 ELSE 0 END) as successfully_synced,
                    SUM(CASE WHEN overall_status IN ('PARTIAL', 'partially_synced') THEN 1 ELSE 0 END) as partially_failed,
                    SUM(CASE WHEN overall_status IN ('FAILED', 'failed') THEN 1 ELSE 0 END) as failed
                FROM supplier_pricing_history
                """
            ).fetchone()

            summary_stats = {
                "total_quotations": stats_row["total_quotations"] or 0,
                "successfully_synced": stats_row["successfully_synced"] or 0,
                "partially_failed": stats_row["partially_failed"] or 0,
                "failed": stats_row["failed"] or 0,
            }

            # 2. Count filtered records
            count_query = f"SELECT COUNT(*) FROM supplier_pricing_history h WHERE {where_sql}"
            total_count = conn.execute(count_query, params).fetchone()[0]

            # 3. Retrieve page of records
            data_query = f"""
                SELECT
                    h.id, h.quotation_number, h.supplier_name, h.quotation_date,
                    h.source_filename, h.currency, h.processed_at, h.processed_by,
                    h.overall_status, h.total_items, h.created_count, h.updated_count,
                    h.failed_count, h.total_supplier_net, h.total_landed_cost,
                    h.total_selling_price, h.total_gross_profit, h.overall_margin_percent,
                    h.zoho_organization_id, h.zoho_environment, h.sync_message
                FROM supplier_pricing_history h
                WHERE {where_sql}
                ORDER BY h.processed_at DESC
                LIMIT ? OFFSET ?
            """
            rows = conn.execute(data_query, params + [page_size, offset]).fetchall()

            records = [dict(row) for row in rows]
            total_pages = max(1, (total_count + page_size - 1) // page_size)

        return records, total_count, total_pages, summary_stats

    def get_history_detail(self, history_id: str) -> Optional[dict[str, Any]]:
        """
        Retrieves full read-only detail of a specific history record including all items and audit log.
        """
        with self._get_connection() as conn:
            h_row = conn.execute(
                "SELECT * FROM supplier_pricing_history WHERE id = ?",
                (history_id,),
            ).fetchone()

            if not h_row:
                return None

            result = dict(h_row)
            try:
                result["audit_log"] = json.loads(result.get("audit_log") or "[]")
            except Exception:
                result["audit_log"] = []

            # Retrieve items
            items_rows = conn.execute(
                """
                SELECT
                    id, history_id, line_number, sku, description, quantity,
                    unit, supplier_unit_price, discount_percent, landed_cost,
                    selling_price, action, zoho_item_id, zoho_status,
                    zoho_message, error_message
                FROM supplier_pricing_history_items
                WHERE history_id = ?
                ORDER BY line_number ASC
                """,
                (history_id,),
            ).fetchall()

            result["items"] = [dict(r) for r in items_rows]

        return result


supplier_pricing_history_service = SupplierPricingHistoryService()
