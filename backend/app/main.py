"""
Kidney Genetics Database API
Main FastAPI application
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.api.endpoints import datasources, genes
from app.core.config import settings
from app.core.database import engine, get_db
from app.models import Base

# Create database tables
Base.metadata.create_all(bind=engine)

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="API for kidney disease gene curation",
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
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
