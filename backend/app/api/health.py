from fastapi import APIRouter
from app.config import settings

router = APIRouter()


@router.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "ai_model": settings.GEMINI_MODEL,
        "gemini_api_configured": bool(settings.GEMINI_API_KEY),
    }
