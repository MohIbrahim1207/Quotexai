import sqlite3
import json
import time
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone

from app.config import BASE_DIR, OUTPUT_DIR, UPLOAD_DIR
from app.schemas.quotation import QuotationData, ValidationSummary

logger = logging.getLogger(__name__)

DB_PATH = BASE_DIR.parent / "outputs" / "conversions.db"


class HistoryService:
    """SQLite-backed conversion history persistence layer."""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS conversions (
                    id TEXT PRIMARY KEY,
                    quote_number TEXT,
                    customer TEXT,
                    source_pdf_filename TEXT,
                    source_pdf_id TEXT,
                    template_id TEXT,
                    quote_date TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    status TEXT,
                    items_count INTEGER,
                    currency TEXT,
                    grand_total REAL,
                    pricing_mode TEXT,
                    excel_file_id TEXT,
                    excel_filename TEXT,
                    quotation_data TEXT,
                    validation_summary TEXT
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_conv_created ON conversions(created_at DESC)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_conv_quote ON conversions(quote_number)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_conv_customer ON conversions(customer)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_conv_status ON conversions(status)")
            conn.commit()

    def create_or_update_record(
        self,
        quotation: QuotationData,
        validation: Optional[ValidationSummary] = None,
        source_pdf_filename: str = "",
        source_pdf_id: str = "",
        template_id: Optional[str] = None,
        excel_file_id: Optional[str] = None,
        excel_filename: Optional[str] = None,
        pricing_mode: str = "quoted_price",
        status: Optional[str] = None,
        conversion_id: Optional[str] = None,
    ) -> str:
        now_iso = datetime.now(timezone.utc).isoformat()

        
        # Determine status if not provided
        if not status:
            if excel_file_id:
                status = "generated"
            elif validation and validation.errors_count > 0:
                status = "error"
            elif validation and validation.warnings_count > 0:
                status = "warning"
            else:
                status = "verified"

        # Calculate grand total
        grand_total = quotation.grand_total
        if grand_total is None and quotation.items:
            grand_total = sum(
                it.total_price if it.total_price is not None else ((it.quantity or 0.0) * (it.unit_price or 0.0))
                for it in quotation.items
            )

        cid = conversion_id or f"conv_{int(time.time())}_{quotation.quote_number or 'draft'}"
        
        quote_json = quotation.model_dump_json() if hasattr(quotation, "model_dump_json") else json.dumps(quotation)
        val_json = validation.model_dump_json() if validation and hasattr(validation, "model_dump_json") else (json.dumps(validation) if validation else "{}")

        with self._get_connection() as conn:
            # Check if record already exists by ID or quote_number + source_pdf_id
            existing = None
            if conversion_id:
                existing = conn.execute("SELECT id FROM conversions WHERE id = ?", (conversion_id,)).fetchone()
            elif quotation.quote_number and source_pdf_id:
                existing = conn.execute(
                    "SELECT id FROM conversions WHERE quote_number = ? AND source_pdf_id = ?",
                    (quotation.quote_number, source_pdf_id),
                ).fetchone()

            if existing:
                cid = existing["id"]
                conn.execute(
                    """
                    UPDATE conversions SET
                        quote_number = ?,
                        customer = ?,
                        source_pdf_filename = COALESCE(NULLIF(?, ''), source_pdf_filename),
                        source_pdf_id = COALESCE(NULLIF(?, ''), source_pdf_id),
                        template_id = COALESCE(NULLIF(?, ''), template_id),
                        quote_date = ?,
                        updated_at = ?,
                        status = ?,
                        items_count = ?,
                        currency = ?,
                        grand_total = ?,
                        pricing_mode = ?,
                        excel_file_id = COALESCE(NULLIF(?, ''), excel_file_id),
                        excel_filename = COALESCE(NULLIF(?, ''), excel_filename),
                        quotation_data = ?,
                        validation_summary = ?
                    WHERE id = ?
                    """,
                    (
                        quotation.quote_number or "",
                        quotation.customer or "",
                        source_pdf_filename,
                        source_pdf_id,
                        template_id or "",
                        quotation.quote_date or "",
                        now_iso,
                        status,
                        len(quotation.items),
                        quotation.currency or "EUR",
                        grand_total or 0.0,
                        pricing_mode,
                        excel_file_id or "",
                        excel_filename or "",
                        quote_json,
                        val_json,
                        cid,
                    ),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO conversions (
                        id, quote_number, customer, source_pdf_filename, source_pdf_id,
                        template_id, quote_date, created_at, updated_at, status,
                        items_count, currency, grand_total, pricing_mode,
                        excel_file_id, excel_filename, quotation_data, validation_summary
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        cid,
                        quotation.quote_number or "",
                        quotation.customer or "",
                        source_pdf_filename,
                        source_pdf_id,
                        template_id or "",
                        quotation.quote_date or "",
                        now_iso,
                        now_iso,
                        status,
                        len(quotation.items),
                        quotation.currency or "EUR",
                        grand_total or 0.0,
                        pricing_mode,
                        excel_file_id or "",
                        excel_filename or "",
                        quote_json,
                        val_json,
                    ),
                )
            conn.commit()

        logger.info(f"Persisted conversion record {cid} [Quote: {quotation.quote_number}, Status: {status}]")
        return cid

    def get_record(self, conversion_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM conversions WHERE id = ?", (conversion_id,)).fetchone()
            if not row:
                return None
            return self._row_to_dict(row)

    def list_records(
        self,
        page: int = 1,
        limit: int = 20,
        search: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        offset = (page - 1) * limit
        query_parts = ["1=1"]
        params: List[Any] = []

        if search:
            s_term = f"%{search.strip().lower()}%"
            query_parts.append(
                "(LOWER(quote_number) LIKE ? OR LOWER(customer) LIKE ? OR LOWER(source_pdf_filename) LIKE ?)"
            )
            params.extend([s_term, s_term, s_term])

        if status:
            query_parts.append("status = ?")
            params.append(status.strip().lower())

        where_clause = " AND ".join(query_parts)

        with self._get_connection() as conn:
            count_row = conn.execute(f"SELECT COUNT(*) as total FROM conversions WHERE {where_clause}", params).fetchone()
            total_count = count_row["total"] if count_row else 0

            rows = conn.execute(
                f"""
                SELECT id, quote_number, customer, source_pdf_filename, source_pdf_id,
                       template_id, quote_date, created_at, updated_at, status,
                       items_count, currency, grand_total, pricing_mode,
                       excel_file_id, excel_filename
                FROM conversions
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                params + [limit, offset],
            ).fetchall()

            records = [dict(r) for r in rows]
            total_pages = max(1, (total_count + limit - 1) // limit)
            return records, total_count, total_pages

    def delete_record(self, conversion_id: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM conversions WHERE id = ?", (conversion_id,))
            conn.commit()
            return cursor.rowcount > 0

    def clear_all(self):
        with self._get_connection() as conn:
            conn.execute("DELETE FROM conversions")
            conn.commit()

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        data = dict(row)
        if data.get("quotation_data"):
            try:
                data["quotation_data"] = json.loads(data["quotation_data"])
            except Exception:
                pass
        if data.get("validation_summary"):
            try:
                data["validation_summary"] = json.loads(data["validation_summary"])
            except Exception:
                pass
        return data


history_service = HistoryService()
