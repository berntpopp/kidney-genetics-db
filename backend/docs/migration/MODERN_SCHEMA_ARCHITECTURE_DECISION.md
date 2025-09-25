# Modern Database Schema Architecture Decision
## Date: 2025-09-25
## Status: FINAL DECISION FOR COMPLETE RESET

## Executive Summary
We're performing a complete database reset to implement a modern, consistent schema that eliminates ALL 124 differences and technical debt. No data preservation needed - full recomputation planned.

## Key Architecture Decisions

### 1. PRIMARY KEYS: Use BIGSERIAL, Not UUID
**Decision**: BIGSERIAL (BIGINT with auto-increment)

**Rationale**:
- **Performance**: INTEGER/BIGINT primary keys are 4-8 bytes vs 16 bytes for UUID
- **Index Performance**: B-tree indexes work better with sequential integers
- **Join Performance**: Integer joins are significantly faster
- **Storage**: Less storage overhead (50% less for PKs)
- **Readability**: Easier debugging and manual queries
- **PostgreSQL Native**: BIGSERIAL is PostgreSQL's recommended approach

**Implementation**:
```sql
id BIGSERIAL PRIMARY KEY  -- 8-byte auto-incrementing integer
```

**When to use UUID**:
- Only for external identifiers (API tokens, public references)
- Store as additional column when needed: `external_id UUID DEFAULT gen_random_uuid()`

### 2. TIMESTAMPS: Always WITH TIME ZONE (UTC)
**Decision**: ALL timestamps use `TIMESTAMP WITH TIME ZONE`

**Rationale**:
- **Best Practice**: PostgreSQL documentation recommends timestamptz
- **Automatic Conversion**: PostgreSQL handles timezone conversion
- **No Ambiguity**: Stored as UTC internally
- **Future-Proof**: Supports global applications

**Implementation**:
```sql
created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
```

### 3. JSONB: Use for Semi-Structured Data
**Decision**: JSONB for all JSON data (not JSON)

**Rationale**:
- **Performance**: Binary format is faster to query
- **Indexing**: Supports GIN indexes for fast lookups
- **Validation**: Rejects invalid JSON
- **Operators**: Rich query operators

**Implementation**:
```sql
annotations JSONB NOT NULL DEFAULT '{}'
metadata JSONB NOT NULL DEFAULT '{}'
```

### 4. TEXT vs VARCHAR
**Decision**: Use TEXT for variable-length strings

**Rationale**:
- **PostgreSQL Internal**: VARCHAR and TEXT are identical internally
- **No Performance Difference**: Same storage mechanism
- **Flexibility**: No artificial length limits
- **Exception**: Use VARCHAR(n) only when business logic requires length constraint

**Implementation**:
```sql
name TEXT NOT NULL           -- No artificial limit
email VARCHAR(255) NOT NULL  -- Only if email standard requires
```

### 5. ARRAYS: Use PostgreSQL Native Arrays
**Decision**: Use native arrays for list data

**Rationale**:
- **Performance**: Better than JSONB for simple lists
- **Type Safety**: Enforces element types
- **Operators**: Rich array operators and functions

**Implementation**:
```sql
aliases TEXT[] DEFAULT '{}'
tags TEXT[] DEFAULT '{}'
```

### 6. DEFAULTS: Always at Database Level
**Decision**: Define ALL defaults in database, not just ORM

**Rationale**:
- **Consistency**: Works regardless of client
- **Performance**: Database handles defaults efficiently
- **Data Integrity**: Ensures values even with direct SQL

**Implementation**:
```sql
-- Timestamps
created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()

-- Counters
view_count BIGINT NOT NULL DEFAULT 0

-- Booleans
is_active BOOLEAN NOT NULL DEFAULT true

-- JSONB
metadata JSONB NOT NULL DEFAULT '{}'

-- Arrays
tags TEXT[] NOT NULL DEFAULT '{}'
```

### 7. INDEXES: Strategic, Not Automatic
**Decision**: Only create indexes based on actual query patterns

**Required Indexes**:
- Primary keys (automatic)
- Foreign keys (for joins)
- Unique constraints
- Common WHERE clause columns
- Timestamp columns used for sorting

**Implementation**:
```sql
-- Foreign key index
CREATE INDEX idx_gene_annotations_gene_id ON gene_annotations(gene_id);

-- Query pattern index
CREATE INDEX idx_genes_approved_symbol ON genes(approved_symbol);

-- Timestamp sorting
CREATE INDEX idx_system_logs_timestamp ON system_logs(timestamp DESC);

-- JSONB GIN index
CREATE INDEX idx_annotations_gin ON gene_annotations USING gin(annotations);
```

### 8. NAMING CONVENTIONS
**Decision**: Consistent PostgreSQL naming

**Rules**:
- Tables: `snake_case`, plural (e.g., `gene_annotations`)
- Columns: `snake_case` (e.g., `created_at`)
- Primary Keys: Always `id`
- Foreign Keys: `<table>_id` (e.g., `gene_id`)
- Indexes: `idx_<table>_<column(s)>`
- Constraints: `<table>_<column>_<type>` (e.g., `users_email_unique`)

### 9. CONSTRAINTS: Enforce at Database Level
**Decision**: All business rules in database constraints

**Implementation**:
```sql
-- NOT NULL for required fields
email TEXT NOT NULL

-- UNIQUE for business keys
CONSTRAINT users_email_unique UNIQUE (email)

-- CHECK for valid ranges
CONSTRAINT positive_score CHECK (score >= 0)

-- Foreign keys with CASCADE options
FOREIGN KEY (gene_id) REFERENCES genes(id) ON DELETE CASCADE
```

### 10. ALEMBIC MIGRATIONS: Clean Single Migration
**Decision**: Single consolidated migration for fresh start

**Rationale**:
- **Clean History**: No legacy migrations
- **Performance**: Single transaction for schema creation
- **Maintainable**: One file to understand entire schema

## Schema Blueprint

```sql
-- Core tables with modern patterns
CREATE TABLE genes (
    id BIGSERIAL PRIMARY KEY,
    hgnc_id TEXT UNIQUE NOT NULL,
    approved_symbol TEXT NOT NULL,
    approved_name TEXT NOT NULL,
    aliases TEXT[] DEFAULT '{}',
    omim_id TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE gene_annotations (
    id BIGSERIAL PRIMARY KEY,
    gene_id BIGINT NOT NULL REFERENCES genes(id) ON DELETE CASCADE,
    source TEXT NOT NULL,
    version TEXT NOT NULL,
    annotations JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT unique_gene_source_version UNIQUE(gene_id, source, version)
);

-- Indexes based on query patterns
CREATE INDEX idx_genes_approved_symbol ON genes(approved_symbol);
CREATE INDEX idx_genes_hgnc_id ON genes(hgnc_id);
CREATE INDEX idx_gene_annotations_gene_id ON gene_annotations(gene_id);
CREATE INDEX idx_gene_annotations_source ON gene_annotations(source);
CREATE INDEX idx_annotations_gin ON gene_annotations USING gin(annotations);
```

## Migration Strategy

### Phase 1: Backup Current State
```bash
pg_dump -U postgres kidney_genetics_db > backup_before_reset.sql
```

### Phase 2: Drop and Recreate Database
```bash
dropdb kidney_genetics_db
createdb kidney_genetics_db
```

### Phase 3: Apply New Schema
```bash
alembic upgrade head  # Single new migration
```

### Phase 4: Recompute All Data
```bash
python scripts/recompute_all_data.py
```

## Benefits of This Approach

1. **Performance**:
   - 50% less storage for primary keys
   - Faster joins with BIGINT
   - Optimized indexes based on actual usage

2. **Consistency**:
   - All timestamps in UTC with timezone
   - All JSON as JSONB
   - All defaults at database level

3. **Maintainability**:
   - Clear naming conventions
   - Single migration file
   - Database-enforced constraints

4. **Modern Best Practices**:
   - No UUIDs for primary keys (performance)
   - JSONB for semi-structured data
   - Native arrays for lists
   - Strategic indexing

5. **Zero Technical Debt**:
   - No legacy columns
   - No mismatched types
   - No missing constraints
   - No unnecessary indexes

## Conclusion
This architecture provides a clean, modern, performant database schema that follows PostgreSQL best practices and eliminates all 124 existing inconsistencies. The use of BIGSERIAL over UUID for primary keys ensures optimal performance while maintaining simplicity.