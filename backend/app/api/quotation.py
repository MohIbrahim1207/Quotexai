import os
import logging
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse

from app.config import settings, UPLOAD_DIR, OUTPUT_DIR, TEMPLATE_DIR, SAMPLE_DIR
from app.schemas.quotation import (
    QuotationData,
    ExtractionResponse,
    ValidationSummary,
    GenerateExcelRequest,
    GenerateExcelResponse,
    TemplateAnalysisResponse,
)
from app.services.quotation_service import quotation_orchestrator
from app.services.validation_service import validation_service
from app.services.excel_service import excel_service
from app.utils.file_utils import save_uploaded_file, get_file_path

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/quotation", tags=["Quotation"])


@router.post("/upload-pdf", summary="Upload supplier quotation PDF")
async def upload_pdf(file: UploadFile = File(...)):
    """Uploads and saves a supplier quotation PDF."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")
    
    file_id, dest_path = await save_uploaded_file(file, UPLOAD_DIR)
    logger.info(f"PDF uploaded successfully: {file.filename} -> {file_id}")
    return {
        "success": True,
        "file_id": file_id,
        "filename": file.filename,
        "size_bytes": dest_path.stat().st_size,
    }


@router.post("/upload-template", summary="Upload Excel quotation template")
async def upload_template(file: UploadFile = File(...)):
    """Uploads and saves an Excel quotation template (.xlsx or .xlsm)."""
    if not file.filename.lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(status_code=400, detail="Only .xlsx or .xlsm files are allowed.")
    
    file_id, dest_path = await save_uploaded_file(file, TEMPLATE_DIR)
    logger.info(f"Excel template uploaded successfully: {file.filename} -> {file_id}")

    # Analyze template headers immediately
    try:
        analysis = excel_service.analyze_template(dest_path)
    except Exception as e:
        logger.warning(f"Could not auto-analyze template {file_id}: {e}")
        analysis = None

    return {
        "success": True,
        "template_id": file_id,
        "filename": file.filename,
        "size_bytes": dest_path.stat().st_size,
        "analysis": analysis,
    }


@router.post("/extract", response_model=ExtractionResponse, summary="Extract and analyze quotation from PDF")
async def extract_quotation(
    pdf_id: str = Form(...),
    template_id: str = Form(None),
):
    """Processes uploaded PDF, extracts structured items using Gemini AI, and validates."""
    pdf_path = get_file_path(pdf_id, [UPLOAD_DIR, SAMPLE_DIR])
    if not pdf_path:
        raise HTTPException(
            status_code=404,
            detail=f"Quotation PDF '{pdf_id}' not found. Please upload again."
        )

    try:
        response = await quotation_orchestrator.process_pdf_quotation(
            pdf_path=pdf_path,
            source_pdf_id=pdf_id,
            template_id=template_id,
        )
        return response
    except Exception as e:
        logger.error(f"Extraction error for {pdf_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to extract quotation: {str(e)}"
        )


@router.post("/validate", response_model=ValidationSummary, summary="Validate updated quotation data")
async def validate_quotation(quotation: QuotationData):
    """Re-runs deterministic validation against quotation data."""
    _, summary = validation_service.validate_quotation(quotation)
    return summary


@router.post("/analyze-template", response_model=TemplateAnalysisResponse, summary="Inspect template columns")
async def analyze_template(template_id: str = Form(...)):
    """Inspects an Excel template to discover headers and suggest column mappings."""
    template_path = get_file_path(template_id, [TEMPLATE_DIR, UPLOAD_DIR, SAMPLE_DIR])
    if not template_path:
        raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found.")
    
    return excel_service.analyze_template(template_path)


@router.post("/generate", response_model=GenerateExcelResponse, summary="Generate filled Excel quotation")
async def generate_excel(request: GenerateExcelRequest):
    """Fills the template with approved quotation data and generates a downloadable .xlsx file."""
    try:
        return quotation_orchestrator.generate_excel_quotation(request)
    except Exception as e:
        logger.error(f"Excel generation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Excel generation error: {str(e)}"
        )


@router.get("/download/{file_id}", summary="Download generated Excel file")
async def download_file(file_id: str):
    """Serves the generated Excel file as a download."""
    file_path = get_file_path(file_id, [OUTPUT_DIR])
    if not file_path or not file_path.exists():
        raise HTTPException(status_code=404, detail="Requested file not found or has expired.")

    # Clean download name
    download_name = file_path.name
    if "_" in download_name:
        parts = download_name.split("_", 2)
        if len(parts) >= 3:
            download_name = parts[2]

    return FileResponse(
        path=str(file_path),
        filename=download_name,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
