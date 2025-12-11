from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from datetime import datetime
import logging

from config.settings import get_settings
from config.logging_config import setup_logging
from db.session import engine
from db.models import Base
from api.project_router import router as project_router
from api.document_router import router as document_router
from api.chat_router import router as chat_router
from api.schemas import HealthResponse

settings = get_settings()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    setup_logging(
        log_level=settings.log_level,
        log_file=settings.log_file,  # Always log to file for debugging
        enable_console=settings.log_to_console
    )
    
    logger.info("Starting AI Brain application...")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Version: {settings.app_version}")
    logger.info(f"Database: {settings.database_url.split('@')[-1]}")  # Hide credentials
    
    # Check Redis/Celery availability
    try:
        import redis
        r = redis.from_url(settings.celery_broker_url)
        r.ping()
        logger.info("✅ Redis connection successful - Async processing enabled")
        print("\n✅ Redis connected - Async document processing available\n")
    except Exception as e:
        logger.warning(f"⚠️ Redis not available: {e}")
        print("\n" + "=" * 70)
        print("⚠️  WARNING: Redis/Celery not running")
        print("=" * 70)
        print("Document ingestion will use SYNCHRONOUS processing (slower).")
        print("\nTo enable async processing:")
        print("  1. Install Redis: choco install redis-64 (run as Administrator)")
        print("  2. Start Redis: redis-server")
        print("  3. Start Celery worker: python start_celery_worker.py")
        print("\nCurrent mode: Synchronous (documents processed during upload)")
        print("=" * 70 + "\n")
    
    yield
    
    # Shutdown
    logger.info("Shutting down AI Brain application...")
    await engine.dispose()
    logger.info("Database connections closed")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-powered document analysis system for real estate with RAG capabilities",
    lifespan=lifespan,
    debug=settings.debug
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(project_router, prefix=settings.api_v1_prefix)
app.include_router(document_router, prefix=settings.api_v1_prefix)
app.include_router(chat_router, prefix=settings.api_v1_prefix)

# Mount UI static files (Sprint 4)
app.mount("/ui", StaticFiles(directory="ui", html=True), name="ui")


@app.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    tags=["Health"]
)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        timestamp=datetime.utcnow()
    )


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint."""
    return {
        "message": "AI Brain API - Real Estate Document Analysis",
        "version": settings.app_version,
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )
