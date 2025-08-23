"""
Kidney Genetics Database API
Main FastAPI application
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.api.endpoints import cache, datasources, gene_staging, genes, ingestion, progress
from app.core.background_tasks import task_manager
from app.core.config import settings
from app.core.database import engine, get_db
from app.core.events import event_bus
from app.core.startup import run_startup_tasks
from app.models import Base

# FORCE DEBUG LOGGING TO WORK
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", force=True
)
# Set uvicorn loggers to DEBUG
logging.getLogger("uvicorn").setLevel(logging.DEBUG)
logging.getLogger("uvicorn.access").setLevel(logging.DEBUG)
logging.getLogger("uvicorn.error").setLevel(logging.DEBUG)
# Set our app loggers to DEBUG
logging.getLogger("app").setLevel(logging.DEBUG)
logging.getLogger("app.core").setLevel(logging.DEBUG)
logging.getLogger("app.api").setLevel(logging.DEBUG)
logging.getLogger("app.pipeline").setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)

# Create database tables
Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle - start/stop background tasks and event bus"""
    # Startup
    logger.info("Starting application...")

    # Run startup tasks (register data sources, etc.)
    run_startup_tasks()

    # Start event bus for WebSocket pub/sub pattern - REPLACES POLLING!
    logger.info("Starting event bus for optimized WebSocket communication...")
    await event_bus.start()

    logger.info("Starting background task manager...")

    # Set up broadcast callback for WebSocket updates (now uses event bus internally)
    from app.api.endpoints.progress import get_connection_manager

    manager = get_connection_manager()
    task_manager.set_broadcast_callback(manager.broadcast)

    # Start auto-updates for data sources
    if settings.AUTO_UPDATE_ENABLED:
        try:
            await task_manager.start_auto_updates()
        except Exception as e:
            logger.warning(f"Failed to start auto-updates: {e}. Continuing without auto-updates.")

    yield

    # Shutdown
    logger.info("Shutting down event bus...")
    await event_bus.stop()

    logger.info("Shutting down background task manager...")
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

# Include routers
app.include_router(genes.router, prefix="/api/genes", tags=["genes"])
app.include_router(datasources.router, prefix="/api/datasources", tags=["datasources"])
app.include_router(gene_staging.router, prefix="/api/staging", tags=["gene-staging"])
app.include_router(progress.router, prefix="/api/progress", tags=["progress"])
app.include_router(cache.router, prefix="/api/admin/cache", tags=["cache-admin"])
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
