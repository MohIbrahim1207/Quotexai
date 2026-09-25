import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.api import health, quotation, history, supplier_pricing

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Enterprise AI PDF to Excel Quotation Converter with formatting preservation and leading zero protection.",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS setup
origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    settings.FRONTEND_URL,
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.FRONTEND_URL == "*" else origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global error handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error on {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal Server Error",
            "detail": str(exc),
        },
    )

# Include API routers
app.include_router(health.router, prefix=settings.API_V1_STR)
app.include_router(quotation.router, prefix=settings.API_V1_STR)
app.include_router(history.router, prefix=settings.API_V1_STR)
app.include_router(supplier_pricing.router, prefix=settings.API_V1_STR)


@app.get("/health", tags=["Health"])
async def root_health_check():
    """Root health check endpoint for Docker and load balancers."""
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "ai_model": settings.GEMINI_MODEL,
        "gemini_api_configured": bool(settings.GEMINI_API_KEY),
    }


@app.on_event("startup")
async def startup_event():
    logger.info(f"=== {settings.PROJECT_NAME} v{settings.VERSION} starting up ===")
    logger.info(f"Gemini API configured: {bool(settings.GEMINI_API_KEY)}")
    logger.info(f"Using model: {settings.GEMINI_MODEL}")


@app.get("/")
async def root():
    return {
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": "/docs",
        "health": f"{settings.API_V1_STR}/health",
    }
