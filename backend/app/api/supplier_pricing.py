import logging
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query

from app.config import UPLOAD_DIR, SAMPLE_DIR
from app.schemas.supplier_pricing import (
    SupplierQuotationData,
    SupplierExtractionResponse,
    SupplierValidationSummary,
    SupplierWorkflowStagesResponse,
    SupplierPricingCalculationRequest,
    SupplierPricingCalculationResponse,
    ProcurementApprovalRequest,
    ProcurementApprovalResponse,
    ZohoPreviewRequest,
    ZohoPreviewResponse,
    ZohoExecuteSyncRequest,
    ZohoExecuteSyncResponse,
    SupplierPricingHistorySummary,
    SupplierPricingHistoryDetail,
    SupplierPricingHistoryStats,
    SupplierPricingHistoryListResponse,
    ZohoCompositeItemCreateRequest,
    ZohoCompositeItemUpdateRequest,
    ZohoCompositeItemResponse,
)
from app.services.supplier_pricing_service import supplier_pricing_service
from app.services.supplier_pricing_history_service import supplier_pricing_history_service
from app.services.zoho_books_service import zoho_books_service
from app.utils.file_utils import save_uploaded_file, get_file_path

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/supplier-pricing", tags=["Supplier Pricing & Zoho Books"])


@router.post("/upload-pdf", summary="Upload supplier quotation PDF")
async def upload_supplier_pdf(file: UploadFile = File(...)):
    """Uploads and saves a supplier quotation PDF for extraction."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed for supplier quotation upload.")

    file_id, dest_path = await save_uploaded_file(file, UPLOAD_DIR)
    logger.info(f"Supplier quotation PDF uploaded: {file.filename} -> {file_id}")
    return {
        "success": True,
        "file_id": file_id,
        "filename": file.filename,
        "size_bytes": dest_path.stat().st_size,
    }


@router.post("/extract", response_model=SupplierExtractionResponse, summary="Extract structured supplier quote from PDF")
async def extract_supplier_quotation(pdf_id: str = Form(...)):
    """Extracts supplier name, quote #, date, line items, charges, totals, and validation status."""
    pdf_path = get_file_path(pdf_id, [UPLOAD_DIR, SAMPLE_DIR])
    if not pdf_path:
        raise HTTPException(
            status_code=404,
            detail=f"Supplier PDF '{pdf_id}' not found. Please upload again."
        )

    try:
        response = supplier_pricing_service.extract_from_pdf(
            pdf_path=pdf_path,
            source_pdf_id=pdf_id,
            original_filename=pdf_path.name,
        )
        return response
    except Exception as e:
        logger.error(f"Error extracting supplier quote {pdf_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to extract supplier quotation: {str(e)}"
        )


@router.post("/validate", response_model=SupplierValidationSummary, summary="Validate edited supplier quotation data")
async def validate_supplier_quotation(quotation: SupplierQuotationData):
    """Re-runs validation on edited supplier quotation fields and calculates warnings/errors."""
    try:
        return supplier_pricing_service.validate_quotation(quotation)
    except Exception as e:
        logger.error(f"Validation error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Validation failed: {str(e)}"
        )


@router.get("/stages", response_model=SupplierWorkflowStagesResponse, summary="Get module workflow stages")
async def get_workflow_stages():
    """Returns workflow status and roadmap placeholders for Pricing, Approval, and Zoho Books."""
    return supplier_pricing_service.get_workflow_stages()


@router.post("/calculate-pricing", response_model=SupplierPricingCalculationResponse, summary="Calculate deterministic customer pricing")
async def calculate_supplier_pricing(req: SupplierPricingCalculationRequest):
    """Calculates deterministic pricing with step-by-step breakdown using Excel pricing logic."""
    try:
        return supplier_pricing_service.calculate_pricing(req)
    except Exception as e:
        logger.error(f"Pricing calculation error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Pricing calculation failed: {str(e)}"
        )


@router.post("/approval", response_model=ProcurementApprovalResponse, summary="Submit procurement approval decision")
async def submit_procurement_approval(req: ProcurementApprovalRequest):
    """Submits procurement approval decision (pending, approved, rejected) with notes."""
    try:
        return supplier_pricing_service.submit_approval(req)
    except Exception as e:
        logger.error(f"Approval submission error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Approval submission failed: {str(e)}"
        )


@router.post("/zoho-preview", response_model=ZohoPreviewResponse, summary="Preview Zoho Books CREATE and UPDATE sync actions")
async def preview_zoho_sync_records(req: ZohoPreviewRequest):
    """Categorizes items into CREATE (new SKU) and UPDATE (existing SKU) without writing to production."""
    try:
        return supplier_pricing_service.preview_zoho_sync(req)
    except Exception as e:
        logger.error(f"Zoho preview error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Zoho preview failed: {str(e)}"
        )


@router.post("/zoho-sync", response_model=ZohoExecuteSyncResponse, summary="Execute confirmed sync to Zoho Books")
async def execute_zoho_books_sync(req: ZohoExecuteSyncRequest):
    """Executes Zoho Books sync only with explicit user confirmation; never silently writes."""
    if not req.user_confirmed:
        raise HTTPException(
            status_code=400,
            detail="Safety guardrail triggered: User confirmation required before writing to Zoho Books."
        )
    try:
        return supplier_pricing_service.execute_zoho_sync(req)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Zoho sync error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Zoho sync failed: {str(e)}"
        )


@router.get("/zoho/test-connection", summary="Test read-only Zoho Books connection")
async def test_zoho_connection(organization_id: str | None = None):
    """Executes read-only Zoho Books connectivity test targeting TEST-AUTOMATION-001 (Item ID: 2552396000020372001)."""
    try:
        return zoho_books_service.test_connectivity(organization_id=organization_id)
    except Exception as e:
        logger.error(f"Zoho connectivity test error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Zoho connectivity test failed: {str(e)}"
        )


@router.get("/zoho/items/search", summary="Search Zoho Books items (read-only)")
async def search_zoho_items(search_text: str = "", organization_id: str | None = None):
    """Searches Zoho Books items using GET /books/v3/items?organization_id={org_id}&search_text={search_text}."""
    try:
        return zoho_books_service.search_items(search_text=search_text, organization_id=organization_id)
    except Exception as e:
        logger.error(f"Zoho item search error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Zoho item search failed: {str(e)}"
        )


@router.get("/zoho/live-connectivity-test", summary="Strict LIVE Zoho Books connectivity verification without mock/fallback")
async def strict_live_zoho_test(organization_id: str | None = None):
    """Executes strictly LIVE real HTTPS request to Zoho Books API for TEST-AUTOMATION-001 (Item ID: 2552396000020372001)."""
    try:
        return zoho_books_service.strict_live_connectivity_test(organization_id=organization_id)
    except Exception as e:
        logger.error(f"Strict live Zoho connectivity test error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Strict live Zoho connectivity test failed: {str(e)}"
        )


# ============================================================================
# Zoho Books Composite Items Endpoints
# ============================================================================

@router.post(
    "/zoho/composite-items",
    response_model=ZohoCompositeItemResponse,
    summary="Create a new composite item in Zoho Books",
)
async def create_zoho_composite_item(
    req: ZohoCompositeItemCreateRequest,
    organization_id: str | None = None,
):
    """Creates a new composite item in Zoho Books using POST /books/v3/compositeitems."""
    try:
        payload = req.model_dump(exclude_none=True)
        res = zoho_books_service.create_composite_item(payload=payload, organization_id=organization_id)
        return ZohoCompositeItemResponse(
            success=True,
            composite_item_id=res.get("composite_item_id"),
            message=res.get("message", "Composite item created successfully"),
            composite_item=res.get("composite_item"),
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except RuntimeError as re:
        err_msg = str(re)
        if "401" in err_msg or "authentication" in err_msg.lower():
            raise HTTPException(status_code=401, detail=err_msg)
        if "403" in err_msg or "permission" in err_msg.lower():
            raise HTTPException(status_code=403, detail=err_msg)
        raise HTTPException(status_code=502, detail=err_msg)
    except Exception as e:
        logger.error(f"Error creating Zoho composite item: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create composite item: {str(e)}")


@router.put(
    "/zoho/composite-items/{composite_item_id}",
    response_model=ZohoCompositeItemResponse,
    summary="Update an existing composite item in Zoho Books",
)
async def update_zoho_composite_item(
    composite_item_id: str,
    req: ZohoCompositeItemUpdateRequest,
    organization_id: str | None = None,
):
    """Updates an existing composite item in Zoho Books using PUT /books/v3/compositeitems/{id}."""
    try:
        payload = req.model_dump(exclude_none=True)
        res = zoho_books_service.update_composite_item(
            composite_item_id=composite_item_id,
            payload=payload,
            organization_id=organization_id,
        )
        return ZohoCompositeItemResponse(
            success=True,
            composite_item_id=res.get("composite_item_id"),
            message=res.get("message", "Composite item updated successfully"),
            composite_item=res.get("composite_item"),
        )
    except ValueError as ve:
        if "not found" in str(ve).lower() or "404" in str(ve):
            raise HTTPException(status_code=404, detail=str(ve))
        raise HTTPException(status_code=400, detail=str(ve))
    except RuntimeError as re:
        err_msg = str(re)
        if "401" in err_msg or "authentication" in err_msg.lower():
            raise HTTPException(status_code=401, detail=err_msg)
        if "403" in err_msg or "permission" in err_msg.lower():
            raise HTTPException(status_code=403, detail=err_msg)
        raise HTTPException(status_code=502, detail=err_msg)
    except Exception as e:
        logger.error(f"Error updating Zoho composite item: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update composite item: {str(e)}")


@router.get(
    "/zoho/composite-items",
    summary="Fetch read-only list of composite items from Zoho Books",
)
async def list_zoho_composite_items(
    search: str | None = None,
    organization_id: str | None = None,
):
    """Fetches list of composite items from Zoho Books."""
    try:
        res = zoho_books_service.list_composite_items(
            organization_id=organization_id,
            search_text=search,
        )
        if not res.get("success", False):
            status = res.get("http_status") or 500
            if status in (401, 403, 404):
                raise HTTPException(status_code=status, detail=res.get("error") or res.get("message") or "Failed to fetch composite items")
            raise HTTPException(status_code=502, detail=res.get("error") or res.get("message") or "Zoho API error fetching composite items")
        return res
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching Zoho composite items: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch composite items: {str(e)}")


@router.get(
    "/zoho/composite-items/{composite_item_id}",
    summary="Fetch read-only details of a composite item from Zoho Books",
)
async def get_zoho_composite_item(
    composite_item_id: str,
    organization_id: str | None = None,
):
    """Fetches details of a single composite item from Zoho Books."""
    try:
        return zoho_books_service.get_composite_item(
            composite_item_id=composite_item_id,
            organization_id=organization_id,
        )
    except ValueError as ve:
        if "not found" in str(ve).lower() or "404" in str(ve):
            raise HTTPException(status_code=404, detail=str(ve))
        raise HTTPException(status_code=400, detail=str(ve))
    except RuntimeError as re:
        err_msg = str(re)
        if "401" in err_msg or "authentication" in err_msg.lower():
            raise HTTPException(status_code=401, detail=err_msg)
        raise HTTPException(status_code=502, detail=err_msg)
    except Exception as e:
        logger.error(f"Error fetching Zoho composite item: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch composite item: {str(e)}")


@router.get("/history", response_model=SupplierPricingHistoryListResponse, summary="List supplier pricing & Zoho Books sync history")
async def list_supplier_pricing_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(15, ge=1, le=100),
    search: str | None = None,
    status: str | None = None,
    action: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
):
    """Returns paginated, searchable, filtered audit history of supplier pricing & Zoho Books synchronizations."""
    try:
        records, total_count, total_pages, summary_stats = supplier_pricing_history_service.list_history(
            page=page,
            page_size=page_size,
            search=search,
            status=status,
            action=action,
            start_date=start_date,
            end_date=end_date,
        )
        return SupplierPricingHistoryListResponse(
            success=True,
            records=records,
            total_count=total_count,
            total_pages=total_pages,
            current_page=page,
            summary_stats=SupplierPricingHistoryStats(**summary_stats),
        )
    except Exception as e:
        logger.error(f"Error listing supplier pricing history: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve supplier pricing history: {str(e)}"
        )


@router.get("/history/{history_id}", response_model=SupplierPricingHistoryDetail, summary="Get full read-only history record details")
async def get_supplier_pricing_history_detail(history_id: str):
    """Retrieves complete read-only details of a processed quotation and its Zoho Books sync results."""
    try:
        record = supplier_pricing_history_service.get_history_detail(history_id)
        if not record:
            raise HTTPException(status_code=404, detail="History record not found.")
        return SupplierPricingHistoryDetail(**record)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving history detail {history_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve history detail: {str(e)}"
        )

