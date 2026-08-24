import time
import logging
from pathlib import Path
from typing import Optional

from app.config import settings, UPLOAD_DIR, OUTPUT_DIR, TEMPLATE_DIR, SAMPLE_DIR
from app.models.quotation import ExtractionResult
from app.schemas.quotation import (
    QuotationData,
    ExtractionResponse,
    GenerateExcelRequest,
    GenerateExcelResponse,
)
from app.services.pdf_service import pdf_service
from app.services.ai_service import get_ai_service
from app.services.validation_service import validation_service
from app.services.excel_service import excel_service
from app.services.history_service import history_service
from app.utils.file_utils import get_file_path

logger = logging.getLogger(__name__)


class QuotationOrchestratorService:
    """Orchestrates PDF text extraction, AI understanding, validation, and Excel generation."""

    async def process_pdf_quotation(
        self, pdf_path: str | Path, source_pdf_id: str, template_id: Optional[str] = None
    ) -> ExtractionResponse:
        start_time = time.time()
        pdf_path = Path(pdf_path)
        logger.info(f"Processing quotation extraction for {source_pdf_id}")

        # 1. PDF Extraction via PyMuPDF
        extraction_result: ExtractionResult = pdf_service.extract_content(pdf_path)

        # 2. AI Extraction via Gemini Provider (with deterministic fallback)
        ai_provider = get_ai_service()
        quotation: QuotationData = await ai_provider.extract_quotation(
            pdf_text=extraction_result.full_text,
            filename=pdf_path.name,
        )

        quotation.source_pdf_id = source_pdf_id
        quotation.template_id = template_id

        # 3. Deterministic Validation
        validated_quote, validation_summary = validation_service.validate_quotation(
            quotation=quotation,
            raw_pdf_text=extraction_result.full_text,
        )

        # 4. Save to Conversion History
        try:
            history_service.create_or_update_record(
                quotation=validated_quote,
                validation=validation_summary,
                source_pdf_filename=pdf_path.name,
                source_pdf_id=source_pdf_id,
                template_id=template_id,
                status="verified" if validation_summary.is_valid and validation_summary.errors_count == 0 else ("warning" if validation_summary.warnings_count > 0 else "error"),
            )
        except Exception as e:
            logger.warning(f"Failed to persist extraction history: {e}")

        elapsed = round(time.time() - start_time, 2)
        source_type = "ocr_ai" if extraction_result.is_scanned else "pdf_text_ai"

        return ExtractionResponse(
            success=True,
            quotation=validated_quote,
            validation=validation_summary,
            processing_time_seconds=elapsed,
            extracted_page_count=len(extraction_result.pages),
            extraction_source=source_type,
        )

    def generate_excel_quotation(self, req: GenerateExcelRequest) -> GenerateExcelResponse:
        logger.info(f"Generating quotation Excel for template_id: {req.template_id}")
        
        template_path = get_file_path(req.template_id, [TEMPLATE_DIR, UPLOAD_DIR, SAMPLE_DIR])
        if not template_path:
            sample_templates = list(TEMPLATE_DIR.glob("*.xlsx"))
            if sample_templates:
                template_path = sample_templates[0]
            else:
                raise FileNotFoundError(f"Excel template '{req.template_id}' not found.")

        base_name = Path(req.template_id).stem
        if req.quotation.quote_number:
            out_filename = f"{req.quotation.quote_number}_Quotation.xlsx"
        else:
            out_filename = f"Generated_{base_name}.xlsx"

        file_id = f"gen_{int(time.time())}_{out_filename}"
        output_path = OUTPUT_DIR / file_id

        # Pre-generation safety checks: Validate quotation before Excel generation
        validated_quote, val_summary = validation_service.validate_quotation(req.quotation)
        if val_summary.errors_count > 0:
            error_details = "; ".join(i.message for i in val_summary.issues if i.issue_type == "error")
            logger.warning(f"Quotation has validation errors: {error_details}")
            # If critical errors exist (like duplicate line numbers or missing required fields), stop
            if any(i.field in ("line_number", "part_number") for i in val_summary.issues if i.issue_type == "error"):
                raise ValueError(f"Cannot generate Excel due to validation errors: {error_details}")

        items_count = excel_service.generate_quotation_excel(
            template_path=template_path,
            output_path=output_path,
            quotation=req.quotation,
            pricing_mode=req.pricing_mode,
            margin_percent=req.margin_percent,
            supplier_discount_percent=req.supplier_discount_percent,
            custom_mapping=req.custom_mapping,
        )

        grand_total = (
            req.quotation.grand_total
            if req.quotation.grand_total is not None
            else sum(it.total_price if it.total_price is not None else ((it.quantity or 0.0) * (it.unit_price or 0.0)) for it in req.quotation.items)
        )

        # Update Conversion History with generated Excel details
        try:
            history_service.create_or_update_record(
                quotation=validated_quote,
                validation=val_summary,
                source_pdf_id=req.quotation.source_pdf_id or "",
                template_id=req.template_id,
                excel_file_id=file_id,
                excel_filename=out_filename,
                pricing_mode=req.pricing_mode,
                status="generated",
            )
        except Exception as e:
            logger.warning(f"Failed to update generation history: {e}")

        return GenerateExcelResponse(
            success=True,
            download_url=f"{settings.API_V1_STR}/quotation/download/{file_id}",
            filename=out_filename,
            file_id=file_id,
            total_items_written=items_count,
            grand_total_written=round(grand_total, 2),
        )



quotation_orchestrator = QuotationOrchestratorService()

