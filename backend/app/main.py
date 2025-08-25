"""
Kidney Genetics Database API
Main FastAPI application
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.api.endpoints import (
    admin_logs,
    cache,
    datasources,
    gene_annotations,
    gene_staging,
    genes,
    ingestion,
    progress,
    statistics,
)
from app.core.background_tasks import task_manager
from app.core.config import settings
from app.core.database import engine, get_db
from app.core.events import event_bus
from app.core.logging import configure_logging, get_logger
from app.core.startup import run_startup_tasks
from app.middleware.error_handling import register_error_handlers
from app.middleware.logging_middleware import LoggingMiddleware
from app.models import Base

# Configure unified logging system
configure_logging(log_level="DEBUG", database_enabled=True, console_enabled=True)

# Get unified logger for main application
logger = get_logger(__name__)

# Create database tables
Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle - start/stop background tasks and event bus"""
    # Startup
    logger.sync_info("Starting application...")

    # Run startup tasks (register data sources, etc.)
    run_startup_tasks()

    # Start event bus for WebSocket pub/sub pattern - REPLACES POLLING!
    logger.sync_info("Starting event bus for optimized WebSocket communication...")
    await event_bus.start()

    logger.sync_info("Starting background task manager...")

    # Set up broadcast callback for WebSocket updates (now uses event bus internally)
    from app.api.endpoints.progress import get_connection_manager

    manager = get_connection_manager()
    task_manager.set_broadcast_callback(manager.broadcast)

    # Start auto-updates for data sources
    if settings.AUTO_UPDATE_ENABLED:
        try:
            await task_manager.start_auto_updates()
        except Exception as e:
            logger.sync_warning("Failed to start auto-updates. Continuing without auto-updates.",
                               error=e, auto_update_enabled=settings.AUTO_UPDATE_ENABLED)

    # Start annotation scheduler
    logger.sync_info("Starting annotation scheduler...")
    from app.core.scheduler import annotation_scheduler
    annotation_scheduler.start()

    yield

    # Shutdown
    logger.sync_info("Shutting down annotation scheduler...")
    annotation_scheduler.stop()

    logger.sync_info("Shutting down event bus...")
    await event_bus.stop()

    logger.sync_info("Shutting down background task manager...")
    await task_manager.shutdown()


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="API for kidney disease gene curation with real-time progress tracking",
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add unified logging middleware (replaces basic error handling)
app.add_middleware(
    LoggingMiddleware,
    log_request_body=False,  # Set to True for debugging, False for production
    log_response_body=False, # Set to True for debugging, False for production
    slow_request_threshold_ms=1000,
    exclude_paths=["/health", "/docs", "/redoc", "/openapi.json"],
)

# Register standardized error handlers (enhanced by logging middleware)
register_error_handlers(app)

# Include routers
app.include_router(genes.router, prefix="/api/genes", tags=["genes"])
app.include_router(gene_annotations.router, prefix="/api/annotations", tags=["annotations"])
app.include_router(datasources.router, prefix="/api/datasources", tags=["datasources"])
app.include_router(gene_staging.router, prefix="/api/staging", tags=["gene-staging"])
app.include_router(progress.router, prefix="/api/progress", tags=["progress"])
app.include_router(cache.router, prefix="/api/admin/cache", tags=["cache-admin"])
app.include_router(admin_logs.router)  # Admin logs management (already has prefix)
app.include_router(statistics.router, prefix="/api/statistics", tags=["statistics"])
app.include_router(ingestion.router)


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint"""
    return {"message": "Kidney Genetics API", "version": "0.1.0"}


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint"""
    # Test database connection
    try:
        from sqlalchemy import text

        db: Session = next(get_db())
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {e!s}"
    finally:
        if "db" in locals():
            db.close()

    return {"status": "healthy", "service": "kidney-genetics-api", "database": db_status}


@app.get("/api/test")
async def test_endpoint() -> dict[str, str]:
    """Test endpoint to verify API routing"""
    return {"message": "API is working!", "path": "/api/test"}
