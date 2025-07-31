# Database Implementation Plan

## Overview

PostgreSQL-based database implementing the enhanced hybrid architecture with core metrics as relational columns and detailed evidence in JSONB. This design combines the query performance of relational data with the flexibility of document storage.

## Architecture Design

### Technology Stack
- **Database**: PostgreSQL 15+ with JSONB support
- **Extensions**: pg_jsonschema for JSONB validation
- **Migrations**: Alembic for version control
- **Indexing**: GIN indexes for JSONB queries, B-tree for relational columns
- **Constraints**: Database-level validation and integrity
- **Backup**: pg_dump with point-in-time recovery

### Database Schema Structure

```sql
-- Core ENUMs for data integrity
CREATE TYPE curation_status AS ENUM (
    'Automated', 
    'In_Primary_Review', 
    'In_Secondary_Review', 
    'Expert_Review',
    'Approved', 
    'Rejected', 
    'Published'
);

CREATE TYPE confidence_classification AS ENUM (
    'Definitive',
    'Strong', 
    'Moderate',
    'Limited',
    'Disputed',
    'Refuted',
    'No Known Disease Relationship',
    'Animal Model Only'
);

CREATE TYPE user_role AS ENUM ('viewer', 'curator', 'admin');
```

### Core Tables Design

#### 1. Users Table
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    institution VARCHAR(255),
    role user_role NOT NULL DEFAULT 'viewer',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
```

#### 2. Genes Table  
```sql
CREATE TABLE genes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hgnc_id VARCHAR(50) UNIQUE NOT NULL,
    approved_symbol VARCHAR(100) NOT NULL,
    aliases TEXT[],
    genomic_coordinates JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_genes_hgnc_id ON genes(hgnc_id);
CREATE INDEX idx_genes_symbol ON genes(approved_symbol);
CREATE INDEX idx_genes_aliases ON genes USING GIN(aliases);
```

#### 3. Enhanced Curations Table (Hybrid Architecture)
```sql
CREATE TABLE gene_curations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    gene_id UUID NOT NULL REFERENCES genes(id) ON DELETE CASCADE,
    
    -- CORE METRICS (Relational columns for fast queries)
    total_evidence_score NUMERIC(5,2) NOT NULL DEFAULT 0.0,
    highest_confidence_classification confidence_classification NOT NULL,
    evidence_source_count INTEGER NOT NULL DEFAULT 0,
    expert_panel_count INTEGER NOT NULL DEFAULT 0,
    literature_source_count INTEGER NOT NULL DEFAULT 0,
    
    -- VERSIONING & INTEGRITY (Content addressability)
    record_hash VARCHAR(64) NOT NULL UNIQUE,
    previous_hash VARCHAR(64),
    version_number INTEGER NOT NULL DEFAULT 1,
    
    -- WORKFLOW STATUS (Relational for fast filtering)
    workflow_status curation_status NOT NULL DEFAULT 'Automated',
    primary_curator UUID REFERENCES users(id),
    secondary_curator UUID REFERENCES users(id),
    
    -- COMPLETE CURATION DATA (JSONB for flexibility)
    curation_data JSONB NOT NULL,
    
    -- AUDIT FIELDS
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- CONSTRAINTS
    CONSTRAINT valid_evidence_score CHECK (total_evidence_score >= 0 AND total_evidence_score <= 100),
    CONSTRAINT valid_source_counts CHECK (evidence_source_count >= 0 AND expert_panel_count >= 0),
    CONSTRAINT valid_version CHECK (version_number > 0),
    
    -- JSONB Schema Validation
    CONSTRAINT valid_curation_data CHECK (
        -- Required fields validation
        (curation_data ? 'hgnc_id') AND
        (curation_data ? 'approved_symbol') AND
        (curation_data ? 'assertions') AND
        (curation_data ? 'versioning') AND
        (curation_data ? 'curation_workflow') AND
        
        -- Structure validation
        (jsonb_typeof(curation_data->'assertions') = 'array') AND
        (curation_data->'versioning'->>'record_hash' = record_hash) AND
        (curation_data->'versioning'->>'version_number')::integer = version_number
    )
);
```

#### 4. Comprehensive Indexing Strategy
```sql
-- Fast queries on core metrics (relational columns)
CREATE INDEX idx_curations_score ON gene_curations(total_evidence_score);
CREATE INDEX idx_curations_classification ON gene_curations(highest_confidence_classification);
CREATE INDEX idx_curations_evidence_count ON gene_curations(evidence_source_count);
CREATE INDEX idx_curations_expert_panels ON gene_curations(expert_panel_count);
CREATE INDEX idx_curations_workflow_status ON gene_curations(workflow_status);

-- Version chain navigation
CREATE INDEX idx_curations_hash ON gene_curations(record_hash);
CREATE INDEX idx_curations_previous_hash ON gene_curations(previous_hash);

-- JSONB indexes for complex queries
CREATE INDEX idx_curations_jsonb_gin ON gene_curations USING GIN (curation_data);

-- Specific JSONB path indexes for common queries
CREATE INDEX idx_curations_assertions ON gene_curations 
USING GIN ((curation_data->'assertions'));

CREATE INDEX idx_curations_evidence_sources ON gene_curations 
USING GIN ((curation_data->'assertions'->0->'evidence'));

CREATE INDEX idx_curations_workflow_details ON gene_curations 
USING GIN ((curation_data->'curation_workflow'));

CREATE INDEX idx_curations_ancillary_data ON gene_curations 
USING GIN ((curation_data->'ancillary_data'));

-- Specific operational indexes
CREATE INDEX idx_curations_curator ON gene_curations 
USING GIN ((curation_data->'curation_workflow'->'primary_curator'));

CREATE INDEX idx_curations_external_submissions ON gene_curations 
USING GIN ((curation_data->'curation_workflow'->'external_submissions'));
```

#### 5. Audit Log Table
```sql
CREATE TABLE curation_audit_log (
    id BIGSERIAL PRIMARY KEY,
    curation_id UUID NOT NULL REFERENCES gene_curations(id),
    user_id UUID REFERENCES users(id),
    action VARCHAR(50) NOT NULL,
    previous_state JSONB,
    new_state JSONB,
    changes_summary JSONB,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    digital_signature VARCHAR(512)
);

CREATE INDEX idx_audit_curation ON curation_audit_log(curation_id);
CREATE INDEX idx_audit_timestamp ON curation_audit_log(timestamp);
CREATE INDEX idx_audit_user ON curation_audit_log(user_id);
```

## Advanced Database Features

### 1. Content Hash Generation Function
```sql
CREATE OR REPLACE FUNCTION generate_content_hash(content JSONB) 
RETURNS VARCHAR(64) AS $$
BEGIN
    RETURN encode(digest(content::text, 'sha256'), 'hex');
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Trigger to auto-generate hash on insert/update
CREATE OR REPLACE FUNCTION update_content_hash() 
RETURNS TRIGGER AS $$
BEGIN
    NEW.record_hash = generate_content_hash(NEW.curation_data);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_content_hash
    BEFORE INSERT OR UPDATE ON gene_curations
    FOR EACH ROW
    EXECUTE FUNCTION update_content_hash();
```

### 2. Core Metrics Calculation Functions
```sql
CREATE OR REPLACE FUNCTION calculate_evidence_metrics(curation_data JSONB)
RETURNS TABLE(
    total_score NUMERIC(5,2),
    source_count INTEGER,
    expert_panel_count INTEGER,
    literature_count INTEGER,
    highest_classification TEXT
) AS $$
DECLARE
    assertion JSONB;
    evidence JSONB;
    score NUMERIC(5,2) := 0.0;
    sources INTEGER := 0;
    panels INTEGER := 0;
    literature INTEGER := 0;
    classification TEXT := 'No Known Disease Relationship';
BEGIN
    -- Iterate through assertions
    FOR assertion IN SELECT jsonb_array_elements(curation_data->'assertions')
    LOOP
        -- Count evidence sources
        FOR evidence IN SELECT jsonb_array_elements(assertion->'evidence')
        LOOP
            sources := sources + 1;
            
            -- Count expert panels
            IF evidence->>'source_category' = 'Expert Panel' THEN
                panels := panels + 1;
            END IF;
            
            -- Count literature
            IF evidence->>'source_category' = 'Literature' THEN
                literature := literature + 1;
            END IF;
            
            -- Add to score (weighted by source category)
            score := score + COALESCE((evidence->>'weight_in_scoring')::NUMERIC, 0.5) *
                CASE evidence->>'source_category'
                    WHEN 'Expert Panel' THEN 1.0
                    WHEN 'Literature' THEN 0.8
                    WHEN 'Diagnostic Panel' THEN 0.6
                    WHEN 'Constraint Evidence' THEN 0.4
                    ELSE 0.3
                END;
        END LOOP;
        
        -- Update highest classification
        IF assertion->>'final_classification' IN ('Definitive', 'Strong') THEN
            classification := assertion->>'final_classification';
        END IF;
    END LOOP;
    
    RETURN QUERY SELECT 
        LEAST(score, 100.0) as total_score,
        sources as source_count,
        panels as expert_panel_count, 
        literature as literature_count,
        classification as highest_classification;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-calculate metrics
CREATE OR REPLACE FUNCTION update_evidence_metrics() 
RETURNS TRIGGER AS $$
DECLARE
    metrics RECORD;
BEGIN
    SELECT * INTO metrics FROM calculate_evidence_metrics(NEW.curation_data);
    
    NEW.total_evidence_score := metrics.total_score;
    NEW.evidence_source_count := metrics.source_count;
    NEW.expert_panel_count := metrics.expert_panel_count;
    NEW.literature_source_count := metrics.literature_count;
    NEW.highest_confidence_classification := metrics.highest_classification::confidence_classification;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_evidence_metrics
    BEFORE INSERT OR UPDATE ON gene_curations
    FOR EACH ROW
    EXECUTE FUNCTION update_evidence_metrics();
```

### 3. Advanced Query Functions
```sql
-- Get curation history (version chain)
CREATE OR REPLACE FUNCTION get_curation_history(input_hash VARCHAR(64))
RETURNS TABLE(
    id UUID,
    version_number INTEGER,
    record_hash VARCHAR(64),
    previous_hash VARCHAR(64),
    created_at TIMESTAMPTZ,
    total_evidence_score NUMERIC(5,2),
    classification confidence_classification
) AS $$
DECLARE
    current_hash VARCHAR(64) := input_hash;
BEGIN
    WHILE current_hash IS NOT NULL LOOP
        RETURN QUERY
        SELECT 
            gc.id,
            gc.version_number,
            gc.record_hash,
            gc.previous_hash,
            gc.created_at,
            gc.total_evidence_score,
            gc.highest_confidence_classification
        FROM gene_curations gc
        WHERE gc.record_hash = current_hash;
        
        SELECT gc.previous_hash INTO current_hash
        FROM gene_curations gc
        WHERE gc.record_hash = current_hash;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Find conflicting evidence across curations
CREATE OR REPLACE FUNCTION find_conflicting_evidence()
RETURNS TABLE(
    gene_symbol TEXT,
    disease_count INTEGER,
    classification_conflicts JSONB
) AS $$
BEGIN
    RETURN QUERY
    WITH gene_diseases AS (
        SELECT 
            g.approved_symbol,
            assertion->>'disease_id' as disease_id,
            assertion->>'final_classification' as classification,
            COUNT(*) as assertion_count
        FROM gene_curations gc
        JOIN genes g ON gc.gene_id = g.id
        CROSS JOIN jsonb_array_elements(gc.curation_data->'assertions') AS assertion
        GROUP BY g.approved_symbol, assertion->>'disease_id', assertion->>'final_classification'
    ),
    conflicts AS (
        SELECT 
            approved_symbol,
            COUNT(DISTINCT classification) as classification_count,
            jsonb_agg(DISTINCT jsonb_build_object(
                'classification', classification,
                'count', assertion_count
            )) as classifications
        FROM gene_diseases
        GROUP BY approved_symbol
        HAVING COUNT(DISTINCT classification) > 1
    )
    SELECT 
        approved_symbol as gene_symbol,
        classification_count::INTEGER as disease_count,
        classifications as classification_conflicts
    FROM conflicts;
END;
$$ LANGUAGE plpgsql;
```

## Migration Strategy

### Alembic Migration Structure
```python
# alembic/versions/001_initial_schema.py
"""Initial schema with hybrid architecture

Revision ID: 001
Create Date: 2024-07-31 10:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    # Create ENUMs
    op.execute("CREATE TYPE user_role AS ENUM ('viewer', 'curator', 'admin');")
    op.execute("""
        CREATE TYPE confidence_classification AS ENUM (
            'Definitive', 'Strong', 'Moderate', 'Limited', 
            'Disputed', 'Refuted', 'No Known Disease Relationship', 'Animal Model Only'
        );
    """)
    op.execute("""
        CREATE TYPE curation_status AS ENUM (
            'Automated', 'In_Primary_Review', 'In_Secondary_Review', 
            'Expert_Review', 'Approved', 'Rejected', 'Published'
        );
    """)
    
    # Create tables
    op.create_table('users',
        sa.Column('id', postgresql.UUID(), nullable=False, default=sa.text('gen_random_uuid()')),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('name', sa.String(255)),
        sa.Column('institution', sa.String(255)),
        sa.Column('role', postgresql.ENUM('viewer', 'curator', 'admin', name='user_role'), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False, default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    
    # Additional tables and indexes...

def downgrade():
    op.drop_table('gene_curations')
    op.drop_table('genes')  
    op.drop_table('users')
    op.execute("DROP TYPE IF EXISTS curation_status;")
    op.execute("DROP TYPE IF EXISTS confidence_classification;")
    op.execute("DROP TYPE IF EXISTS user_role;")
```

## Performance Optimization

### Query Performance Expectations
```sql
-- Fast queries using relational columns (< 10ms)
SELECT id, approved_symbol, total_evidence_score, highest_confidence_classification
FROM gene_curations gc
JOIN genes g ON gc.gene_id = g.id
WHERE gc.total_evidence_score > 8.0 
  AND gc.highest_confidence_classification = 'Definitive'
  AND gc.expert_panel_count >= 2
ORDER BY gc.total_evidence_score DESC
LIMIT 20;

-- Complex JSONB queries with GIN indexes (< 100ms)
SELECT gc.*, g.approved_symbol
FROM gene_curations gc
JOIN genes g ON gc.gene_id = g.id
WHERE gc.curation_data->'assertions' @> '[{"evidence": [{"source_name": "ClinGen"}]}]'::jsonb
  AND gc.curation_data->'curation_workflow'->>'status' = 'Approved'
  AND gc.curation_data->'ancillary_data'->'constraint_metrics' @> '[{"source": "gnomAD"}]'::jsonb;

-- Version chain navigation (< 50ms)
SELECT * FROM get_curation_history('a1b2c3d4e5f67890...');
```

### Monitoring Queries
```sql
-- Performance monitoring
SELECT 
    schemaname,
    tablename,
    attname as column_name,
    n_distinct,
    correlation
FROM pg_stats 
WHERE tablename = 'gene_curations';

-- Index usage
SELECT 
    indexrelname as index_name,
    idx_tup_read,
    idx_tup_fetch,
    idx_scan
FROM pg_stat_user_indexes 
WHERE relname = 'gene_curations';
```

## Backup and Recovery

### Backup Strategy
```bash
# Daily full backup
pg_dump -h localhost -U postgres -d kidney_genetics_db \
  --format=custom --compress=9 \
  --file=backup_$(date +%Y%m%d).dump

# Continuous WAL archiving for point-in-time recovery
archive_command = 'cp %p /backup/wal_archive/%f'
```

This database design provides the foundation for a high-performance, scientifically rigorous gene curation platform that can handle complex analytical queries while maintaining data integrity and full audit trails.