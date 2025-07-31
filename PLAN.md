# Kidney-Genetics Database Modernization Plan

## Executive Summary

This document outlines the comprehensive migration strategy for transforming the existing R-based kidney-genetics project into a modern, scalable web application. The current system is a sophisticated bioinformatics pipeline that curates approximately 3,000 kidney disease-related genes from 5 major data sources, producing timestamped, versioned datasets with complex evidence scoring and clinical annotations.

### Current State
- **Language**: R-based analysis scripts with manual execution
- **Data Volume**: ~3,000 curated genes with 25+ complex metadata fields
- **Data Sources**: PanelApp, Literature, Diagnostic Panels, HPO, PubTator
- **Output Format**: Timestamped CSV files with nested string data
- **Documentation**: Bookdown-generated GitHub Pages site
- **Update Frequency**: Manual, periodic execution with date-based versioning

### Target Architecture
- **Backend**: Python FastAPI with Celery for background processing
- **Database**: PostgreSQL with hybrid JSONB + normalized table structure
- **Frontend**: Vue.js/Vite/Vuetify SPA with interactive data exploration
- **Deployment**: Docker-based containerized architecture
- **Updates**: Automated scheduling with real-time progress tracking

### Implementation Overview
- **Parallel Development**: New system built alongside existing R pipeline
- **Validation Period**: Parallel execution and output comparison phase
- **Gradual Cutover**: Component-by-component migration with rollback capability

---

## Insights from Similar Python Refactor (laborberlin/custom-panel)

### Key Learnings from Parallel Implementation

The laborberlin/custom-panel project provides an excellent blueprint for our kidney-genetics modernization, as it successfully refactored a similar R-based genomic data aggregation pipeline to Python. Here are the critical insights:

#### Architecture Patterns Successfully Applied

**1. Modular Pipeline Design**
- **Centralized Orchestrator**: `Pipeline` class coordinates entire workflow
- **Plugin-based Sources**: Each data source (g01_panelapp.py, g02_hpo.py, etc.) follows consistent interface
- **Separation of Concerns**: Clear boundaries between data fetching, processing, and output generation
- **Configuration-driven**: YAML-based configuration with environment-specific overrides

**2. Modern Python Toolchain**
- **Poetry**: Dependency management with clear dev/prod separation
- **Typer**: Rich CLI with excellent user experience
- **Pydantic/Type Hints**: Comprehensive type safety throughout codebase
- **Ruff**: Fast linting and formatting (replacing flake8, black, isort)
- **MyPy**: Strict type checking with generics enforcement

**3. Data Processing Excellence**
- **Pandas-centric**: Standardized DataFrame operations throughout pipeline
- **Caching Layer**: `CacheManager` for API response caching and performance
- **Robust Error Handling**: Network resilience with retry logic and graceful degradation
- **Multiple Output Formats**: Excel, CSV, Parquet, BED files with consistent schemas

#### Directly Applicable Components for Kidney-Genetics

**1. Web Scraping Infrastructure** (`scrapers/parsers/`)
- **Blueprint Genetics Parser**: Direct relevance - kidney-genetics already scrapes Blueprint
- **Base Parser Pattern**: Extensible framework for adding new commercial panel scrapers
- **Error Recovery**: Network timeout handling and retry mechanisms
- **JSON Output Format**: Structured data extraction for downstream processing

**2. API Integration Patterns**
- **PanelApp Client**: Nearly identical to kidney-genetics PanelApp integration
- **HGNC Standardization**: Same gene symbol normalization requirements
- **HPO Integration**: Phenotype ontology processing (kidney-genetics uses HPO extensively)
- **Rate Limiting**: Built-in API throttling to respect service limits

**3. Configuration Management**
- **Nested Configuration Access**: `ConfigManager` with safe key traversal
- **Environment Overrides**: `config.local.yml` for sensitive API keys
- **Source Toggling**: Enable/disable individual data sources via configuration
- **Scoring Weights**: Configurable evidence weighting system

**4. Data Standardization Pipeline**
- **Standard DataFrame Schema**: Consistent column naming across all sources
- **Gene Symbol Validation**: HGNC-based standardization with conflict resolution
- **Metadata Tracking**: Source provenance and processing timestamps
- **Quality Control**: Automated data validation and integrity checks

#### Technical Improvements to Adopt

**1. Enhanced Testing Strategy**
```python
# Test structure directly applicable to kidney-genetics
tests/
├── test_cli.py              # CLI functionality
├── test_sources.py          # Individual data source testing  
├── test_engine.py           # Pipeline integration testing
├── test_scrapers.py         # Web scraping validation
└── test_utils.py            # Utility function testing
```

**2. Modern Development Workflow**
```bash
# Quality assurance automation
./scripts/lint.sh            # Comprehensive code quality
./scripts/coverage.sh html   # Detailed test coverage
poetry run mypy              # Strict type checking
```

**3. Improved Output Management**
- **Timestamped Run Directories**: Preserves historical execution results
- **Intermediate File Preservation**: Debug capability with `--save-intermediate`
- **Rich Console Output**: Progress bars and structured logging
- **HTML Report Generation**: Interactive data exploration interface

#### Migration Strategy Refinements

Based on laborberlin/custom-panel's successful approach:

**Foundation Enhancement**
- Adopt Poetry for dependency management (replacing conda/pip requirements)
- Implement comprehensive type hints from day one
- Set up Ruff for linting/formatting (single tool vs. multiple)
- Create base classes for data sources following their plugin pattern

**Pipeline Architecture Enhancement**  
- Use their Pipeline orchestrator pattern as template
- Implement CacheManager for API response caching
- Adopt their configuration management system
- Integrate rich console output for better user experience

**Data Processing Enhancement**
- Leverage their DataFrame standardization patterns
- Implement their multi-format output system (Excel, CSV, Parquet, BED)
- Use their gene symbol normalization approach
- Adapt their quality control and validation framework

**Web Scraping Enhancement**
- Directly port their Blueprint Genetics parser (shared data source)
- Adapt their base parser framework for other diagnostic panels
- Use their JSON-based scraper output format
- Implement their error handling and retry mechanisms

#### Code Reuse Opportunities

**Direct Adaptations:**
1. **Blueprint Genetics Scraper**: Identical data source, parser directly transferable
2. **PanelApp Client**: Same API, can adapt their caching and error handling
3. **HGNC Integration**: Gene standardization logic directly applicable
4. **Configuration System**: YAML-based config management pattern
5. **CLI Framework**: Typer-based interface with rich output

**Architectural Patterns:**
1. **Plugin System**: Source modules following consistent interface
2. **Pipeline Orchestration**: Central coordinator with modular components
3. **Error Handling**: Network resilience and graceful degradation
4. **Output Management**: Multi-format, timestamped result preservation
5. **Testing Strategy**: Comprehensive test coverage with mocked dependencies

---

## Current System Analysis

### Architecture Overview
The existing kidney-genetics project follows a modular R-based pipeline:

```
Input Data Sources → Individual Analysis Scripts → Merge → Annotate → Output CSVs
```

### Data Processing Pipeline

#### Phase 1: Data Collection (Scripts 01-05)
1. **01_PanelApp** (`01_PanelApp.R`)
   - Fetches kidney-related gene panels from PanelApp UK and Australia
   - Processes JSON panel data and extracts gene evidence levels
   - Outputs: Timestamped gene and panel CSV files

2. **02_Literature** (`02_Literature.R`)
   - Manual literature curation from Excel files
   - Processes publication-specific gene lists
   - Outputs: Curated gene lists with publication metadata

3. **03_DiagnosticPanels** (`03_DiagnosticPanels.R`)
   - Web scraping of commercial diagnostic panels (Blueprint Genetics, CeGaT)
   - HTML parsing to extract gene lists from nephrology panels
   - Outputs: Diagnostic panel gene lists with provider metadata

4. **04_HPO** (`04_HPO-detection.R`)
   - Human Phenotype Ontology API integration
   - Kidney-related phenotype term detection and gene mapping
   - Outputs: HPO-based gene associations with phenotype metadata

5. **05_PubTator** (`05_PubTator.R`)
   - Literature mining via PubTator API
   - Automated gene-disease association extraction
   - Outputs: Literature-derived gene associations

#### Phase 2: Data Integration (Scripts A-D)
1. **A_MergeAnalysesSources** (`A_MergeAnalysesSources.R`)
   - Combines all analysis results into unified dataset
   - Evidence counting and percentile scoring
   - Outputs: Merged gene list with evidence metrics

2. **B_AnnotationHGNC** (`B_AnnotationHGNC.R`)
   - HGNC gene nomenclature standardization
   - ClinVar clinical variant integration
   - Genomic coordinate annotation

3. **C_AnnotateMergedTable** (`C_AnnotateMergedTable.R`)
   - Complex annotation enrichment:
     - GTEx expression data (kidney cortex/medulla)
     - STRING-DB protein interaction networks
     - MGI mouse phenotype data
     - Clinical evidence scoring
   - Outputs: Final annotated gene table (25+ columns)

4. **D_ProteinInteractionAnalysis** (`D_ProteinInteractionAnalysis.R`)
   - Protein interaction network analysis
   - Network clustering and visualization
   - Community detection algorithms

### Current Data Schema
The final output contains these key fields (from latest CSV analysis):
- **Gene Identity**: `approved_symbol`, `hgnc_id`, `cur_id`
- **Evidence Metrics**: `evidence_count`, `source_count_percentile`
- **Constraint Scores**: `pLI`, `oe_lof`, `lof_z`, `mis_z`
- **Clinical Annotations**: `omim_summary`, `gencc_summary`, `clingen_summary`, `clinvar`
- **Phenotype Groups**: `clinical_groups_p`, `onset_groups_p`, `syndromic_groups_p`
- **Model Organism**: `mgi_phenotype`
- **Interactions**: `interaction_score`, `stringdb_interaction_*`
- **Expression**: `expression_score`, `gtex_kidney_*`, `descartes_kidney_tpm`

### External Dependencies
- **APIs**: PanelApp (UK/Australia), HGNC, HPO, PubTator, NCBI
- **Web Scraping**: Blueprint Genetics, CeGaT diagnostic panels
- **Data Sources**: GTEx, STRING-DB, ClinVar, OMIM, GenCC
- **Configuration**: YAML-based configuration with API keys

---

## Target Architecture Design

### Database Schema Design

#### Core Versioned Data Model
```sql
-- Primary gene registry with audit timestamps
CREATE TABLE genes (
    id SERIAL PRIMARY KEY,
    hgnc_id VARCHAR(20) UNIQUE NOT NULL,
    approved_symbol VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Version control for curation runs
CREATE TABLE curation_versions (
    id SERIAL PRIMARY KEY,
    version_number INTEGER NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    notes TEXT,
    user_id INTEGER REFERENCES users(id),
    pipeline_status VARCHAR(50) DEFAULT 'running',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Versioned gene curation data (JSONB source of truth)
CREATE TABLE gene_curations (
    id SERIAL PRIMARY KEY,
    gene_id INTEGER REFERENCES genes(id),
    version_id INTEGER REFERENCES curation_versions(id),
    curation_data JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(gene_id, version_id)
);

-- Critical: All schema changes managed via Alembic migrations from day one
-- Never create tables manually - every change must be a versioned migration

-- FIRST ACTION after defining SQLAlchemy models:
-- 1. Run: alembic init alembic
-- 2. Run: alembic revision --autogenerate -m "Initial migration"
-- 3. Run: alembic upgrade head
-- 4. Every subsequent model change MUST include a new migration file
```

#### JSONB Schema Validation at Database Level
```sql
-- Add pg_jsonschema extension for schema validation
CREATE EXTENSION IF NOT EXISTS pg_jsonschema;

-- GenCC-compatible gene_curations table with schema validation
CREATE TABLE gene_curations (
    id SERIAL PRIMARY KEY,
    gene_id INTEGER REFERENCES genes(id),
    version_id INTEGER REFERENCES curation_versions(id),
    curation_data JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(gene_id, version_id),
    
    -- Database-level GenCC-compatible schema validation
    -- References plan/schema/gene_curation.json for complete validation
    CONSTRAINT valid_curation_data CHECK (
        -- Required GenCC fields validation
        (curation_data ? 'hgnc_id') AND
        (curation_data ? 'approved_symbol') AND
        (curation_data ? 'evidence_sources') AND
        (curation_data ? 'curation_metadata') AND
        -- HGNC ID format validation
        (curation_data->>'hgnc_id' ~ '^HGNC:[0-9]+$') AND
        -- Evidence sources must be array
        (jsonb_typeof(curation_data->'evidence_sources') = 'array') AND
        -- Disease associations validation (if present)
        (CASE WHEN curation_data ? 'disease_associations' 
         THEN jsonb_typeof(curation_data->'disease_associations') = 'array'
         ELSE true END)
    )
);

-- Indexes for efficient GenCC-compatible queries
CREATE INDEX idx_gene_curations_hgnc_id ON gene_curations 
USING GIN ((curation_data->'hgnc_id'));

CREATE INDEX idx_gene_curations_clinical_validity ON gene_curations 
USING GIN ((curation_data->'disease_associations'));

CREATE INDEX idx_gene_curations_evidence_sources ON gene_curations 
USING GIN ((curation_data->'evidence_sources'));

-- GenCC submission tracking
CREATE INDEX idx_gene_curations_gencc_submitted ON gene_curations 
USING GIN ((curation_data->'curation_metadata'->'external_submissions'->'gencc_submitted'));
```

#### Database Dockerfile with Extensions
```dockerfile
# db/Dockerfile - Custom PostgreSQL with extensions
FROM postgres:15-alpine

# Install pg_jsonschema extension
RUN apk add --no-cache --virtual .build-deps \
    gcc musl-dev postgresql-dev git make \
    && git clone https://github.com/supabase/pg_jsonschema.git \
    && cd pg_jsonschema \
    && make install \
    && cd .. && rm -rf pg_jsonschema \
    && apk del .build-deps

# Copy initialization scripts
COPY init-extensions.sql /docker-entrypoint-initdb.d/
```

```sql
-- db/init-extensions.sql
CREATE EXTENSION IF NOT EXISTS pg_jsonschema;
```

### Fast-Reloading Development Environment

**Critical for LLM Productivity**: This Docker-based setup provides instant code reloading across all components, eliminating manual restarts and enabling rapid iteration.

#### Complete Development Stack with Hot Reloading
```yaml
# docker-compose.yml - Optimized for fast development workflow
# Run: docker-compose up --build (first time) or docker-compose up (daily)

version: '3.8'

services:
  # PostgreSQL Database with Extensions and Data Persistence
  db:
    build:
      context: ./db
      dockerfile: Dockerfile
    volumes:
      # CRITICAL: Persists database data on host machine
      - ./postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_USER=kidney_genetics
      - POSTGRES_PASSWORD=dev_password
      - POSTGRES_DB=kidney_genetics_db
    ports:
      - "5432:5432"

  # Redis for Celery Message Broker and API Caching
  redis:
    image: redis:7-alpine
    volumes:
      - ./redis_data:/data
    ports:
      - "6379:6379"

  # Backend API with FastAPI Auto-Reload
  api:
    build:
      context: ./backend
      dockerfile: Dockerfile.dev
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      # CRITICAL: Mounts local code for instant reloading (1-2 second restart)
      - ./backend:/app
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://kidney_genetics:dev_password@db/kidney_genetics_db
      - REDIS_URL=redis://redis:6379
      - SECRET_KEY=dev_secret_key_change_in_production
    depends_on:
      - db
      - redis

  # Background Task Processor with Code Reloading
  celery_worker:
    build: ./backend
    command: celery -A app.celery_worker.celery worker --loglevel=info
    volumes:
      # CRITICAL: Workers also get instant code updates
      - ./backend:/app
    environment:
      - DATABASE_URL=postgresql://kidney_genetics:dev_password@db/kidney_genetics_db
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - redis

  # Frontend with Vite Hot Module Replacement (HMR)
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev
    command: npm run dev -- --host 0.0.0.0
    volumes:
      # CRITICAL: Mounts local code for instant HMR (<50ms updates)
      - ./frontend:/app
      # Prevents local node_modules from overwriting container's
      - /app/node_modules
    ports:
      # Vite dev server with HMR
      - "5173:5173"
    environment:
      - VITE_API_BASE_URL=http://localhost:8000

  # Celery Task Monitoring Dashboard
  flower:
    build: ./backend
    command: celery -A app.celery_worker.celery flower --port=5555
    depends_on: [redis]
    ports:
      - "5555:5555"
    environment:
      - REDIS_URL=redis://redis:6379

  # Database Management Interface
  adminer:
    image: adminer
    ports:
      - "8080:8080"
```

#### Development Dockerfile Configurations

**Backend Dockerfile (backend/Dockerfile.dev)**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install development dependencies
RUN pip install --no-cache-dir uvicorn[standard] watchfiles

# Copy application code (will be overridden by volume mount)
COPY . .

# Expose port
EXPOSE 8000

# Default command (overridden in docker-compose.yml)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

**Frontend Dockerfile (frontend/Dockerfile.dev)**
```dockerfile
FROM node:18-alpine

WORKDIR /app

# Copy package files first for better Docker layer caching
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code (will be overridden by volume mount)
COPY . .

# Expose Vite dev server port
EXPOSE 5173

# Default command (overridden in docker-compose.yml)
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
```

#### The Development Workflow Experience

**First-Time Setup (One Command)**
```bash
# Clone and start everything
git clone <repo-url> kidney-genetics-db
cd kidney-genetics-db
docker-compose up --build
```

**Daily Development Workflow**
```bash
# Start all services in background
docker-compose up -d

# Access points:
# - Frontend: http://localhost:5173 (Vue.js app with HMR)
# - API: http://localhost:8000 (FastAPI with auto-docs at /docs)
# - Database Admin: http://localhost:8080 (Adminer)
# - Task Monitor: http://localhost:5555 (Flower dashboard)

# Work in your local editor:
# 1. Edit backend/api/endpoints/genes.py → API reloads in 1-2 seconds
# 2. Edit frontend/src/components/GeneTable.vue → Page updates in <50ms
# 3. Database changes persist automatically in ./postgres_data/

# Stop when done
docker-compose down
```

**Key Development Benefits:**
- **Instant Backend Updates**: FastAPI with `--reload` detects Python file changes and restarts the server in 1-2 seconds
- **Instant Frontend Updates**: Vite HMR updates Vue components in <50ms without page refresh, preserving application state
- **Persistent Database**: All database changes saved to `./postgres_data/` survive container restarts
- **Isolated Environment**: Each developer gets identical setup regardless of local machine configuration
- **No Manual Restarts**: Volume mounts ensure all code changes are instantly reflected in running containers
- **Full Stack Testing**: All components (frontend, API, database, background tasks) run together locally

**Critical Volume Mounts for Hot Reloading:**
```yaml
# Backend: Local changes instantly available in container
- ./backend:/app

# Frontend: Local changes trigger HMR 
- ./frontend:/app
- /app/node_modules  # Preserves container's node_modules

# Database: Persistent data storage
- ./postgres_data:/var/lib/postgresql/data
```

This setup eliminates the traditional "edit → build → restart → test" cycle, enabling continuous development flow where changes are visible almost immediately.

#### Query-Optimized Tables (Latest Version)
```sql
-- Expression data for fast querying
CREATE TABLE expression_latest (
    gene_id INTEGER REFERENCES genes(id),
    tissue VARCHAR(100),
    tpm FLOAT,
    expression_score FLOAT,
    PRIMARY KEY (gene_id, tissue)
);

-- Protein interactions
CREATE TABLE interactions_latest (
    gene1_id INTEGER REFERENCES genes(id),
    gene2_id INTEGER REFERENCES genes(id),
    interaction_score FLOAT,
    evidence_types TEXT[],
    PRIMARY KEY (gene1_id, gene2_id)
);

-- Clinical phenotypes
CREATE TABLE phenotypes_latest (
    gene_id INTEGER REFERENCES genes(id),
    phenotype_source VARCHAR(50),
    phenotype_id VARCHAR(100),
    phenotype_name TEXT,
    evidence_level VARCHAR(20),
    PRIMARY KEY (gene_id, phenotype_source, phenotype_id)
);

-- Clinical evidence
CREATE TABLE clinical_evidence_latest (
    gene_id INTEGER REFERENCES genes(id),
    evidence_source VARCHAR(50),
    evidence_level VARCHAR(20),
    disease_name TEXT,
    inheritance_pattern VARCHAR(50),
    confidence_score FLOAT
);
```

### Backend API Architecture

#### FastAPI Application Structure
```
backend/
├── main.py                 # FastAPI app initialization
├── api/
│   ├── endpoints/
│   │   ├── genes.py        # Gene CRUD operations
│   │   ├── pipeline.py     # Pipeline management
│   │   └── users.py        # User management
│   └── dependencies.py     # Auth and DB dependencies
├── database/
│   ├── models.py          # SQLAlchemy models
│   ├── connection.py      # Database connection
│   └── migrations/        # Alembic migrations
├── schemas.py             # Pydantic schemas
├── core/
│   ├── config.py          # Pydantic-based settings management
│   └── security.py        # JWT and password hashing
└── services/
    ├── gene_service.py    # Business logic
    └── pipeline_service.py # Pipeline orchestration
```

#### Modern Environment Configuration
```python
# backend/core/config.py - Type-safe environment variable loading
from pydantic_settings import BaseSettings
from pydantic import Field, validator
from typing import Optional
import secrets

class Settings(BaseSettings):
    """Application settings with type validation and environment variable loading."""
    
    # Database
    database_url: str = Field(..., env="DATABASE_URL")
    
    # Redis
    redis_url: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    
    # JWT Security - CRITICAL: Must be long, random string in production
    secret_key: str = Field(default_factory=lambda: secrets.token_urlsafe(32), env="SECRET_KEY")
    algorithm: str = Field(default="HS256", env="ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    
    # External API Keys
    ncbi_api_key: Optional[str] = Field(default=None, env="NCBI_API_KEY")
    omim_api_key: Optional[str] = Field(default=None, env="OMIM_API_KEY")
    cosmic_username: Optional[str] = Field(default=None, env="COSMIC_USERNAME")
    cosmic_password: Optional[str] = Field(default=None, env="COSMIC_PASSWORD")
    
    # Application
    environment: str = Field(default="development", env="ENVIRONMENT")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    @validator("secret_key")
    def validate_secret_key(cls, v):
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        return v
    
    @validator("database_url")
    def validate_database_url(cls, v):
        if not v.startswith(("postgresql://", "postgresql+asyncpg://")):
            raise ValueError("DATABASE_URL must be a valid PostgreSQL URL")
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Global settings instance
settings = Settings()
```

#### Database Connection with Settings
```python
# backend/database/connection.py - Modern database configuration
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from ..core.config import settings

# Use settings for database URL with connection optimization
engine = create_engine(
    settings.database_url,
    echo=settings.environment == "development",  # SQL logging in dev only
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=300,    # Recycle connections every 5 minutes
    pool_size=10,        # Connection pool size
    max_overflow=20      # Max overflow connections
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """Database dependency for FastAPI routes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

#### Authentication & Authorization System
```python
# Enhanced User model with role-based access control
class User(Base):
    id: int
    email: str
    hashed_password: str
    is_active: bool = True
    is_verified: bool = False
    role: str = "viewer"  # viewer, curator, admin
    created_at: datetime
    updated_at: datetime

# Role-based permissions
class UserRole(str, Enum):
    VIEWER = "viewer"       # Read-only access to genes and data
    CURATOR = "curator"     # Can review/annotate data, access admin views
    ADMIN = "admin"         # Can trigger pipelines, manage users

# FastAPI dependency for role checking
async def require_role(required_role: UserRole):
    def role_checker(current_user: User = Depends(get_current_user)):
        role_hierarchy = {"admin": 3, "curator": 2, "viewer": 1}
        if role_hierarchy.get(current_user.role, 0) < role_hierarchy.get(required_role.value, 999):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user
    return role_checker

# Usage in endpoints
@router.post("/pipeline/trigger")
async def trigger_pipeline(
    user: User = Depends(require_role(UserRole.ADMIN))
):
    # Only admins can trigger pipelines
    pass
```

#### Critical Alembic Migration Workflow
```bash
# FIRST ACTION after defining SQLAlchemy models:

# 1. Initialize Alembic (one time only)
alembic init alembic

# 2. Configure alembic.ini and env.py with database URL from settings
# Edit alembic/env.py to import settings:
from backend.core.config import settings
config.set_main_option("sqlalchemy.url", settings.database_url)

# 3. Create initial migration (captures current model state)
alembic revision --autogenerate -m "Initial migration"

# 4. Apply migration to database  
alembic upgrade head

# 5. EVERY SUBSEQUENT MODEL CHANGE requires a new migration:
# - Edit models.py
# - Run: alembic revision --autogenerate -m "Add new field to gene table"
# - Run: alembic upgrade head
# - Commit migration file to version control

# NON-NEGOTIABLE RULES:
# - Never create tables manually
# - Every model change needs a migration file
# - Migration files must be committed to git
# - Test migrations on development database first
```

#### FastAPI-Users Security Best Practices
```python
# backend/core/security.py - Production-grade security implementation
from fastapi_users import FastAPIUsers
from fastapi_users.authentication import JWTAuthentication
from fastapi_users.db import SQLAlchemyUserDatabase
from passlib.context import CryptContext
from .config import settings

# Password hashing with bcrypt (production standard - slow and secure)
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12  # Sufficient rounds for security vs performance
)

# JWT Authentication with secure settings
jwt_authentication = JWTAuthentication(
    secret=settings.secret_key,  # Must be 32+ chars, randomly generated
    lifetime_seconds=settings.access_token_expire_minutes * 60,
    tokenUrl="auth/jwt/login",
)

# CRITICAL SECURITY REQUIREMENTS:
# - SECRET_KEY must be 32+ characters (enforced by validator)
# - Use bcrypt for password hashing (slow by design)
# - JWT tokens have reasonable expiration (30 minutes default)
# - Never log or expose SECRET_KEY in application code
# - In production: inject SECRET_KEY via Docker Secrets/Vault
```

#### Core API Endpoints
```python
# Gene browsing and search
GET /api/v1/genes/                    # Paginated gene list with filters
GET /api/v1/genes/{hgnc_id}          # Single gene detail
GET /api/v1/genes/{hgnc_id}/history  # Version history
GET /api/v1/genes/search             # Advanced search

# Pipeline management (authenticated)
POST /api/v1/pipeline/trigger        # Start new curation run
GET /api/v1/pipeline/status/{task_id} # Task status
GET /api/v1/pipeline/versions        # Available versions

# Data export
GET /api/v1/export/csv               # CSV export (backwards compatibility)
GET /api/v1/export/json              # JSON export
```

### Data Processing Pipeline Architecture

#### Python Module Structure
```
pipeline/
├── __init__.py
├── core/
│   ├── base_source.py     # Abstract base class for data sources
│   ├── merger.py          # Data merging logic
│   └── annotator.py       # Annotation enrichment
├── sources/
│   ├── panelapp.py        # PanelApp integration
│   ├── literature.py      # Literature curation
│   ├── diagnostic_panels.py # Commercial panel scraping
│   ├── hpo.py            # HPO phenotype data
│   └── pubtator.py       # Literature mining
├── tasks.py              # Celery task definitions
└── scheduler.py          # Automated scheduling
```

#### Transactional Pipeline Implementation
```python
# pipeline/tasks.py - Robust, transactional pipeline execution
from sqlalchemy.orm import Session
from app.database.connection import get_db

@celery.task(bind=True)
def run_update_pipeline(self, notes: str, user_id: int):
    """
    Main pipeline task with full transactional integrity.
    If any step fails, entire update is rolled back.
    """
    task_id = self.request.id
    db: Session = next(get_db())
    
    try:
        # Begin transaction for entire pipeline update
        with db.begin():
            # 1. Create new CurationVersion (committed only if all steps succeed)
            version = CurationVersion(
                notes=notes,
                user_id=user_id,
                pipeline_status="running"
            )
            db.add(version)
            db.flush()  # Get version ID without committing
            
            # 2. Process all sources with validation
            all_gene_data = []
            for source_module in ENABLED_SOURCES:
                try:
                    # Fetch and transform data
                    raw_data = source_module.fetch()
                    transformed_data = source_module.transform(raw_data)
                    
                    # Validate against Pydantic schema
                    validated_data = [GeneCurationSchema(**gene) for gene in transformed_data]
                    all_gene_data.extend(validated_data)
                    
                except Exception as e:
                    logger.error(f"Source {source_module.__name__} failed: {e}")
                    raise  # Abort entire transaction
            
            # 3. Merge and deduplicate data
            merged_data = merge_gene_data(all_gene_data)
            
            # 4. Insert versioned data
            for gene_data in merged_data:
                gene_curation = GeneCuration(
                    gene_id=gene_data.gene_id,
                    version_id=version.id,
                    curation_data=gene_data.dict()
                )
                db.add(gene_curation)
            
            # 5. Refresh all _latest tables atomically
            refresh_latest_tables(db, version.id)
            
            # 6. Mark version as completed
            version.pipeline_status = "completed"
            
            # Commit entire transaction
            logger.info(f"Pipeline update {version.id} completed successfully")
            
    except Exception as e:
        # Rollback occurs automatically
        logger.error(f"Pipeline failed, rolling back: {e}")
        raise  # Re-raise for Celery error handling

def refresh_latest_tables(db: Session, version_id: int):
    """Atomically refresh all _latest tables with new version data"""
    # TRUNCATE and repopulate all _latest tables
    db.execute("TRUNCATE expression_latest, interactions_latest, phenotypes_latest CASCADE")
    
    # Repopulate from new version data
    db.execute("""
        INSERT INTO expression_latest (gene_id, tissue, tpm, expression_score)
        SELECT gc.gene_id, 
               (gc.curation_data->>'expression_data')::jsonb->>tissue,
               ...
        FROM gene_curations gc 
        WHERE gc.version_id = :version_id
    """, {"version_id": version_id})
    
    # Similar for other _latest tables...
```

#### Data Source Mapping (Enhanced with laborberlin/custom-panel Patterns)
| Current R Script | New Python Module | Primary Function | laborberlin Equivalent |
|-----------------|-------------------|------------------|----------------------|
| `01_PanelApp.R` | `sources/g01_panelapp.py` | PanelApp API integration | `g01_panelapp.py` (direct port) |
| `02_Literature.R` | `sources/g02_literature.py` | Manual curation workflow | `b_manual_curation.py` (pattern) |
| `03_DiagnosticPanels.R` | `sources/g03_diagnostic_panels.py` | Web scraping automation | `g03_commercial_panels.py` + `scrapers/` |
| `04_HPO-detection.R` | `sources/g04_hpo.py` | HPO API integration | `g02_hpo.py` (direct adaptation) |
| `05_PubTator.R` | `sources/g05_pubtator.py` | Literature mining API | New implementation |
| `A_MergeAnalysesSources.R` | `engine/merger.py` | Multi-source data merging | `engine/merger.py` (direct port) |
| `B_AnnotationHGNC.R` | `engine/annotator.py` | HGNC standardization | `core/hgnc_client.py` (pattern) |
| `C_AnnotateMergedTable.R` | `engine/annotator.py` | Complex annotation enrichment | `engine/annotator.py` (pattern) |

### Frontend Application Architecture

#### Vue.js Application Structure
```
frontend/
├── src/
│   ├── components/
│   │   ├── GeneTable.vue      # Searchable gene browser
│   │   ├── GeneDetail.vue     # Gene detail view
│   │   ├── NetworkViewer.vue  # Protein interaction networks
│   │   └── ExpressionHeatmap.vue # Expression visualization
│   ├── views/
│   │   ├── GeneListView.vue   # Main gene browser page
│   │   ├── GeneDetailView.vue # Gene detail page
│   │   └── PipelineView.vue   # Admin pipeline management
│   ├── stores/
│   │   ├── geneStore.js       # Gene data management
│   │   └── pipelineStore.js   # Pipeline status management
│   ├── services/
│   │   └── api.js             # API communication
│   └── router/
│       └── index.js           # Vue Router configuration
├── package.json
└── vite.config.js
```

#### Key Frontend Features
- **Interactive Gene Browser**: Vuetify data table with server-side pagination, sorting, and filtering
- **Advanced Search**: Multi-field search with boolean operators
- **Gene Detail Views**: Expandable JSON data with structured visualization
- **Network Visualization**: Interactive protein interaction networks
- **Expression Heatmaps**: Tissue-specific expression data visualization
- **Pipeline Dashboard**: Real-time pipeline status and version management

---

## Phase-by-Phase Implementation Plan

### Phase 1: Foundation & Database Schema

#### Part 1: Project Setup
**Deliverables:**
- [ ] Initialize `/kidney-genetics-db/` repository structure
- [ ] Docker development environment configuration
- [ ] PostgreSQL database setup with initial schema
- [ ] Basic FastAPI application skeleton

**Tasks:**
1. **Repository Structure & Security Setup**
   ```bash
   mkdir -p kidney-genetics-db/{backend,pipeline,frontend,schema,scripts}
   cd kidney-genetics-db
   
   # Create .gitignore from day one
   cat > .gitignore << 'EOF'
   # Environment files - NEVER commit secrets
   .env
   .env.local
   config.local.yml
   
   # Dependencies
   node_modules/
   __pycache__/
   .pytest_cache/
   .mypy_cache/
   .ruff_cache/
   
   # IDE
   .vscode/
   .idea/
   *.swp
   *.swo
   
   # OS
   .DS_Store
   Thumbs.db
   
   # Data
   postgres_data/
   redis_data/
   *.csv
   *.xlsx
   *.json.gz
   
   # Logs
   *.log
   logs/
   
   # Build artifacts
   dist/
   build/
   *.egg-info/
   EOF
   ```

2. **Docker Configuration with Fast Reloading**
   - Complete `docker-compose.yml` with hot reloading enabled for all services
   - Volume mounts for instant code updates (backend: 1-2s, frontend: <50ms)
   - Development Dockerfiles optimized for rapid iteration
   - Environment variable management (`.env.example`)

3. **Database Schema**
   - Implement core tables (`genes`, `curation_versions`, `gene_curations`)
   - Create query-optimized tables for latest data
   - Set up Alembic for schema migrations

4. **Basic FastAPI Setup**
   - FastAPI application initialization
   - Database connection configuration
   - Basic health check endpoints

5. **Code Quality Infrastructure**
   - Set up pre-commit hooks with Ruff and MyPy
   - Configure automated code quality enforcement
   - Establish testing framework foundations

#### Part 2: Data Model Implementation
**Deliverables:**
- [ ] Complete SQLAlchemy models
- [ ] Pydantic schemas for data validation
- [ ] Database migration system
- [ ] Basic CRUD operations

**Tasks:**
1. **SQLAlchemy Models**
   - Implement all database models with relationships
   - Add indexes for performance optimization
   - Configure connection pooling

2. **Pydantic Schemas**
   - Create comprehensive data validation schemas
   - Map existing CSV schema to Pydantic models
   - Handle nested JSON structures

3. **Data Migration Framework**
   - Design migration scripts for existing CSV data
   - Create data validation and integrity checks
   - Implement rollback procedures

### Phase 2: Backend API Development

#### Part 1: Core API Implementation (Enhanced with laborberlin Patterns)
**Deliverables:**
- [ ] Gene browsing and search endpoints with rich console output
- [ ] Typer-based CLI integration alongside web API
- [ ] Configuration management system with YAML overrides

**Tasks:**
1. **Gene API Endpoints** (Following laborberlin patterns)
   ```python
   # Implement core endpoints with caching
   GET /api/v1/genes/                    # List with pagination/filtering
   GET /api/v1/genes/{hgnc_id}          # Single gene detail  
   GET /api/v1/genes/{hgnc_id}/history  # Version history
   POST /api/v1/genes/search            # Advanced search
   ```

2. **CLI Integration** (Direct adaptation from laborberlin)
   - Typer-based command interface
   - Rich console output with progress bars
   - Configuration validation commands
   - Development-friendly debugging options

3. **Configuration Management** (Port from laborberlin)
   - YAML-based configuration with nested access
   - Environment-specific overrides (config.local.yml)
   - Source enable/disable toggles
   - API caching configuration

#### Part 2: Data Processing Pipeline (Leveraging laborberlin Architecture)
**Deliverables:**
- [ ] Plugin-based source system following laborberlin pattern
- [ ] Enhanced CLI pipeline runner with rich output
- [ ] Direct ports of applicable laborberlin components

**Tasks:**
1. **Data Source Migration** (Using laborberlin as template)
   ```python
   # Direct ports from laborberlin
   pipeline/sources/g01_panelapp.py     # Port laborberlin's PanelApp client
   pipeline/sources/g04_hpo.py          # Adapt laborberlin's HPO integration
   
   # New implementations following laborberlin patterns  
   pipeline/sources/g05_pubtator.py     # Literature mining
   pipeline/sources/g02_literature.py   # Manual curation (adapt b_manual_curation.py)
   
   # Enhanced web scraping using laborberlin's scraper framework
   pipeline/sources/g03_diagnostic_panels.py  # Use laborberlin's scrapers/parsers/
   ```

2. **Pipeline Orchestration** (Direct adaptation from laborberlin)
   - `Pipeline` class as central orchestrator
   - Rich progress reporting and logging
   - Intermediate file preservation for debugging
   - Configurable source weights and scoring

3. **Enhanced Development Experience**
   - Rich CLI with colored output and progress bars
   - Comprehensive logging with structured output
   - Debug mode with intermediate file preservation
   - Configuration validation and testing commands

### Phase 3: Frontend Application

#### Part 1: Vue.js Application Setup
**Deliverables:**
- [ ] Vue.js application with Vuetify integration
- [ ] Basic gene browsing interface
- [ ] API integration layer

**Tasks:**
1. **Frontend Initialization**
   ```bash
   npm create vite@latest frontend -- --template vue
   npm install vuetify @pinia/vue3 vue-router axios
   ```

2. **Core Components**
   - `GeneTable.vue`: Server-side paginated data table
   - `GeneSearch.vue`: Advanced search interface
   - `NavigationDrawer.vue`: Main navigation

3. **State Management**
   - Pinia stores for gene data and search state
   - API service layer with error handling
   - Loading and error state management

#### Part 2: Advanced Features
**Deliverables:**
- [ ] Gene detail views with JSON visualization
- [ ] Interactive data visualizations
- [ ] Pipeline management interface

**Tasks:**
1. **Gene Detail Interface**
   - Expandable JSON data display
   - Evidence scoring visualization
   - Clinical annotation sections

2. **Data Visualizations**
   - Protein interaction network graphs (D3.js/vis.js)
   - Expression heatmaps
   - Evidence score charts

3. **Admin Interface**
   - Pipeline trigger and monitoring
   - Version management
   - System status dashboard

### Phase 4: Data Migration & Testing

#### Part 1: Data Migration
**Deliverables:**
- [ ] Complete migration of existing CSV data
- [ ] Data validation and integrity checks
- [ ] Performance optimization

**Tasks:**
1. **Historical Data Migration**
   - Import all timestamped CSV files (2023-05-18 through 2024-05-14)
   - Preserve data versioning and traceability
   - Validate data integrity against source CSVs

2. **Migration Scripts**
   ```python
   # Migration utilities
   scripts/migrate_csv_to_postgres.py
   scripts/validate_data_integrity.py
   scripts/performance_benchmarks.py
   ```

3. **Query Optimization**
   - Database indexing strategy
   - Query performance tuning
   - Caching layer implementation

#### Part 2: Testing & Validation
**Deliverables:**
- [ ] Comprehensive test suite
- [ ] API endpoint validation
- [ ] Performance benchmarking

**Tasks:**
1. **Backend Testing**
   - Unit tests for all API endpoints
   - Integration tests for pipeline processing
   - Database transaction testing

2. **Frontend Testing**
   - Component unit tests (Jest/Vitest)
   - End-to-end testing (Playwright/Cypress)
   - User interface testing

3. **Data Validation**
   - Deep comparison script for R vs Python output validation
   - Field-by-field gene data comparison with discrepancy reporting
   - Validate gene counts, evidence scores, and clinical annotations
   - Performance testing with full dataset

**Validation Script Implementation:**
```python
# scripts/validate_r_vs_python.py - Deep data validation
def compare_gene_outputs(r_csv_path: Path, python_json_path: Path):
    """Field-by-field comparison of R CSV vs Python JSON output"""
    r_data = pd.read_csv(r_csv_path)
    with open(python_json_path) as f:
        python_data = json.load(f)
    
    discrepancies = []
    for gene_symbol in r_data['approved_symbol']:
        r_gene = r_data[r_data['approved_symbol'] == gene_symbol].iloc[0]
        python_gene = next((g for g in python_data if g['approved_symbol'] == gene_symbol), None)
        
        if not python_gene:
            discrepancies.append(f"Gene {gene_symbol} missing in Python output")
            continue
            
        # Compare critical fields
        for field in ['evidence_count', 'hgnc_id', 'pLI', 'clinical_groups_p']:
            if field in r_gene and field in python_gene:
                if not values_match(r_gene[field], python_gene[field]):
                    discrepancies.append(f"{gene_symbol}.{field}: R={r_gene[field]} vs Python={python_gene[field]}")
    
    return discrepancies
```

### Phase 5: Integration & Documentation

#### Part 1: System Integration
**Deliverables:**
- [ ] Production Docker configuration
- [ ] CI/CD pipeline setup
- [ ] Monitoring and logging

**Tasks:**
1. **Production Setup**
   - Multi-stage Docker builds
   - Environment-specific configurations
   - Database backup and restore procedures

2. **DevOps Integration**
   - GitHub Actions CI/CD pipeline
   - Automated testing and deployment
   - Environment promotion workflow

3. **Monitoring**
   - Application logging (structured logging)
   - Performance monitoring
   - Error tracking and alerting

#### Part 2: Documentation & Deployment
**Deliverables:**
- [ ] Updated documentation website
- [ ] API documentation
- [ ] Deployment guides

**Tasks:**
1. **Documentation Migration**
   - Convert Bookdown documentation to modern format
   - Integrate FastAPI auto-generated API docs
   - User guides and tutorials

2. **Final Testing**
   - User acceptance testing
   - Load testing with production data
   - Security testing and review

3. **Go-Live Preparation**
   - Production deployment checklist
   - Rollback procedures
   - User training materials

---

## Technical Implementation Details

### Database Migration Strategy

#### CSV to PostgreSQL Mapping
```python
# Example migration mapping
CSV_FIELD_MAPPING = {
    'approved_symbol': 'genes.approved_symbol',
    'hgnc_id': 'genes.hgnc_id',
    'evidence_count': 'gene_curations.curation_data->evidence->count',
    'omim_summary': 'gene_curations.curation_data->clinical->omim',
    'stringdb_interaction_string': 'gene_curations.curation_data->interactions->stringdb',
    # ... complete mapping for all 25+ fields
}
```

#### Refined GenCC-Compatible Schema (Source of Truth)

**Architectural Breakthrough**: This refined schema addresses critical feedback to create a scientifically rigorous, flexible, and internationally compatible data model.

**Key Refinements Based on Expert Analysis**:

1. **Generic Evidence Structure**: Replaces rigid PanelApp-specific structure with flexible evidence objects that accommodate any source type
2. **Complete Provenance Tracking**: Every data point (pLI scores, expression values, etc.) includes source, version, and date accessed
3. **Professional Curation Workflow**: Multi-stage review process with complete audit trail (Automated → Primary Review → Secondary Review → Approved)

**GenCC Compatibility Benefits**:
- **Direct International Submission**: Curations can be submitted to GenCC database for global impact
- **Standardized Clinical Validity**: Uses GenCC evidence-based terminology (Definitive, Strong, Moderate, Limited, etc.)
- **Interoperability**: Compatible with ClinGen, OMIM, Orphanet workflows

```json
# plan/schema/gene_curation.json - Refined scientifically rigorous schema
{
  "$schema": "http://json-schema.org/draft-07/schema#", 
  "title": "Kidney Gene Curation Record",
  "description": "Comprehensive record aggregating multiple gene-disease assertions with full provenance",
  "required": ["hgnc_id", "approved_symbol", "assertions", "version_details"],
  
  "properties": {
    "hgnc_id": {"type": "string", "pattern": "^HGNC:[0-9]+$"},
    "approved_symbol": {"type": "string"},
    
    "assertions": {
      "type": "array",
      "description": "Gene-disease-inheritance assertions (core scientific content)",
      "items": {
        "type": "object",
        "properties": {
          "disease": {
            "mondo_id": "MONDO:0009180",
            "mondo_label": "Polycystic kidney disease 1", 
            "submitted_disease_ids": ["OMIM:173900", "HP:0000003"]
          },
          "classification": {
            "type": "string",
            "enum": ["Definitive", "Strong", "Moderate", "Limited", "Disputed", "Refuted", "No Known Disease Relationship"]
          },
          "evidence": {
            "type": "array",
            "description": "Generic evidence structure accommodates any source",
            "items": {
              "source_name": "PanelApp UK | PMID | ClinGen | Blueprint Genetics",
              "source_id": "Panel ID | PMID number | Assertion ID",
              "source_version": "v1.3 | 2024-07-31", 
              "classification": "Green | Pathogenic | Definitive | Included",
              "submitted_disease": "Original disease term from source",
              "additional_metadata": "Source-specific data (flexible)"
            }
          }
        }
      }
    },
    
    "ancillary_data": {
      "description": "COMPLETE provenance tracking - every value traceable to source",
      "constraint_metrics": [
        {
          "source": "gnomAD", "version": "v2.1.1", "date_accessed": "2024-07-31", 
          "pli": 0.999, "oe_lof": 0.04
        },
        {
          "source": "gnomAD", "version": "v4.0", "date_accessed": "2024-07-31",
          "pli": 0.998, "oe_lof": 0.05
        }
      ],
      "expression_data": [
        {
          "source": "GTEx", "version": "v8", "date_accessed": "2024-07-31",
          "measurements": [
            {"tissue": "Kidney - Cortex", "value": 45.2, "unit": "TPM", "sample_size": 73}
          ]
        }
      ]
    },
    
    "curation_workflow": {
      "description": "Professional review process with complete audit trail",
      "status": "Automated | In Primary Review | In Secondary Review | Approved",
      "primary_curator": "curator1@institution.edu",
      "secondary_curator": "senior_curator@institution.edu", 
      "review_log": [
        {
          "timestamp": "2024-07-31T14:30:00Z",
          "user_email": "curator1@institution.edu",
          "action": "status_change",
          "previous_status": "Automated",
          "new_status": "In Primary Review",
          "comment": "Assigned for review. Evidence comprehensive.",
          "changes_made": {"evidence_summary": "Updated", "pmids": "Added PMID:23456789"}
        }
      ],
      "flags": {
        "conflicting_evidence": false,
        "insufficient_evidence": false,
        "outdated_sources": false
      }
    }
  }
}
```

**Scientific Impact of Refined Schema**:

1. **From Data Reporting to Data Integration**:
   - **Before**: `"source": "PMID_35325889 | PMID_34264297"` (unparseable concatenated strings)
   - **After**: Structured evidence array with full metadata, enabling complex queries like "Find all genes with 'Green' evidence from any PanelApp panel"

2. **Reproducible Science Through Provenance**:
   - **Before**: `"pLI": 0.999` (source unknown, version unknown, date unknown)  
   - **After**: `{"source": "gnomAD", "version": "v2.1.1", "date_accessed": "2024-07-31", "pli": 0.999}` (fully traceable)

3. **Professional Curation Workflow**:
   - **Before**: Simple status field, no accountability
   - **After**: Complete audit trail with curator assignments, review stages, and change tracking

4. **Plugin Architecture Ready**:
   - Generic evidence structure means new data sources require NO schema changes
   - Each source module (`panelapp.py`, `literature.py`) simply produces evidence objects
   - Fully extensible and maintainable

**Database Queries Enabled by Refined Schema**:
```sql
-- Find genes with conflicting evidence between sources
SELECT hgnc_id, approved_symbol 
FROM gene_curations 
WHERE curation_data->'curation_workflow'->'flags'->>'conflicting_evidence' = 'true';

-- Find all "Definitive" classifications supported by ClinGen
SELECT * FROM gene_curations 
WHERE curation_data->'assertions' @> '[{"classification": "Definitive"}]'::jsonb
  AND curation_data->'assertions' @> '[{"evidence": [{"source_name": "ClinGen"}]}]'::jsonb;

-- Track curation workflow progress
SELECT 
  approved_symbol,
  curation_data->'curation_workflow'->>'status' as status,
  jsonb_array_length(curation_data->'curation_workflow'->'review_log') as review_actions
FROM gene_curations;
```
          "disease_id": {"type": "string"},
          "clinical_validity": {
            "type": "string",
            "enum": ["Definitive", "Strong", "Moderate", "Limited", "Disputed Evidence", "Refuted Evidence", "No Known Disease Relationship", "Animal Model Only"],
            "description": "GenCC standardized clinical validity term"
          },
          "mode_of_inheritance": {"type": "string"},
          "assertion_date": {"type": "string", "format": "date"},
          "assertion_criteria": {"type": "string", "format": "uri"},
          "supporting_evidence_ids": {
            "type": "array", 
            "items": {"type": "string"}
          }
        }
      }
    },
    "curation_metadata": {
      "type": "object",
      "required": ["curation_status", "curation_version", "last_updated"],
      "properties": {
        "external_submissions": {
          "type": "object",
          "properties": {
            "gencc_submitted": {"type": "boolean"},
            "gencc_submission_date": {"type": "string", "format": "date"}
          }
        }
      }
    }
  },
  "additionalProperties": true
      "properties": {
        "pLI": {"type": ["number", "null"]},
        "oe_lof": {"type": ["number", "null"]},
        "lof_z": {"type": ["number", "null"]},
        "mis_z": {"type": ["number", "null"]}
      }
    },
    "clinical_annotations": {
      "type": "object",
      "properties": {
        "omim_summary": {"type": ["string", "null"]},
        "gencc_summary": {"type": ["string", "null"]},
        "clingen_summary": {"type": ["string", "null"]},
        "clinvar": {"type": ["string", "null"]}
      }
    },
    "expression_data": {
      "type": "object",
      "properties": {
        "gtex_kidney_medulla": {"type": ["number", "null"]},
        "gtex_kidney_cortex": {"type": ["number", "null"]},
        "descartes_kidney_tpm": {"type": ["number", "null"]},
        "expression_score": {"type": ["number", "null"]}
      }
    },
    "interaction_data": {
      "type": "object",
      "properties": {
        "stringdb_interaction_sum_score": {"type": ["number", "null"]},
        "stringdb_interaction_normalized_score": {"type": ["number", "null"]},
        "stringdb_interaction_string": {"type": ["string", "null"]},
        "interaction_score": {"type": ["number", "null"]}
      }
    }
  },
  "additionalProperties": true
}
```

#### Auto-Generated Pydantic Models
```python
# backend/schemas.py - Generated from JSON Schema
# DO NOT EDIT MANUALLY - Generated by scripts/generate_schemas.py

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import json
from pathlib import Path

# Load schema and generate models
SCHEMA_PATH = Path(__file__).parent.parent / "schema" / "gene_curation.json"

class ConstraintMetrics(BaseModel):
    pLI: Optional[float] = None
    oe_lof: Optional[float] = None
    lof_z: Optional[float] = None
    mis_z: Optional[float] = None

class ClinicalAnnotations(BaseModel):
    omim_summary: Optional[str] = None
    gencc_summary: Optional[str] = None
    clingen_summary: Optional[str] = None
    clinvar: Optional[str] = None

class ExpressionData(BaseModel):
    gtex_kidney_medulla: Optional[float] = None
    gtex_kidney_cortex: Optional[float] = None
    descartes_kidney_tpm: Optional[float] = None
    expression_score: Optional[float] = None

class InteractionData(BaseModel):
    stringdb_interaction_sum_score: Optional[float] = None
    stringdb_interaction_normalized_score: Optional[float] = None
    stringdb_interaction_string: Optional[str] = None
    interaction_score: Optional[float] = None

class GeneCurationSchema(BaseModel):
    """Auto-generated from plan/schema/gene_curation.json"""
    approved_symbol: str = Field(..., description="HGNC approved gene symbol")
    hgnc_id: str = Field(..., pattern=r"^HGNC:[0-9]+$", description="HGNC identifier")
    evidence_count: int = Field(..., ge=0, description="Total evidence count")
    source_count_percentile: Optional[float] = Field(None, ge=0, le=100)
    
    constraint_metrics: Optional[ConstraintMetrics] = None
    clinical_annotations: Optional[ClinicalAnnotations] = None
    expression_data: Optional[ExpressionData] = None
    interaction_data: Optional[InteractionData] = None
    
    class Config:
        extra = "allow"  # Allow additional properties from JSON schema
        validate_assignment = True

# Schema validation for JSONB at database level
def get_jsonb_schema_constraint() -> str:
    """Generate PostgreSQL CHECK constraint for JSONB validation"""
    with open(SCHEMA_PATH) as f:
        schema = json.load(f)
    return f"jsonb_matches_schema('{json.dumps(schema)}', curation_data)"
```

#### Schema Generation Script
```python
# scripts/generate_schemas.py - Auto-generate Pydantic from JSON Schema
import json
from pathlib import Path
from datamodel_code_generator import InputFileType, generate

def generate_pydantic_models():
    """Generate Pydantic models from JSON Schema"""
    schema_path = Path("plan/schema/gene_curation.json")
    output_path = Path("backend/schemas_generated.py")
    
    generate(
        input_=schema_path,
        input_file_type=InputFileType.JsonSchema,
        output=output_path,
        target_python_version=PythonVersion.PY_310,
        use_schema_description=True,
        use_field_description=True,
    )
    
    print(f"Generated Pydantic models from {schema_path} to {output_path}")

if __name__ == "__main__":
    generate_pydantic_models()
```

### API Performance Considerations

#### Caching Strategy
- **Redis**: Cache frequently accessed gene data
- **Database**: Materialized views for complex aggregations
- **CDN**: Static assets and documentation

#### Pagination and Filtering
```python
# Efficient pagination for large datasets
@router.get("/genes/")
async def list_genes(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    evidence_min: Optional[int] = None,
    clinical_group: Optional[str] = None
):
    # Implement efficient filtering and pagination
    pass
```

### Frontend Performance

#### Virtual Scrolling
- Handle large gene datasets (3,000+ rows) efficiently
- Implement virtual scrolling for gene tables
- Progressive loading for gene detail views

#### State Management
```javascript
// Pinia store for gene data
export const useGeneStore = defineStore('genes', {
  state: () => ({
    genes: [],
    totalCount: 0,
    loading: false,
    filters: {},
    currentGene: null
  }),
  actions: {
    async fetchGenes(params) {
      // Implement efficient API calls with caching
    }
  }
})
```

---

## Risk Mitigation & Validation

### Data Integrity Risks

#### Risk: Data Loss During Migration
**Mitigation:**
- Complete backup of existing CSV files
- Parallel validation during migration
- Rollback procedures to restore from CSV
- Checksum validation for all migrated records

#### Risk: API Integration Failures
**Mitigation:**
- Implement robust retry logic with exponential backoff
- Fallback to cached data when APIs are unavailable
- Circuit breaker pattern for external service calls
- Comprehensive error logging and alerting

#### Risk: Performance Degradation
**Mitigation:**
- Load testing with production-scale data
- Database query optimization and indexing
- Caching layer implementation
- Horizontal scaling capability with Docker

### Validation Framework

#### Data Consistency Checks
```python
def validate_migration_integrity():
    """Comprehensive validation of migrated data"""
    # 1. Record count validation
    assert postgres_gene_count == csv_gene_count
    
    # 2. Evidence score validation
    validate_evidence_scores_match()
    
    # 3. Clinical annotation validation
    validate_clinical_data_completeness()
    
    # 4. Interaction network validation
    validate_stringdb_interactions()
```

#### API Output Validation
- Compare FastAPI JSON responses with R-generated CSV data
- Validate complex nested structures (clinical groups, interactions)
- Ensure backwards compatibility for existing data consumers

### Rollback Strategy

#### Phased Rollback Capability
1. **Database Rollback**: Restore from CSV files if database issues occur
2. **API Rollback**: Maintain existing R pipeline as fallback
3. **Frontend Rollback**: Serve static CSV downloads if web interface fails
4. **Pipeline Rollback**: Preserve existing R scripts for emergency use

---

## Success Metrics & Deliverables

### Quantitative Success Metrics

#### Data Completeness
- ✅ **100% Gene Migration**: All 3,000+ genes successfully migrated
- ✅ **Zero Data Loss**: All 25+ metadata fields preserved
- ✅ **Historical Preservation**: All timestamped versions maintained
- ✅ **API Parity**: FastAPI responses match CSV data structure

#### Performance Improvements
- ✅ **Query Speed**: <200ms response time for gene lookups
- ✅ **Pipeline Efficiency**: 50% reduction in total processing time
- ✅ **Scalability**: Support for 10,000+ genes without performance degradation
- ✅ **Availability**: 99.9% uptime for web application

#### User Experience Enhancements
- ✅ **Search Performance**: Real-time search with <100ms response
- ✅ **Data Exploration**: Interactive filtering and visualization
- ✅ **Export Capability**: CSV/JSON export maintaining backwards compatibility
- ✅ **Documentation**: Comprehensive API documentation and user guides

### Key Deliverables by Phase

#### Phase 1 Deliverables
- [ ] Docker development environment
- [ ] PostgreSQL database with complete schema
- [ ] Basic FastAPI application structure
- [ ] Data migration framework

#### Phase 2 Deliverables
- [ ] Complete REST API with all endpoints
- [ ] Python-based data processing pipeline
- [ ] Celery task queue for background processing
- [ ] Authentication and authorization system

#### Phase 3 Deliverables
- [ ] Vue.js frontend application
- [ ] Interactive gene browser and search
- [ ] Data visualization components
- [ ] Pipeline management interface

#### Phase 4 Deliverables
- [ ] Complete data migration from existing CSVs
- [ ] Comprehensive test suite (>90% coverage)
- [ ] Performance optimization and caching
- [ ] Data validation and integrity checks

#### Phase 5 Deliverables
- [ ] Production deployment configuration
- [ ] Updated documentation website
- [ ] CI/CD pipeline
- [ ] Monitoring and logging system

### Long-term Success Indicators

#### Community Impact
- **Research Utility**: Increased usage by kidney genetics researchers
- **Data Currency**: Automated updates ensure latest genetic findings
- **Collaboration**: API enables third-party integrations
- **Reproducibility**: Versioned data supports reproducible research

#### Technical Excellence
- **Maintainability**: Clear separation of concerns and modular architecture
- **Extensibility**: Easy addition of new data sources and analysis methods
- **Reliability**: Robust error handling and graceful degradation
- **Security**: Secure API design with proper authentication

---

## Observability & Monitoring Strategy

### Structured Logging Implementation
```python
# backend/core/logging.py - Centralized structured logging
import structlog
import logging.config

# Configure structured logging from day one
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": structlog.stdlib.ProcessorFormatter,
            "processor": structlog.dev.ConsoleRenderer(colors=False),
            "foreign_pre_chain": [
                structlog.contextvars.merge_contextvars,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.stdlib.add_log_level,
                structlog.stdlib.add_logger_name,
            ],
        },
    },
    "handlers": {
        "default": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
    },
    "loggers": {
        "": {
            "handlers": ["default"],
            "level": "INFO",
            "propagate": False,
        },
    }
}

# Usage in pipeline tasks
logger = structlog.get_logger("pipeline")
logger.info("Pipeline started", version_id=version.id, user_id=user_id, source_count=len(sources))
```

### Health Check & Monitoring Endpoints
```python
# backend/api/endpoints/health.py - Standard health monitoring
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

router = APIRouter()

@router.get("/health")
async def health_check():
    """Basic health check for load balancers/orchestrators"""
    return {"status": "healthy", "timestamp": datetime.utcnow()}

@router.get("/health/detailed")
async def detailed_health_check(db: Session = Depends(get_db)):
    """Detailed health check including database connectivity"""
    try:
        # Test database connection
        db.execute("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    try:
        # Test Redis connection
        redis_client.ping()
        cache_status = "healthy"
    except Exception as e:
        cache_status = f"unhealthy: {str(e)}"
    
    return {
        "status": "healthy" if db_status == "healthy" and cache_status == "healthy" else "degraded",
        "database": db_status,
        "cache": cache_status,
        "timestamp": datetime.utcnow()
    }
```

### Performance Monitoring
```python
# backend/core/monitoring.py - Request timing and metrics
from fastapi import Request, Response
import time
import structlog

logger = structlog.get_logger("api.performance")

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    logger.info(
        "Request completed",
        method=request.method,
        url=str(request.url),
        status_code=response.status_code,
        process_time=round(process_time, 4)
    )
    
    response.headers["X-Process-Time"] = str(process_time)
    return response
```

---

---

## Production Security & Configuration Management

### Secrets Management Strategy
```yaml
# .env.example - Template for environment variables
# Copy to .env and fill in actual values (NEVER commit .env)

# Database
DATABASE_URL=postgresql://kidney_genetics:your_password@localhost/kidney_genetics_db
POSTGRES_USER=kidney_genetics
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=kidney_genetics_db

# Redis
REDIS_URL=redis://localhost:6379

# API Security
SECRET_KEY=your-super-secret-jwt-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# External API Keys (fill with actual keys)
NCBI_API_KEY=your_ncbi_api_key
OMIM_API_KEY=your_omim_api_key
COSMIC_USERNAME=your_cosmic_username
COSMIC_PASSWORD=your_cosmic_password

# Production overrides
ENVIRONMENT=development
LOG_LEVEL=INFO
```

### Production Secrets Injection
```yaml
# docker-compose.prod.yml - Production with external secrets
version: '3.8'
services:
  api:
    build: ./backend
    environment:
      # Inject from Docker Secrets / AWS Secrets Manager / Vault
      - DATABASE_URL_FILE=/run/secrets/database_url  
      - SECRET_KEY_FILE=/run/secrets/jwt_secret
      - NCBI_API_KEY_FILE=/run/secrets/ncbi_api_key
    secrets:
      - database_url
      - jwt_secret
      - ncbi_api_key

secrets:
  database_url:
    external: true
  jwt_secret:
    external: true
  ncbi_api_key:
    external: true
```

### Automated Dependency Security Scanning
```yaml
# .github/workflows/security.yml - Automated security scanning
name: Security Scan

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 0 * * 1'  # Weekly scans

jobs:
  python-security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Python Security Scan
        uses: pypa/pip-audit-action@v1
        with:
          inputs: backend/requirements.txt
          
      - name: Bandit Security Scan
        run: |
          pip install bandit
          bandit -r backend/ -f json -o bandit-report.json
          
      - name: Upload Security Report
        uses: actions/upload-artifact@v3
        with:
          name: security-report
          path: bandit-report.json

  javascript-security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Node.js Security Audit
        run: |
          cd frontend
          npm audit --audit-level=high
          
      - name: Snyk Security Scan
        uses: snyk/actions/node@master
        env:
          SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
        with:
          args: --severity-threshold=high

  dependabot-config:
    # Create .github/dependabot.yml
    contents: |
      version: 2
      updates:
        - package-ecosystem: "pip"
          directory: "/backend"
          schedule:
            interval: "weekly"
          open-pull-requests-limit: 10
          
        - package-ecosystem: "npm"
          directory: "/frontend"
          schedule:
            interval: "weekly"
          open-pull-requests-limit: 10
```

### Enhanced Pre-commit Security Hooks  
```yaml
# .pre-commit-config.yaml - Enhanced with security scanning
repos:
  - repo: https://github.com/charliermarsh/ruff-pre-commit
    rev: v0.1.6
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.7.1
    hooks:
      - id: mypy
        additional_dependencies: [types-requests, types-PyYAML]

  - repo: https://github.com/PyCQA/bandit
    rev: 1.7.5
    hooks:
      - id: bandit
        args: ['-r', 'backend/', '--skip', 'B101,B601']
        
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']
        
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: detect-private-key
      - id: check-merge-conflict
```

---

## Enhanced Testing Strategy

### API Testing Framework
```python
# tests/test_api.py - Comprehensive API testing
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Use separate test database
SQLALCHEMY_DATABASE_URL = "postgresql://test_user:test_pass@localhost/test_kidney_genetics"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture
def test_db():
    """Create isolated test database for each test"""
    # Create all tables
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Drop all tables
        Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client(test_db):
    """FastAPI test client with test database"""
    def override_get_db():
        try:
            yield test_db
        finally:
            test_db.close()
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client

def test_gene_list_endpoint(client):
    """Test gene listing with pagination"""
    response = client.get("/api/v1/genes/")
    assert response.status_code == 200
    data = response.json()
    assert "genes" in data
    assert "total" in data
    assert len(data["genes"]) <= 20  # Default limit
```

### Pipeline Testing with Mocking
```python
# tests/test_pipeline.py - Pipeline testing with external service mocking
import pytest
from unittest.mock import patch, MagicMock
import respx
import httpx

@pytest.mark.asyncio
@respx.mock
async def test_panelapp_source():
    """Test PanelApp data source with mocked HTTP responses"""
    # Mock PanelApp API response
    respx.get("https://panelapp.genomicsengland.co.uk/api/v1/panels/").mock(
        return_value=httpx.Response(200, json={"results": [{"id": 1, "name": "Test Panel"}]})
    )
    
    # Test source fetch
    from pipeline.sources.g01_panelapp import fetch_panelapp_data
    result = await fetch_panelapp_data(test_config)
    
    assert len(result) > 0
    assert "gene_symbol" in result[0]

@patch('pipeline.sources.g01_panelapp.requests.get')
def test_panelapp_error_handling(mock_get):
    """Test error handling in PanelApp source"""
    # Mock network failure
    mock_get.side_effect = requests.RequestException("Network error")
    
    with pytest.raises(requests.RequestException):
        fetch_panelapp_data(test_config)
```

### Pre-commit Hooks Configuration
```yaml
# .pre-commit-config.yaml - Automated code quality enforcement
repos:
  - repo: https://github.com/charliermarsh/ruff-pre-commit
    rev: v0.1.6
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.7.1
    hooks:
      - id: mypy
        additional_dependencies: [types-requests, types-PyYAML]

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
```

### Idempotent Migration Scripts
```python
# scripts/migrate_csv_to_postgres.py - Robust data migration
import pandas as pd
from sqlalchemy.orm import Session
import hashlib
import logging

logger = logging.getLogger(__name__)

class IdempotentMigrator:
    """Idempotent migration that can be safely re-run"""
    
    def __init__(self, db: Session):
        self.db = db
        self.processed_files = set()
        self.load_migration_state()
    
    def load_migration_state(self):
        """Load record of which files have been processed"""
        # Check for migration tracking table
        result = self.db.execute("""
            SELECT filename, file_hash FROM migration_log 
            WHERE status = 'completed'
        """)
        self.processed_files = {(row.filename, row.file_hash) for row in result}
    
    def migrate_csv_file(self, csv_path: Path):
        """Migrate single CSV file with idempotency check"""
        # Calculate file hash for change detection
        file_hash = self.calculate_file_hash(csv_path)
        file_key = (csv_path.name, file_hash)
        
        if file_key in self.processed_files:
            logger.info(f"Skipping {csv_path.name} - already processed")
            return
        
        try:
            # Record migration start
            self.db.execute("""
                INSERT INTO migration_log (filename, file_hash, status, started_at)
                VALUES (:filename, :file_hash, 'running', NOW())
            """, {"filename": csv_path.name, "file_hash": file_hash})
            
            # Process CSV data
            df = pd.read_csv(csv_path)
            self.process_dataframe(df, csv_path.name)
            
            # Mark as completed
            self.db.execute("""
                UPDATE migration_log 
                SET status = 'completed', completed_at = NOW()
                WHERE filename = :filename AND file_hash = :file_hash
            """, {"filename": csv_path.name, "file_hash": file_hash})
            
            self.db.commit()
            logger.info(f"Successfully migrated {csv_path.name}")
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Migration failed for {csv_path.name}: {e}")
            raise
    
    def calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of file for change detection"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            hash_sha256.update(f.read())
        return hash_sha256.hexdigest()
```

---

## Implementation Subtasks & Reference Materials

### Independent Implementation Components

Based on the comprehensive analysis and planning, the kidney-genetics-db modernization has been divided into **three independent implementation components** that can be developed in parallel:

#### 1. Database Implementation
**Location**: [plan/database/README.md](plan/database/README.md)

**Overview**: PostgreSQL-based database implementing the enhanced hybrid architecture with core metrics as relational columns and detailed evidence in JSONB. This design combines the query performance of relational data with the flexibility of document storage.

**Key Features**:
- Hybrid PostgreSQL architecture (relational core metrics + JSONB detailed evidence)
- Content addressability with SHA-256 hashing for immutable versioning
- Professional curation workflow with comprehensive audit logging
- Advanced database functions for evidence metrics calculation
- Comprehensive indexing strategy for performance optimization
- Alembic migration structure

**Reference Files**:
- Enhanced gene curation schema: [plan/schema/enhanced_gene_curation.json](plan/schema/enhanced_gene_curation.json)
- Schema comparison analysis: [plan/docs/schema_comparison_analysis.md](plan/docs/schema_comparison_analysis.md)

#### 2. Backend API Implementation  
**Location**: [plan/backend/README.md](plan/backend/README.md)

**Overview**: FastAPI-based backend implementing the enhanced GenCC-compatible schema with hybrid relational + JSONB architecture. This backend will serve as the core API for our kidney genetics curation platform.

**Key Features**:
- FastAPI with Pydantic v2 for comprehensive data validation
- Hybrid SQLAlchemy models (relational + JSONB)
- Auto-generated Pydantic schemas from JSON Schema
- Evidence scoring engine with weighted source categories
- Professional multi-stage curation workflow
- Complete GenCC export capability for international database submission

**Reference Files from Existing Projects**:
- CLI interface structure: [plan/backend/api_examples/cli.py](plan/backend/api_examples/cli.py)
- PanelApp Python client: [plan/pipeline/sources/g01_panelapp.py](plan/pipeline/sources/g01_panelapp.py)
- HPO Python implementation: [plan/pipeline/sources/g02_hpo.py](plan/pipeline/sources/g02_hpo.py)
- Pipeline architecture: [plan/pipeline/pipeline.py](plan/pipeline/pipeline.py)
- PanelApp R functions: [plan/pipeline/sources/panelapp-functions.R](plan/pipeline/sources/panelapp-functions.R)

#### 3. Frontend Implementation
**Location**: [plan/frontend/README.md](plan/frontend/README.md)

**Overview**: Modern Vue 3 + Vite frontend implementing a sophisticated gene curation interface with real-time data visualization, professional workflow management, and advanced search capabilities. Built specifically for scientific curation workflows.

**Key Features**:
- Vue 3 with Composition API + TypeScript
- Vuetify 3 for Material Design components
- Advanced search interface with multiple criteria filtering
- Data visualization components for evidence scoring
- Professional workflow management interface
- Real-time updates with Vite Hot Module Replacement

### Implementation Planning Materials

#### Enhanced Schema Development
The implementation is built around a scientifically rigorous, GenCC-compatible schema that has evolved through multiple iterations:

1. **Enhanced Gene Curation Schema**: [plan/schema/enhanced_gene_curation.json](plan/schema/enhanced_gene_curation.json)
   - Hybrid architecture with relational core metrics + JSONB flexibility
   - Content addressability with SHA-256 hashing
   - Professional curation workflow integration
   - Complete provenance tracking for all data points

2. **Schema Example**: [plan/examples/enhanced_schema_example.json](plan/examples/enhanced_schema_example.json)
   - Complete PKD1 gene example demonstrating all schema features
   - Comprehensive evidence structure with multiple source types
   - Professional workflow with audit trail
   - Enhanced quality control features

3. **Schema Comparison Analysis**: [plan/docs/schema_comparison_analysis.md](plan/docs/schema_comparison_analysis.md)
   - Detailed comparison with Gene Curator hybrid architecture
   - Performance benefits and scientific integrity features
   - Migration strategy and implementation recommendations

#### Source Code Reference Files

**From kidney-genetics (R functions)**:
- PanelApp API logic: [plan/pipeline/sources/panelapp-functions.R](plan/pipeline/sources/panelapp-functions.R)
- HPO processing: [plan/pipeline/sources/hpo-functions.R](plan/pipeline/sources/hpo-functions.R) 
- Blueprint Genetics parsing: [plan/pipeline/sources/blueprintgenetics-functions.R](plan/pipeline/sources/blueprintgenetics-functions.R)
- Data merging algorithms: [plan/pipeline/sources/A_MergeAnalysesSources.R](plan/pipeline/sources/A_MergeAnalysesSources.R)

**From custom-panel (Python implementations)**:
- PanelApp Python client: [plan/pipeline/sources/g01_panelapp.py](plan/pipeline/sources/g01_panelapp.py)
- HPO Python implementation: [plan/pipeline/sources/g02_hpo.py](plan/pipeline/sources/g02_hpo.py)
- Pipeline architecture: [plan/pipeline/pipeline.py](plan/pipeline/pipeline.py)
- CLI interface structure: [plan/backend/api_examples/cli.py](plan/backend/api_examples/cli.py)

#### Project Organization

**Complete planning structure organized in plan/ subfolder**:
```
plan/
├── README.md                                    # Complete planning overview
├── schema/
│   ├── enhanced_gene_curation.json             # Enhanced hybrid schema
│   └── gene_curation.json                      # Original refined schema
├── examples/
│   └── enhanced_schema_example.json            # Complete PKD1 example
├── docs/
│   └── schema_comparison_analysis.md           # Gene Curator comparison
├── backend/
│   ├── README.md                               # FastAPI implementation plan
│   └── api_examples/
│       └── cli.py                              # CLI interface reference
├── database/
│   └── README.md                               # PostgreSQL implementation plan
├── frontend/
│   └── README.md                               # Vue.js implementation plan
└── pipeline/
    ├── pipeline.py                             # Pipeline architecture reference
    └── sources/
        ├── g01_panelapp.py                     # PanelApp Python client
        ├── g02_hpo.py                          # HPO Python implementation
        ├── panelapp-functions.R                # PanelApp R functions
        ├── hpo-functions.R                     # HPO R functions
        ├── blueprintgenetics-functions.R       # Blueprint Genetics R functions
        └── A_MergeAnalysesSources.R            # Data merging R functions
```

### Implementation Strategy

#### Parallel Development Approach
The three components can be developed independently:

1. **Database First**: Set up PostgreSQL schema and migration framework
2. **Backend Parallel**: Develop FastAPI application with database integration
3. **Frontend Parallel**: Build Vue.js interface consuming the API

#### Technology Integration Points
- **Database ↔ Backend**: SQLAlchemy ORM with hybrid relational + JSONB models
- **Backend ↔ Frontend**: RESTful JSON API with comprehensive OpenAPI documentation
- **Data Pipeline**: Celery-based background processing with Redis message broker

#### Development Environment
All components utilize the Docker-based development environment with hot reloading:
- **Database**: PostgreSQL with extensions and persistent data
- **Backend**: FastAPI with auto-reload (1-2 second restart)
- **Frontend**: Vite with Hot Module Replacement (<50ms updates)
- **Pipeline**: Celery workers with code reloading

### Next Steps

With all planning materials organized and comprehensive implementation plans created, the project is ready for parallel development across all three components. Each component has detailed README files with specific implementation guidance, reference source code from existing projects, and clear integration points.

The enhanced schema provides a scientifically rigorous foundation that supports both high-performance queries and flexible data modeling, ensuring the platform can serve as a state-of-the-art gene curation system with international database submission capabilities.

---

## Conclusion

This migration plan transforms the kidney-genetics project from a manual, R-based pipeline into a modern, automated, and interactive web platform while preserving all existing functionality and data integrity. The phased approach ensures minimal risk with maximum benefit, providing the kidney genetics research community with a powerful, scalable tool for genetic discovery and clinical application.

The success of this migration will be measured not only by technical metrics but by its impact on advancing kidney disease research and improving patient outcomes through better genetic understanding and clinical decision support.