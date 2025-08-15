# Database Implementation Plan (Lean Version)

## Overview

Simple PostgreSQL database for storing kidney genetics data from 5 core sources (PanelApp, Literature, Diagnostic Panels, HPO, PubTator) with basic API access.

## Core Schema

### 1. Minimal Tables

```sql
-- Users for basic auth
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    is_admin BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Genes master table
CREATE TABLE genes (
    id SERIAL PRIMARY KEY,
    hgnc_id VARCHAR(50) UNIQUE,
    approved_symbol VARCHAR(100) NOT NULL,
    aliases TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Gene evidence from sources
CREATE TABLE gene_evidence (
    id SERIAL PRIMARY KEY,
    gene_id INTEGER REFERENCES genes(id),
    source_name VARCHAR(100) NOT NULL, -- 'PanelApp', 'Literature', 'DiagnosticPanel', 'HPO', 'PubTator'
    source_detail VARCHAR(255), -- e.g., 'PanelApp UK Panel 234'
    evidence_data JSONB NOT NULL, -- Flexible storage for source-specific data
    evidence_date DATE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Final curated gene list (output of merge/annotation)
CREATE TABLE gene_curations (
    id SERIAL PRIMARY KEY,
    gene_id INTEGER REFERENCES genes(id) UNIQUE,
    evidence_count INTEGER DEFAULT 0,
    source_count INTEGER DEFAULT 0,
    
    -- Core kidney genetics fields from R pipeline
    panelapp_panels TEXT[],
    literature_refs TEXT[],
    diagnostic_panels TEXT[],
    hpo_terms TEXT[],
    pubtator_pmids TEXT[],
    
    -- Annotations
    omim_data JSONB,
    clinvar_data JSONB,
    constraint_scores JSONB, -- pLI, oe_lof, etc.
    expression_data JSONB, -- GTEx kidney expression
    
    -- Summary scores
    evidence_score NUMERIC(5,2),
    classification VARCHAR(50),
    
    last_updated TIMESTAMPTZ DEFAULT NOW()
);

-- Pipeline runs tracking
CREATE TABLE pipeline_runs (
    id SERIAL PRIMARY KEY,
    status VARCHAR(50) DEFAULT 'running',
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    stats JSONB, -- genes added, updated, sources processed
    error_log TEXT
);
```

### 2. Essential Indexes

```sql
CREATE INDEX idx_genes_symbol ON genes(approved_symbol);
CREATE INDEX idx_evidence_gene ON gene_evidence(gene_id);
CREATE INDEX idx_evidence_source ON gene_evidence(source_name);
CREATE INDEX idx_curations_score ON gene_curations(evidence_score DESC);
```

## Docker Development Setup

```yaml
# docker-compose.yml
version: '3.8'

services:
  postgres:
    image: postgres:14-alpine
    container_name: kidney_genetics_db
    environment:
      POSTGRES_DB: kidney_genetics
      POSTGRES_USER: kidney_user
      POSTGRES_PASSWORD: kidney_pass
    ports:
      - "5432:5432"
    volumes:
      - ./postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
```

## Alembic Migrations

```python
# alembic/env.py - Simple configuration
from sqlalchemy import create_engine
from alembic import context
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://kidney_user:kidney_pass@localhost/kidney_genetics")

def run_migrations_online():
    engine = create_engine(DATABASE_URL)
    with engine.connect() as connection:
        context.configure(connection=connection)
        with context.begin_transaction():
            context.run_migrations()
```

## Data Flow

1. **Pipeline fetches from original sources** → Fresh computation each run
2. **Sources processed** → Data stored in `gene_evidence` table
3. **Merge process** → Aggregates evidence → `gene_curations` table  
4. **API reads** → `gene_curations` for display
5. **No CSV migration** → All data recomputed from scratch

## Key Queries

```sql
-- Get all curated genes with high evidence
SELECT g.approved_symbol, gc.* 
FROM gene_curations gc
JOIN genes g ON gc.gene_id = g.id
WHERE gc.evidence_score > 5.0
ORDER BY gc.evidence_score DESC;

-- Get evidence for specific gene
SELECT * FROM gene_evidence 
WHERE gene_id = (SELECT id FROM genes WHERE approved_symbol = 'PKD1');

-- Summary statistics
SELECT 
    COUNT(*) as total_genes,
    AVG(evidence_score) as avg_score,
    COUNT(DISTINCT source_name) as sources
FROM gene_curations gc
JOIN gene_evidence ge ON gc.gene_id = ge.gene_id;
```

This lean design focuses on storing and serving the kidney genetics data efficiently without unnecessary complexity.