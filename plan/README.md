# Plan Folder - Schema Design and Examples

This folder contains the planning artifacts for the kidney-genetics-db modernization project. These files are used for design, validation, and implementation planning - they are separate from the main repository to avoid contamination during parallel development.

## Structure

```
plan/
├── README.md                    # This file
├── schema/
│   └── gene_curation.json      # Complete GenCC-compatible JSON schema
├── examples/
│   ├── gencc_mapping_example.json       # GenCC submission mapping
│   └── refined_schema_example.json      # Complete PKD1 example
└── docs/
    └── schema_migration_guide.md        # Migration strategy and validation
```

## Purpose

These planning files serve as:

1. **Schema Definition**: The single source of truth for data structure
2. **Implementation Reference**: Examples showing the schema in action
3. **Migration Strategy**: Documentation for transforming existing data
4. **Validation Examples**: Test cases for schema compliance

## Key Design Principles

### 1. Scientific Rigor
- Complete provenance tracking for all data points
- Every value traceable to source and version
- Professional multi-stage curation workflow

### 2. GenCC Compatibility
- Uses standardized clinical validity terms
- Direct submission capability to international databases
- Compatible with ClinGen, OMIM, Orphanet workflows

### 3. Flexible Architecture
- Generic evidence structure accommodates any source type
- Plugin-based approach for new data sources
- No schema changes required for new sources

### 4. Data Integration
- Structured evidence arrays instead of concatenated strings
- Rich, queryable knowledge graph
- Complex analytical queries enabled

## Usage During Implementation

### For Backend Development
- Reference `schema/gene_curation.json` for Pydantic model generation
- Use `examples/refined_schema_example.json` for test data
- Follow `docs/schema_migration_guide.md` for data transformation

### For Frontend Development
- Use examples to understand data structure
- Reference schema for TypeScript interface generation
- Plan UI components around evidence arrays and workflow states

### For Pipeline Development
- Each source module should produce evidence objects matching the schema
- Use ancillary_data structure for constraint metrics, expression data, etc.
- Implement curation_workflow state machine

### For Database Setup
- Schema defines JSONB structure for PostgreSQL
- Use for database constraint generation
- Reference for index planning on nested JSON queries

## Schema Evolution

As the project develops, this folder will be updated with:
- Schema version increments
- New example data
- Updated migration strategies
- Additional validation tools

The main repository remains clean while this folder provides the detailed specification for implementation teams working in parallel.