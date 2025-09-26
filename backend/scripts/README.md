# Backend Scripts

Essential utility scripts for database and data pipeline management.

## ✅ Active Scripts

### `initialize_database.py`
**Purpose:** Initialize database after migrations
**Usage:** `uv run python scripts/initialize_database.py`
**Called by:** `make db-reset`, `make db-init`
- Creates database views
- Creates admin user
- Clears cache
- Runs initial aggregation

### `create_admin_user.py`
**Purpose:** Create admin user account
**Usage:** `uv run python scripts/create_admin_user.py`
- Creates admin@kidneygenetics.org with password ChangeMe!Admin2024
- Used for initial setup or recovery

### `run_all_sources.py`
**Purpose:** Run all data source pipelines
**Usage:** `uv run python scripts/run_all_sources.py`
- Triggers all configured data sources (PanelApp, HPO, ClinGen, etc.)
- Useful for manual full data refresh

### `rebuild_data.py`
**Purpose:** Force rebuild all data from sources
**Usage:** `uv run python scripts/rebuild_data.py`
- Runs pipeline with force=True flag
- Bypasses cache to get fresh data

### `clean_database.py`
**Purpose:** Remove all data but keep structure
**Usage:** `uv run python scripts/clean_database.py`
- Truncates data tables (genes, annotations, evidence)
- Preserves users and configuration

### `cleanup_data_sources.py`
**Purpose:** Sync data_source_progress with config
**Usage:** `uv run python scripts/cleanup_data_sources.py`
- Removes obsolete data sources from progress table
- Adds missing configured sources
- Ensures consistency between config and database

### `upload_manual_sources.py`
**Purpose:** Upload manual evidence files
**Usage:** `uv run python scripts/upload_manual_sources.py --file path/to/file.xlsx`
- Processes manual evidence uploads
- Used for literature and custom sources

## ❌ Removed Scripts (No Longer Needed)

The following migration-related scripts were removed as database schema is now stable:
- `update_models_to_bigint.py` - Schema refactor (completed)
- `fix_model_columns.py` - Schema refactor (completed)
- `final_fixes.py` - Schema refactor (completed)
- `align_models_with_migration.py` - Schema refactor (completed)
- `analyze_schema_differences.py` - Schema refactor (completed)
- `backfill_clinvar_consequences.py` - Data migration (completed)
- `setup_database.py` - Replaced by Alembic migrations

## Notes

- All scripts use the unified logging system (`app.core.logging`)
- Database connections use `app.core.database.get_db_context()`
- Scripts respect environment configuration from `.env`
- Run scripts from backend directory: `cd backend && uv run python scripts/script_name.py`