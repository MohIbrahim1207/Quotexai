import logging
from typing import Optional
from fastapi import APIRouter, Query, HTTPException

from app.services.history_service import history_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/history", tags=["History"])


@router.get("", summary="List conversion history records")
async def list_history(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(15, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search by quote number, customer, or filename"),
    status: Optional[str] = Query(None, description="Filter by status (e.g. generated, verified, warning, error)"),
):
    """Returns paginated conversion history records with search and status filtering."""
    try:
        records, total_count, total_pages = history_service.list_records(
            page=page,
            limit=limit,
            search=search,
            status=status,
        )
        return {
            "success": True,
            "records": records,
            "total": total_count,
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
        }
    except Exception as e:
        logger.error(f"Failed to list history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve conversion history: {str(e)}")


@router.get("/{conversion_id}", summary="Get single conversion record")
async def get_conversion(conversion_id: str):
    """Retrieves full conversion details including quotation data and validation summary."""
    record = history_service.get_record(conversion_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Conversion record '{conversion_id}' not found.")
    return {
        "success": True,
        "record": record,
    }


@router.delete("/{conversion_id}", summary="Delete a conversion record")
async def delete_conversion(conversion_id: str):
    """Deletes a specific conversion record from history."""
    deleted = history_service.delete_record(conversion_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Conversion record '{conversion_id}' not found.")
    return {
        "success": True,
        "message": f"Conversion record '{conversion_id}' deleted.",
    }


@router.post("/clear", summary="Clear all conversion records")
async def clear_all_history():
    """Clears all conversion records."""
    history_service.clear_all()
    return {
        "success": True,
        "message": "All conversion history cleared.",
    }
