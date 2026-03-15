"""
Kidney Genetics Database API
Main FastAPI application
"""

import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy.orm import Session

from app.api.endpoints import (
    admin_backups,
    admin_logs,
    admin_settings,
    annotation_retrieval,
    annotation_updates,
    auth,
    cache,
    client_logs,
    datasources,
    gene_staging,
    genes,
    ingestion,
    network_analysis,
    percentile_management,
    progress,
    releases,
    seo,
    shadow_tests,
    statistics,
    version,
)
from app.core.background_tasks import task_manager
from app.core.config import settings
from app.core.database import engine, get_db
from app.core.events import event_bus
from app.core.exceptions import (
    AuthenticationError,
    GeneNotFoundError,
    KidneyGeneticsException,
    PermissionDeniedError,
    RateLimitExceededError,
    ResourceConflictError,
)
from app.core.exceptions import ValidationError as DomainValidationError
from app.core.logging import configure_logging, get_logger
from app.core.rate_limit import limiter
from app.core.startup import run_startup_tasks
from app.middleware.error_handling import register_error_handlers
from app.middleware.logging_middleware import LoggingMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.models import Base

# Configure unified logging system
configure_logging(log_level=settings.LOG_LEVEL, database_enabled=True, console_enabled=True)

# Get unified logger for main application
logger = get_logger(__name__)

# Create database tables
Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifecycle - start/stop background tasks and event bus"""
    # Startup
    logger.sync_info("Starting application...")

    # Initialize database (admin user, views, etc.) - MUST run in async context
    from app.core.database_init import initialize_database

    db = next(get_db())
    try:
        init_status = await initialize_database(db)
        await logger.info(
            "Database initialization completed",
            views_created=init_status.get("views_created"),
            admin_created=init_status.get("admin_created"),
            cache_cleared=init_status.get("cache_cleared"),
        )
    finally:
        db.close()

    # Run startup tasks (register data sources, etc.)
    run_startup_tasks()

    # Seed initial evidence data if database is empty
    from app.core.initial_seeder import needs_initial_seeding, run_initial_seeding

    seed_db = next(get_db())
    try:
        if needs_initial_seeding(seed_db):
            logger.sync_info(
                "Empty database detected — running initial seeding from seed files"
            )
            seed_results = await run_initial_seeding(seed_db)
            logger.sync_info("Initial seeding results", results=seed_results)
        else:
            logger.sync_debug("Database already has evidence data — skipping seeding")
    except Exception as e:
        logger.sync_warning(
            "Initial seeding failed — pipeline will populate data later",
            error=str(e),
        )
    finally:
        seed_db.close()

    # Start event bus for WebSocket pub/sub pattern - REPLACES POLLING!
    logger.sync_info("Starting event bus for optimized WebSocket communication...")
    await event_bus.start()

    logger.sync_info("Starting background task manager...")

    # Set up broadcast callback for WebSocket updates (now uses event bus internally)
    from app.api.endpoints.progress import get_connection_manager

    manager = get_connection_manager()
    task_manager.set_broadcast_callback(manager.broadcast)

    # Start annotation scheduler (cron-based maintenance updates)
    logger.sync_info("Starting annotation scheduler...")
    from app.core.scheduler import annotation_scheduler

    annotation_scheduler.start()

    # Start pipeline orchestrator (evidence -> annotations -> aggregation)
    if settings.AUTO_UPDATE_ENABLED:
        try:
            from app.core.pipeline_orchestrator import PipelineOrchestrator

            orchestrator = PipelineOrchestrator(task_manager)
            task_manager.orchestrator = orchestrator
            await orchestrator.start_pipeline()
        except Exception as e:
            logger.sync_warning(
                "Failed to start pipeline. Continuing without auto-updates.",
                error=e,
            )

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
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Request-ID", "X-Requested-With"],
    max_age=600,  # Cache preflight for 10 minutes
)

# Security headers
app.add_middleware(SecurityHeadersMiddleware)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Add unified logging middleware (replaces basic error handling)
app.add_middleware(
    LoggingMiddleware,
    log_request_body=True,  # Enable comprehensive request logging
    log_response_body=False,  # Keep response logging disabled for performance
    max_body_size=50000,  # Limit body size to 50KB for storage efficiency
    slow_request_threshold_ms=1000,
    exclude_paths=[
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/admin/logs",
        "/sitemap.xml",
    ],
)

# Register standardized error handlers (enhanced by logging middleware)
register_error_handlers(app)


# --- Domain exception handlers ---
@app.exception_handler(GeneNotFoundError)
async def gene_not_found_handler(request: Request, exc: GeneNotFoundError) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={
            "error": {
                "type": "not_found",
                "message": exc.message,
                "error_id": str(uuid.uuid4()),
            },
        },
    )


@app.exception_handler(DomainValidationError)
async def domain_validation_handler(request: Request, exc: DomainValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "type": "validation_error",
                "message": exc.message,
                "error_id": str(uuid.uuid4()),
            },
        },
    )


@app.exception_handler(AuthenticationError)
async def authentication_handler(request: Request, exc: AuthenticationError) -> JSONResponse:
    return JSONResponse(
        status_code=401,
        content={
            "error": {
                "type": "authentication_error",
                "message": exc.message,
                "error_id": str(uuid.uuid4()),
            },
        },
    )


@app.exception_handler(PermissionDeniedError)
async def permission_denied_handler(request: Request, exc: PermissionDeniedError) -> JSONResponse:
    return JSONResponse(
        status_code=403,
        content={
            "error": {
                "type": "permission_denied",
                "message": exc.message,
                "error_id": str(uuid.uuid4()),
            },
        },
    )


@app.exception_handler(ResourceConflictError)
async def resource_conflict_handler(request: Request, exc: ResourceConflictError) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={
            "error": {
                "type": "resource_conflict",
                "message": exc.message,
                "error_id": str(uuid.uuid4()),
            },
        },
    )


@app.exception_handler(RateLimitExceededError)
async def rate_limit_handler(request: Request, exc: RateLimitExceededError) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={
            "error": {
                "type": "rate_limit_exceeded",
                "message": exc.message,
                "error_id": str(uuid.uuid4()),
            },
        },
        headers={"Retry-After": str(exc.retry_after)} if exc.retry_after else {},
    )


@app.exception_handler(KidneyGeneticsException)
async def kidney_genetics_handler(request: Request, exc: KidneyGeneticsException) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "type": "internal_error",
                "message": exc.message,
                "error_id": str(uuid.uuid4()),
            },
        },
    )


# Include routers - organized by functional areas
# 0. System - Health, version, SEO, and root endpoints
app.include_router(version.router, tags=["System"])
app.include_router(seo.router, tags=["System"])

# 1. Authentication - User management and auth
app.include_router(auth.router, tags=["Authentication"])

# 2. Core Resources - Primary domain entities
app.include_router(genes.router, prefix="/api/genes", tags=["Core Resources - Genes"])
app.include_router(
    annotation_retrieval.router, prefix="/api/annotations", tags=["Core Resources - Annotations"]
)
app.include_router(
    annotation_updates.router, prefix="/api/annotations", tags=["Core Resources - Annotations"]
)
app.include_router(
    percentile_management.router,
    prefix="/api/annotations",
    tags=["Core Resources - Annotations"],
)
app.include_router(
    datasources.router, prefix="/api/datasources", tags=["Core Resources - Data Sources"]
)
app.include_router(releases.router, prefix="/api/releases", tags=["Core Resources - Data Releases"])

# 3. Data Pipeline - Ingestion and processing operations
app.include_router(gene_staging.router, prefix="/api/staging", tags=["Pipeline - Staging"])
app.include_router(ingestion.router, prefix="/api/ingestion", tags=["Pipeline - Ingestion"])
app.include_router(progress.router, prefix="/api/progress", tags=["Pipeline - Progress Monitoring"])

# 4. Analytics - Statistics and reporting
app.include_router(statistics.router, prefix="/api/statistics", tags=["Analytics - Statistics"])
app.include_router(
    network_analysis.router,
    prefix="/api/network",
    tags=["Analytics - Network Analysis & Enrichment"],
)

# 5. Client reporting - Frontend error logging
app.include_router(client_logs.router, prefix="/api", tags=["Client Reporting"])

# 6. Administration - System management and monitoring
app.include_router(admin_logs.router, prefix="/api/admin/logs", tags=["Administration - Logging"])
app.include_router(
    admin_backups.router, prefix="/api/admin/backups", tags=["Administration - Backups"]
)
app.include_router(
    admin_settings.router, prefix="/api/admin/settings", tags=["Administration - Settings"]
)
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
