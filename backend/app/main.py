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
    auth,
    cache,
    datasources,
    gene_annotations,
    gene_staging,
    genes,
    ingestion,
    progress,
    shadow_tests,
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
            logger.sync_warning(
                "Failed to start auto-updates. Continuing without auto-updates.",
                error=e,
                auto_update_enabled=settings.AUTO_UPDATE_ENABLED,
            )

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
    title="Kidney Genetics Database API",
    description="RESTful API for kidney disease gene curation, evidence aggregation, and real-time data pipeline management",
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
    log_request_body=True,  # Enable comprehensive request logging
    log_response_body=False,  # Keep response logging disabled for performance
    max_body_size=50000,  # Limit body size to 50KB for storage efficiency
    slow_request_threshold_ms=1000,
    exclude_paths=["/health", "/docs", "/redoc", "/openapi.json", "/api/admin/logs"],
)

# Register standardized error handlers (enhanced by logging middleware)
register_error_handlers(app)

# Include routers - organized by functional areas
# 0. Authentication - User management and auth
app.include_router(auth.router, tags=["Authentication"])

# 1. Core Resources - Primary domain entities
app.include_router(genes.router, prefix="/api/genes", tags=["Core Resources - Genes"])
app.include_router(
    gene_annotations.router, prefix="/api/annotations", tags=["Core Resources - Annotations"]
)
app.include_router(
    datasources.router, prefix="/api/datasources", tags=["Core Resources - Data Sources"]
)

# 2. Data Pipeline - Ingestion and processing operations
app.include_router(gene_staging.router, prefix="/api/staging", tags=["Pipeline - Staging"])
app.include_router(ingestion.router, prefix="/api/ingestion", tags=["Pipeline - Ingestion"])
app.include_router(progress.router, prefix="/api/progress", tags=["Pipeline - Progress Monitoring"])

# 3. Analytics - Statistics and reporting
app.include_router(statistics.router, prefix="/api/statistics", tags=["Analytics"])

# 4. Administration - System management and monitoring
app.include_router(admin_logs.router, prefix="/api/admin/logs", tags=["Administration - Logging"])
app.include_router(
    cache.router, prefix="/api/admin/cache", tags=["Administration - Cache Management"]
)
app.include_router(
    shadow_tests.router, prefix="/api/admin/shadow-tests", tags=["Administration - Shadow Testing"]
)


@app.get("/", tags=["System"])
async def root() -> dict[str, str]:
    """Root endpoint - API information"""
    return {
        "service": "Kidney Genetics Database API",
        "version": settings.APP_VERSION,
        "documentation": "/docs",
    }


@app.get("/health", tags=["System"])
async def health_check() -> dict[str, str]:
    """Health check endpoint for monitoring and load balancers"""
    # Test database connection
    try:
        from sqlalchemy import text

        db: Session = next(get_db())
        db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        db_status = f"error: {e!s}"
    finally:
        if "db" in locals():
            db.close()

    return {
        "status": "healthy",
        "service": "kidney-genetics-api",
        "version": settings.APP_VERSION,
        "database": db_status,
    }
