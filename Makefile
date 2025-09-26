# Kidney Genetics Database - Development Makefile
# Usage: make [command]

.PHONY: help dev-up dev-down dev-logs hybrid-up hybrid-down services-up services-down db-reset db-clean status clean-all backend frontend lint test

# Detect docker compose command (v2 vs v1)
DOCKER_COMPOSE := $(shell if command -v docker-compose >/dev/null 2>&1; then echo "docker-compose"; else echo "docker compose"; fi)

# Default target - show help
help:
	@echo "╔════════════════════════════════════════════════════════════════╗"
	@echo "║         Kidney Genetics Database - Development Commands         ║"
	@echo "╚════════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "🚀 HYBRID DEVELOPMENT (Recommended):"
	@echo "  make hybrid-up       - Start DB in Docker + run API/Frontend locally"
	@echo "  make hybrid-down     - Stop all hybrid mode services"
	@echo ""
	@echo "🐳 FULL DOCKER DEVELOPMENT:"
	@echo "  make dev-up          - Start all services in Docker"
	@echo "  make dev-down        - Stop all Docker services"
	@echo "  make dev-logs        - Show Docker logs (follow mode)"
	@echo ""
	@echo "🔧 SERVICE MANAGEMENT:"
	@echo "  make services-up     - Start only DB/Redis in Docker"
	@echo "  make services-down   - Stop Docker services"
	@echo "  make backend         - Run backend API locally"
	@echo "  make frontend        - Run frontend locally"
	@echo ""
	@echo "🗄️  DATABASE MANAGEMENT:"
	@echo "  make db-drop         - Drop and recreate database (disconnects users)"
	@echo "  make db-reset        - Complete database reset (structure + data)"
	@echo "  make db-clean        - Remove all data (keep structure)"
	@echo "  make db-verify-complete - Verify complete schema (tables + views)"
	@echo "  make db-refresh-views - Recreate all database views"
	@echo "  make db-show-view-deps - Show view dependency hierarchy"
	@echo ""
	@echo "📊 MONITORING:"
	@echo "  make status          - Show system status and statistics"
	@echo ""
	@echo "🔍 CODE QUALITY:"
	@echo "  make lint            - Lint backend code with ruff"
	@echo "  make test            - Run backend tests with pytest"
	@echo ""
	@echo "🧹 CLEANUP:"
	@echo "  make clean-backend   - Clean Python cache files (__pycache__, .pyc, etc.)"
	@echo "  make clean-all       - Stop everything and clean all data"

# ════════════════════════════════════════════════════════════════════
# HYBRID DEVELOPMENT MODE (DB in Docker, API/Frontend local)
# ════════════════════════════════════════════════════════════════════

# Start hybrid development environment
hybrid-up: services-up
	@echo "✅ Database is running in Docker"
	@echo ""
	@echo "📝 Now run in separate terminals:"
	@echo "   Terminal 1: make backend"
	@echo "   Terminal 2: make frontend"
	@echo ""
	@echo "🌐 Access points:"
	@echo "   Frontend: http://localhost:5173"
	@echo "   Backend:  http://localhost:8000/docs"
	@echo "   Database: localhost:5432"

# Stop hybrid development environment
hybrid-down:
	@echo "Stopping hybrid development environment..."
	@-pkill -f "uvicorn app.main:app" 2>/dev/null || true
	@-pkill -f "vite.*5173" 2>/dev/null || true
	@$(MAKE) services-down
	@echo "✅ Hybrid environment stopped"

# ════════════════════════════════════════════════════════════════════
# FULL DOCKER DEVELOPMENT MODE
# ════════════════════════════════════════════════════════════════════

# Start all services in Docker
dev-up:
	@echo "Starting full Docker development environment..."
	@$(DOCKER_COMPOSE) up -d
	@echo "⏳ Waiting for services to be ready..."
	@sleep 5
	@echo "✅ All services started in Docker"
	@echo ""
	@echo "🌐 Access points:"
	@echo "   Frontend: http://localhost:3000"
	@echo "   Backend:  http://localhost:8000/docs"
	@echo "   Database: localhost:5432"

# Stop all Docker services
dev-down:
	@echo "Stopping Docker development environment..."
	@$(DOCKER_COMPOSE) down
	@echo "✅ Docker environment stopped"

# Show Docker logs
dev-logs:
	@$(DOCKER_COMPOSE) logs -f

# ════════════════════════════════════════════════════════════════════
# SERVICE MANAGEMENT
# ════════════════════════════════════════════════════════════════════

# Start database and Redis in Docker
services-up:
	@echo "Starting database services in Docker..."
	@$(DOCKER_COMPOSE) -f docker-compose.services.yml up -d
	@echo "⏳ Waiting for database to be ready..."
	@sleep 3
	@docker exec kidney_genetics_postgres pg_isready -U kidney_user -d kidney_genetics >/dev/null 2>&1 && \
		echo "✅ PostgreSQL is ready" || echo "⚠️  PostgreSQL is starting..."
	@echo ""
	@echo "📍 Services:"
	@echo "   PostgreSQL: localhost:5432"

# Stop Docker services
services-down:
	@echo "Stopping Docker services..."
	@$(DOCKER_COMPOSE) -f docker-compose.services.yml down
	@echo "✅ Docker services stopped"

# Run backend locally
backend:
	@echo "Starting backend API..."
	@cd backend && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --log-level debug --access-log

# Run frontend locally
frontend:
	@echo "Starting frontend..."
	@cd frontend && npm run dev

# ════════════════════════════════════════════════════════════════════
# DATABASE MANAGEMENT
# ════════════════════════════════════════════════════════════════════

# Drop database (disconnects all users first)
db-drop: services-up
	@echo "🗑️  Dropping database (will disconnect all users)..."
	@docker exec kidney_genetics_postgres psql -U kidney_user -d postgres -c \
		"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='kidney_genetics' AND pid <> pg_backend_pid();" >/dev/null 2>&1 || true
	@docker exec kidney_genetics_postgres psql -U kidney_user -d postgres -c "DROP DATABASE IF EXISTS kidney_genetics;" >/dev/null 2>&1 || true
	@docker exec kidney_genetics_postgres psql -U kidney_user -d postgres -c "CREATE DATABASE kidney_genetics;"
	@echo "✅ Database dropped and recreated"

# Complete database reset (drop and recreate)
db-reset: db-drop
	@echo "📦 Running migrations..."
	@cd backend && uv run alembic upgrade head
	@echo "🔧 Initializing annotation sources..."
	@cd backend && uv run python -m app.scripts.init_annotation_sources || echo "⚠️  Annotation sources initialization failed"
	@echo "🎯 Running full database initialization (includes admin user)..."
	@cd backend && uv run python scripts/initialize_database.py
	@echo "✅ Database reset complete!"

# Clean all data from database (keep structure)
db-clean:
	@echo "🧹 Cleaning database data..."
	@cd backend && uv run python scripts/clean_database.py
	@echo "🔄 Re-initializing database (views, admin, cache)..."
	@cd backend && uv run python scripts/initialize_database.py
	@echo "✅ Database cleaned and re-initialized!"

# Run all data sources from scratch
data-rebuild:
	@echo "🔄 Rebuilding all data sources..."
	@cd backend && uv run python scripts/rebuild_data.py
	@echo "✅ Data rebuild complete!"

# Full database reset and rebuild
db-rebuild: db-clean data-rebuild
	@echo "✅ Full database rebuild complete!"

# ════════════════════════════════════════════════════════════════════
# MONITORING
# ════════════════════════════════════════════════════════════════════

# Show system status
status:
	@echo "╔════════════════════════════════════════════════════════════════╗"
	@echo "║                      SYSTEM STATUS                              ║"
	@echo "╚════════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "🐳 Docker Services:"
	@-docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep kidney || echo "  No services running"
	@echo ""
	@echo "🔄 Local Processes:"
	@-ps aux | grep -E "uvicorn app.main:app" | grep -v grep >/dev/null 2>&1 && echo "  ✓ Backend API running" || echo "  ✗ Backend API not running"
	@-ps aux | grep -E "vite" | grep -v grep >/dev/null 2>&1 && echo "  ✓ Frontend running" || echo "  ✗ Frontend not running"
	@echo ""
	@echo "📊 Database Statistics:"
	@-cd backend && uv run python -c "\
from sqlalchemy import create_engine, text; \
from app.core.config import settings; \
try: \
    engine = create_engine(settings.DATABASE_URL); \
    with engine.connect() as conn: \
        genes = conn.execute(text('SELECT COUNT(*) FROM genes')).scalar(); \
        evidence = conn.execute(text('SELECT COUNT(*) FROM gene_evidence')).scalar(); \
        curations = conn.execute(text('SELECT COUNT(*) FROM gene_curations')).scalar(); \
        print(f'  Genes:     {genes:,}'); \
        print(f'  Evidence:  {evidence:,}'); \
        print(f'  Curations: {curations:,}'); \
except Exception as e: \
    print('  Database not accessible');" 2>/dev/null || echo "  Database not accessible"
	@echo ""
	@echo "📡 Data Source Status:"
	@-curl -s http://localhost:8000/api/progress/status 2>/dev/null | python3 -c "import sys, json; data = json.loads(sys.stdin.read()) if sys.stdin.read() else []; [print(f\"  {'✓' if s['status'] == 'completed' else '○' if s['status'] == 'idle' else '⏳'} {s['source_name']}: {s['status']} ({s['progress_percentage']}%)\") for s in data]" 2>/dev/null || echo "  Backend API not accessible"

# ════════════════════════════════════════════════════════════════════
# CLEANUP
# ════════════════════════════════════════════════════════════════════

# Complete cleanup
clean-all:
	@echo "🧹 Performing complete cleanup..."
	@$(MAKE) hybrid-down
	@$(MAKE) dev-down
	@$(MAKE) clean-backend
	@docker volume rm kidney-genetics-db_postgres_data 2>/dev/null || true
	@rm -rf logs/*.log 2>/dev/null || true
	@echo "✅ Cleanup complete!"

# ════════════════════════════════════════════════════════════════════
# CODE QUALITY
# ════════════════════════════════════════════════════════════════════

# Lint backend code
lint:
	@echo "🔍 Linting backend app code with ruff..."
	@cd backend && uv run ruff check app/ --fix
	@echo "✅ Linting complete!"

# Run backend tests
test:
	@echo "🧪 Running backend tests with pytest..."
	@cd backend && uv run pytest -v
	@echo "✅ Tests complete!"

# Clean backend development cache files
clean-backend:
	@echo "🧹 Cleaning backend cache files..."
	@echo "  Removing Python cache directories..."
	@find backend -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find backend -type f -name "*.pyc" -delete 2>/dev/null || true
	@find backend -type f -name "*.pyo" -delete 2>/dev/null || true
	@find backend -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@echo "  Removing .cache directory..."
	@rm -rf backend/.cache 2>/dev/null || true
	@echo "  Removing pytest cache..."
	@rm -rf backend/.pytest_cache 2>/dev/null || true
	@echo "  Removing ruff cache..."
	@rm -rf backend/.ruff_cache 2>/dev/null || true
	@echo "  Removing mypy cache..."
	@rm -rf backend/.mypy_cache 2>/dev/null || true
	@echo "✅ Backend cache cleaned!"

# ════════════════════════════════════════════════════════════════════
# MIGRATION MANAGEMENT
# ════════════════════════════════════════════════════════════════════

.PHONY: db-squash-migrations db-migration-backup db-backup-full db-migration-restore db-restore-full db-verify-views db-verify-tables db-verify-complete db-show-view-deps db-refresh-views

# Create a quick backup of current migrations
db-migration-backup:
	@TIMESTAMP=$$(date +%Y%m%d_%H%M%S); \
	mkdir -p backups/$$TIMESTAMP && \
	cp -r backend/alembic/versions backups/$$TIMESTAMP/migrations && \
	echo "✅ Migrations backed up to: backups/$$TIMESTAMP/migrations"

# Create a comprehensive backup (migrations + schema + history)
db-backup-full:
	@TIMESTAMP=$$(date +%Y%m%d_%H%M%S); \
	echo "🔄 Creating comprehensive backup..." && \
	mkdir -p backups/$$TIMESTAMP && \
	cp -r backend/alembic/versions backups/$$TIMESTAMP/migrations 2>/dev/null && \
	docker exec kidney_genetics_postgres pg_dump -U kidney_user -d kidney_genetics > backups/$$TIMESTAMP/database_full.sql && \
	docker exec kidney_genetics_postgres pg_dump -U kidney_user -d kidney_genetics --schema-only > backups/$$TIMESTAMP/schema.sql && \
	cd backend && uv run alembic history > ../backups/$$TIMESTAMP/migration_history.txt && \
	cd backend && uv run alembic current > ../backups/$$TIMESTAMP/current_revision.txt && \
	echo "✅ Full backup created in: backups/$$TIMESTAMP/" && \
	echo "   Contents:" && \
	echo "   - Migration files: backups/$$TIMESTAMP/migrations/" && \
	echo "   - Full database: backups/$$TIMESTAMP/database_full.sql" && \
	echo "   - Schema only: backups/$$TIMESTAMP/schema.sql" && \
	echo "   - Migration history: backups/$$TIMESTAMP/migration_history.txt" && \
	echo "   - Current revision: backups/$$TIMESTAMP/current_revision.txt"

# Squash all migrations into a single initial migration
db-squash-migrations: db-migration-backup
	@echo "╔════════════════════════════════════════════════════════════════╗"
	@echo "║           MIGRATION SQUASHING - DEVELOPMENT ONLY                ║"
	@echo "╚════════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "⚠️  WARNING: This will:"
	@echo "  • Delete all existing migration history"
	@echo "  • Reset the development database completely"
	@echo "  • Generate a new single migration from models"
	@echo ""
	@echo "This should ONLY be used in development environments!"
	@echo ""
	@read -p "Type 'squash' to confirm: " confirm; \
	if [ "$$confirm" != "squash" ]; then \
		echo "❌ Operation cancelled"; \
		exit 1; \
	fi
	@echo ""
	@echo "📦 Step 1/7: Creating comprehensive backup..."
	@TIMESTAMP=$$(date +%Y%m%d_%H%M%S); \
	mkdir -p backups/$$TIMESTAMP && \
	cp -r backend/alembic/versions backups/$$TIMESTAMP/migrations 2>/dev/null || true && \
	docker exec kidney_genetics_postgres pg_dump -U kidney_user -d kidney_genetics --schema-only > backups/$$TIMESTAMP/schema.sql 2>/dev/null || true && \
	cd backend && uv run alembic history > ../backups/$$TIMESTAMP/migration_history.txt 2>/dev/null || true && \
	echo "   ✓ Full backup created in: backups/$$TIMESTAMP/" && \
	echo "     - Migration files: backups/$$TIMESTAMP/migrations/" && \
	echo "     - Database schema: backups/$$TIMESTAMP/schema.sql" && \
	echo "     - Migration history: backups/$$TIMESTAMP/migration_history.txt"
	@echo ""
	@echo "🔄 Step 2/7: Resetting database..."
	@$(DOCKER_COMPOSE) -f docker-compose.services.yml down -v
	@$(DOCKER_COMPOSE) -f docker-compose.services.yml up -d postgres
	@sleep 5
	@docker exec kidney_genetics_postgres pg_isready -U kidney_user -d kidney_genetics >/dev/null 2>&1 || \
		(echo "   ⚠️  Waiting for database..." && sleep 5)
	@echo "   ✓ Database reset complete"
	@echo ""
	@echo "🧹 Step 3/7: Cleaning migration directory..."
	@rm -rf backend/alembic/versions/*.py
	@echo "   ✓ Migration directory cleaned"
	@echo ""
	@echo "🔨 Step 4/7: Generating new squashed migration..."
	@cd backend && uv run alembic revision --autogenerate \
		-m "squashed_complete_schema_$$(date +%Y%m%d)" 2>&1 | \
		grep -E "(Generating|Detected)" || echo "   ✓ Migration generated"
	@echo ""
	@echo "📝 Step 5/7: Review the generated migration"
	@echo "   Location: backend/alembic/versions/"
	@ls -la backend/alembic/versions/*.py | tail -1
	@echo ""
	@read -p "Press Enter to apply the migration, or Ctrl+C to abort: "
	@echo ""
	@echo "🚀 Step 6/7: Applying migration..."
	@cd backend && uv run alembic upgrade head
	@echo ""
	@echo "✅ Step 7/7: Validating schema..."
	@$(MAKE) db-validate-schema
	@echo ""
	@echo "✅ Migration squashing complete!"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Review the generated migration file"
	@echo "  2. Test with: make test"
	@echo "  3. Verify API: make backend (then check http://localhost:8000/docs)"
	@echo "  4. If issues occur, restore with: make db-restore-full"

# Restore migrations from a backup
db-migration-restore:
	@echo "Available backups:"
	@ls -d backups/*/migrations 2>/dev/null | sed 's|backups/||;s|/migrations||' | sed 's/^/  - /' || echo "  No backups found"
	@echo ""
	@read -p "Enter backup timestamp to restore (e.g., 20250822_143022): " timestamp; \
	if [ -d "backups/$$timestamp/migrations" ]; then \
		rm -rf backend/alembic/versions/*.py && \
		cp -r backups/$$timestamp/migrations/* backend/alembic/versions/ && \
		echo "✅ Restored migrations from backup: $$timestamp"; \
		echo "   Run 'make db-reset' to apply the restored migrations"; \
	else \
		echo "❌ Backup not found: backups/$$timestamp"; \
		exit 1; \
	fi

# Restore complete database from backup
db-restore-full:
	@echo "Available full backups:"
	@ls -f backups/*/database_full.sql 2>/dev/null | sed 's|backups/||;s|/database_full.sql||' | sed 's/^/  - /' || echo "  No full backups found"
	@echo ""
	@read -p "Enter backup timestamp to restore (e.g., 20250822_143022): " timestamp; \
	if [ -f "backups/$$timestamp/database_full.sql" ]; then \
		echo "🔄 Restoring database from backup..."; \
		docker exec -i kidney_genetics_postgres psql -U kidney_user -d postgres -c "DROP DATABASE IF EXISTS kidney_genetics;" && \
		docker exec -i kidney_genetics_postgres psql -U kidney_user -d postgres -c "CREATE DATABASE kidney_genetics;" && \
		docker exec -i kidney_genetics_postgres psql -U kidney_user -d kidney_genetics < backups/$$timestamp/database_full.sql && \
		if [ -d "backups/$$timestamp/migrations" ]; then \
			rm -rf backend/alembic/versions/*.py && \
			cp -r backups/$$timestamp/migrations/* backend/alembic/versions/ && \
			echo "   ✓ Migrations restored"; \
		fi && \
		echo "✅ Full restoration complete from backup: $$timestamp"; \
	else \
		echo "❌ Full backup not found: backups/$$timestamp"; \
		exit 1; \
	fi

# Validate database schema against models
db-validate-schema:
	@echo "🔍 Validating database schema..."
	@cd backend && uv run python -c "from sqlalchemy import create_engine, inspect; from app.core.config import settings; from app.models import Base; engine = create_engine(settings.DATABASE_URL); inspector = inspect(engine); db_tables = set(inspector.get_table_names()); model_tables = set(Base.metadata.tables.keys()); missing = model_tables - db_tables; extra = db_tables - model_tables - {'alembic_version'}; missing and print('Missing tables:', missing); extra and print('Extra tables:', extra); (not missing and not extra) and print('Schema is in sync')"

# Verify all database views are created
db-verify-views:
	@echo "🔍 Verifying database views..."
	@cd backend && uv run python -c "from sqlalchemy import create_engine, inspect; from app.core.config import settings; from app.db.views import ALL_VIEWS; engine = create_engine(settings.DATABASE_URL); inspector = inspect(engine); db_views = set(inspector.get_view_names()); expected_views = {view.name for view in ALL_VIEWS}; missing = expected_views - db_views; extra = db_views - expected_views; missing and print('Missing views:', missing); extra and print('Extra views:', extra); (not missing and not extra) and print('All', len(expected_views), 'views present')"

# Verify all database tables are created
db-verify-tables:
	@echo "🔍 Verifying database tables..."
	@COUNT=$$(docker exec kidney_genetics_postgres psql -U kidney_user -d kidney_genetics -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE';"); \
	if [ "$$COUNT" -eq "13" ]; then \
		echo "✅ All 13 tables present"; \
	else \
		echo "❌ Table count mismatch: found $$COUNT tables, expected 13"; \
		docker exec kidney_genetics_postgres psql -U kidney_user -d kidney_genetics -c "\dt"; \
	fi

# Verify complete database schema (tables + views)
db-verify-complete: db-verify-tables db-verify-views db-validate-schema
	@echo "✅ Complete schema verification done"

# Show detailed view dependencies
db-show-view-deps:
	@echo "📊 View dependency hierarchy:"
	@cd backend && uv run python -c "\
from app.db.views import ALL_VIEWS; \
from app.db.replaceable_objects import topological_sort; \
sorted_views = topological_sort(ALL_VIEWS); \
print('  Tier 1 (no dependencies):'); \
[print(f'    - {v.name}') for v in sorted_views if not v.dependencies]; \
print('  Tier 2:'); \
[print(f'    - {v.name} (depends on: {v.dependencies})') for v in sorted_views if v.dependencies and not any(dep in v.dependencies for v2 in sorted_views for dep in v2.dependencies if v2.name in v.dependencies)]; \
"

# Refresh all database views
db-refresh-views:
	@echo "🔄 Refreshing all database views..."
	@cd backend && uv run python -c "from sqlalchemy import create_engine, text; from app.core.config import settings; from app.db.views import ALL_VIEWS; from app.db.replaceable_objects import topological_sort; engine = create_engine(settings.DATABASE_URL); sorted_views = topological_sort(ALL_VIEWS); conn = engine.connect(); trans = conn.begin(); [conn.execute(text(view.drop_statement())) for view in reversed(sorted_views)]; [conn.execute(text(view.create_statement())) for view in sorted_views]; trans.commit(); conn.close(); print('✅ All views refreshed successfully')"

# Create log directory if it doesn't exist
$(shell mkdir -p logs)