"""
Kidney Genetics Database API
Main FastAPI application
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.api.endpoints import datasources, gene_staging, genes, progress
from app.core.background_tasks import task_manager
from app.core.config import settings
from app.core.database import engine, get_db
from app.core.startup import run_startup_tasks
from app.models import Base

logger = logging.getLogger(__name__)

# Create database tables
Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle - start/stop background tasks"""
    # Startup
    logger.info("Starting application...")

    # Run startup tasks (register data sources, etc.)
    run_startup_tasks()

    logger.info("Starting background task manager...")

    # Set up broadcast callback for WebSocket updates
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
        db_status = f"error: {str(e)}"
    finally:
        if "db" in locals():
            db.close()

    return {"status": "healthy", "service": "kidney-genetics-api", "database": db_status}


@app.get("/api/test")
async def test_endpoint() -> dict[str, str]:
    """Test endpoint to verify API routing"""
    return {"message": "API is working!", "path": "/api/test"}
