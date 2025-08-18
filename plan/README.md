# Planning Directory - Reference Materials

This directory contains reference implementations and planning documents for features under active development.

## Current Contents

### `pipeline/`
Reference implementations from the original R pipeline and Python ports:
- **R Functions** (`sources/*.R`) - Original kidney-genetics logic for comparison
- **Python Modules** (`sources/g*.py`) - Reference Python implementations
- **Config Examples** - Sample configuration files

### `schema/`
JSON schema definitions for data validation:
- `gene_curation.json` - Complete GenCC-compatible schema
- `enhanced_gene_curation.json` - Extended schema with additional fields

### `examples/`
Example data and configuration files:
- `gencc_mapping_example.json` - GenCC submission mapping
- `refined_schema_example.json` - Complete gene example
- `enhanced_schema_example.json` - Extended schema example

### Legacy Planning Documents
- `STYLE-GUIDE.md` - Code style guidelines (for reference)
- Other planning documents that may be useful for future features

## Completed Documentation
✅ **Moved to `/docs`**: All documentation for implemented features has been relocated to the main documentation directory:
- `/docs/architecture/` - Database and backend architecture
- `/docs/development/` - Setup and development guides  
- `/docs/data-sources/` - Data source documentation
- `/docs/implementation/` - Implementation details

## Usage

### For New Feature Development
1. Reference the original R implementations in `pipeline/sources/`
2. Use schema definitions for data validation
3. Check examples for data structure patterns

### For Bug Fixes
- Compare current implementation with reference R code
- Validate data against schema definitions
- Use example files for testing

## Note
This directory should only contain reference materials and planning for **unimplemented features**. Once a feature is complete, move its documentation to `/docs`.