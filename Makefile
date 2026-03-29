# Kidney Genetics Database - Development Makefile
# Usage: make [command]

.PHONY: help dev-up dev-down dev-logs hybrid-up hybrid-down services-up services-down db-reset db-clean status clean-all backend frontend worker lint lint-frontend format-check test test-unit test-integration test-e2e test-critical test-coverage test-watch test-failed test-frontend prod-build prod-up prod-down prod-logs prod-restart prod-health prod-test-up prod-test-down prod-test-logs prod-test-health npm-network-create npm-network-check security bandit pip-audit npm-audit ci benchmark-pipeline benchmark-pipeline-fresh

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
	@echo "  make worker          - Run ARQ background worker"
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
	@echo "  make lint-frontend   - Lint frontend code with eslint"
	@echo "  make format-check    - Check formatting (backend + frontend)"
	@echo ""
	@echo "🔒 SECURITY:"
	@echo "  make security        - Run all security scans"
	@echo "  make bandit          - Run Python SAST with Bandit"
	@echo "  make pip-audit       - Scan Python dependencies"
	@echo "  make npm-audit       - Scan JavaScript dependencies"
	@echo ""
	@echo "🧪 TESTING:"
	@echo "  make test            - Run all backend tests"
	@echo "  make test-unit       - Run unit tests only (fast)"
	@echo "  make test-integration- Run integration tests"
	@echo "  make test-e2e        - Run end-to-end tests"
	@echo "  make test-critical   - Run critical tests only"
	@echo "  make test-coverage   - Run tests with coverage report"
	@echo "  make test-failed     - Re-run only failed tests"
	@echo ""
	@echo "📊 BENCHMARKING:"
	@echo "  make benchmark-pipeline       - Benchmark pipeline (uses existing cache)"
	@echo "  make benchmark-pipeline-fresh  - Benchmark pipeline (clears cache first)"
	@echo ""
	@echo "🧹 CLEANUP:"
	@echo "  make clean-backend   - Clean Python cache files (__pycache__, .pyc, etc.)"
	@echo "  make clean-all       - Stop everything and clean all data"
	@echo ""
	@echo "🚢 PRODUCTION DEPLOYMENT:"
	@echo "  make prod-build      - Build production images"
	@echo "  make prod-test-up    - Start test mode (ports: 8080/8001/5433)"
	@echo "  make prod-test-health- Test mode health check"
	@echo "  make prod-test-down  - Stop test mode"
	@echo "  make prod-up         - Start production (NPM mode, no ports)"
	@echo "  make prod-health     - Production health check"
	@echo "  make prod-down       - Stop production"
	@echo "  make npm-network-create - Create shared npm_proxy_network"

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
	@-pkill -f "arq app.core.arq_worker" 2>/dev/null || true
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
	@echo "⏳ Waiting for services to be ready..."
	@sleep 3
	@docker exec kidney_genetics_postgres pg_isready -U kidney_user -d kidney_genetics >/dev/null 2>&1 && \
		echo "✅ PostgreSQL is ready" || echo "⚠️  PostgreSQL is starting..."
	@docker exec kidney_genetics_redis redis-cli ping >/dev/null 2>&1 && \
		echo "✅ Redis is ready" || echo "⚠️  Redis is starting..."
	@echo ""
	@echo "📍 Services:"
	@echo "   PostgreSQL: localhost:5432"
	@echo "   Redis:      localhost:6379"

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

# Run ARQ background worker
worker:
	@echo "Starting ARQ background worker..."
	@echo "⚠️  Requires Redis to be running (make services-up)"
	@cd backend && uv run arq app.core.arq_worker.WorkerSettings

# Run ARQ worker with verbose logging
worker-debug:
	@echo "Starting ARQ background worker (debug mode)..."
	@cd backend && uv run arq app.core.arq_worker.WorkerSettings --verbose

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
# BENCHMARKING
# ════════════════════════════════════════════════════════════════════

# Run pipeline benchmark (uses existing bulk cache)
benchmark-pipeline:
	@echo "📊 Running pipeline resource benchmark..."
	@echo "⚠️  Requires running backend (make backend) and admin credentials in backend/.env"
	@cd backend && uv run python scripts/benchmark_pipeline.py
	@echo "✅ Benchmark complete! Report: backend/benchmark_report.json"

# Run pipeline benchmark after clearing bulk cache (simulates first run)
benchmark-pipeline-fresh:
	@echo "📊 Running pipeline resource benchmark (fresh, no cache)..."
	@echo "⚠️  Requires running backend (make backend) and admin credentials in backend/.env"
	@cd backend && uv run python scripts/benchmark_pipeline.py --clear-cache
	@echo "✅ Benchmark complete! Report: backend/benchmark_report.json"

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

# Lint frontend code
lint-frontend:
	@echo "🔍 Linting frontend code with eslint..."
	@cd frontend && npm run lint:check
	@echo "✅ Frontend linting complete!"

# Check formatting (no auto-fix)
format-check:
	@echo "🔍 Checking formatting..."
	@cd backend && uv run ruff format --check app/
	@cd frontend && npm run format:check
	@echo "✅ Format check complete!"

# ════════════════════════════════════════════════════════════════════
# SECURITY SCANNING
# ════════════════════════════════════════════════════════════════════

.PHONY: security bandit pip-audit npm-audit

# Run all security scans
security: bandit pip-audit npm-audit
	@echo "✅ All security scans complete!"

# Run Bandit security scan (Python SAST)
bandit:
	@echo "🔒 Running Bandit security scan..."
	@cd backend && uv run bandit -r app/ -c pyproject.toml
	@echo "✅ Bandit scan complete!"

# Run pip-audit (Python dependency scan)
pip-audit:
	@echo "🔒 Running pip-audit dependency scan..."
	@cd backend && uv run pip-audit || true
	@echo "✅ pip-audit scan complete!"

# Run npm audit (JavaScript dependency scan)
npm-audit:
	@echo "🔒 Running npm audit dependency scan..."
	@cd frontend && npm audit --omit=dev || true
	@echo "✅ npm audit scan complete!"

# ════════════════════════════════════════════════════════════════════
# CI/CD LOCAL VERIFICATION
# ════════════════════════════════════════════════════════════════════

# Run all CI checks locally (matches GitHub Actions exactly)
ci: ci-backend ci-frontend
	@echo ""
	@echo "╔════════════════════════════════════════════════════════════════╗"
	@echo "║                    ✅ ALL CI CHECKS PASSED                      ║"
	@echo "╚════════════════════════════════════════════════════════════════╝"

# Run backend CI checks (matches GitHub Actions backend-ci job)
ci-backend:
	@echo "╔════════════════════════════════════════════════════════════════╗"
	@echo "║                    BACKEND CI CHECKS                           ║"
	@echo "╚════════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "🔍 Step 1/3: Linting with ruff..."
	@cd backend && uv run ruff check app/
	@echo "✅ Lint passed"
	@echo ""
	@echo "🔍 Step 2/3: Format check with ruff..."
	@cd backend && uv run ruff format --check app/
	@echo "✅ Format check passed"
	@echo ""
	@echo "🧪 Step 3/3: Running tests with pytest..."
	@cd backend && uv run pytest tests/ -v
	@echo "✅ Tests passed"
	@echo ""
	@echo "✅ Backend CI complete!"

# Run frontend CI checks (matches GitHub Actions frontend-ci job)
ci-frontend:
	@echo "╔════════════════════════════════════════════════════════════════╗"
	@echo "║                    FRONTEND CI CHECKS                          ║"
	@echo "╚════════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "🔍 Step 1/4: Linting with eslint..."
	@cd frontend && npm run lint:check
	@echo "✅ ESLint passed"
	@echo ""
	@echo "🔍 Step 2/4: Format check with prettier..."
	@cd frontend && npm run format:check
	@echo "✅ Prettier check passed"
	@echo ""
	@echo "🔨 Step 3/4: Building frontend..."
	@cd frontend && npm run build
	@echo "✅ Build passed"
	@echo ""
	@echo "🧪 Step 4/4: Running frontend tests (vitest)..."
	@cd frontend && npm run test:run
	@echo "✅ Vitest passed"
	@echo ""
	@echo "✅ Frontend CI complete!"

# Run frontend tests (Vitest)
test-frontend:
	@echo "🧪 Running frontend component tests (vitest)..."
	@cd frontend && npm run test:run
	@echo "✅ Frontend tests complete!"

# ════════════════════════════════════════════════════════════════════
# TESTING
# ════════════════════════════════════════════════════════════════════

# Run backend tests
test:
	@echo "🧪 Running backend tests with pytest..."
	@cd backend && uv run pytest -v
	@echo "✅ Tests complete!"

# Run unit tests only (fast)
test-unit:
	@echo "🧪 Running unit tests only..."
	@cd backend && uv run pytest tests/core -v -m "unit or not integration"
	@echo "✅ Unit tests complete!"

# Run integration tests
test-integration:
	@echo "🧪 Running integration tests..."
	@cd backend && uv run pytest tests/api tests/pipeline -v -m "integration"
	@echo "✅ Integration tests complete!"

# Run end-to-end tests
test-e2e:
	@echo "🧪 Running E2E tests..."
	@cd backend && uv run pytest tests/e2e -v -m "e2e" --tb=long
	@echo "✅ E2E tests complete!"

# Run critical tests (fast smoke test)
test-critical:
	@echo "🧪 Running critical tests..."
	@cd backend && uv run pytest -v -m "critical"
	@echo "✅ Critical tests complete!"

# Run tests with coverage report
test-coverage:
	@echo "🧪 Running tests with coverage..."
	@cd backend && uv run pytest --cov=app --cov-report=html --cov-report=term-missing --cov-report=xml
	@echo "✅ Coverage report generated in backend/htmlcov/"
	@echo "📊 Open backend/htmlcov/index.html to view coverage"

# Run tests in watch mode (requires pytest-watch)
test-watch:
	@echo "🧪 Running tests in watch mode..."
	@cd backend && uv run ptw -- -vv

# Run only failed tests from last run
test-failed:
	@echo "🧪 Running only failed tests..."
	@cd backend && uv run pytest --lf -v
	@echo "✅ Failed tests re-run complete!"

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

# Seed initial data from backend/app/data/seed/ (DiagnosticPanels + Literature)
db-seed-initial:
	@echo "Seeding initial data from seed files..."
	@cd backend && uv run python -c "\
		from app.core.database import SessionLocal; \
		from app.core.initial_seeder import needs_initial_seeding, run_initial_seeding; \
		import asyncio; \
		db = SessionLocal(); \
		print('Needs seeding:', needs_initial_seeding(db)); \
		results = asyncio.run(run_initial_seeding(db)); \
		print('Results:', results); \
		db.close()"
	@echo "Initial seeding complete!"

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
# ════════════════════════════════════════════════════════════════════
# VERSION MANAGEMENT
# ════════════════════════════════════════════════════════════════════

.PHONY: version version-check bump-backend-minor bump-backend-patch bump-frontend-minor bump-frontend-patch bump-all-minor bump-all-patch

# Show all component versions
version:
	@echo "╔════════════════════════════════════════════════════════════════╗"
	@echo "║                    COMPONENT VERSIONS                           ║"
	@echo "╚════════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "📦 Backend API:"
	@cd backend && uv run python -c "import tomllib; data = tomllib.load(open('pyproject.toml', 'rb')); print(f'   Version: {data[\"project\"][\"version\"]}')"
	@echo ""
	@echo "🖥️  Frontend:"
	@cd frontend && node -p "'   Version: ' + require('./package.json').version"
	@echo ""
	@echo "🗄️  Database Schema:"
	@cd backend && uv run python -c "\
from sqlalchemy import create_engine, text; \
from app.core.config import settings; \
try: \
    engine = create_engine(settings.DATABASE_URL); \
    conn = engine.connect(); \
    result = conn.execute(text('SELECT version, applied_at FROM schema_versions ORDER BY applied_at DESC LIMIT 1')).fetchone(); \
    if result: \
        print(f'   Version: {result.version}'); \
        print(f'   Applied: {result.applied_at}'); \
    else: \
        print('   Not initialized'); \
    conn.close(); \
except Exception as e: \
    print(f'   Error: {e}');" 2>/dev/null || echo "   Database not accessible"

# Check version via API (requires running backend)
version-check:
	@echo "🔍 Fetching versions from API..."
	@curl -s http://localhost:8000/version 2>/dev/null | python3 -m json.tool || echo "❌ Backend not running on http://localhost:8000"

# Bump backend minor version (0.1.0 -> 0.2.0)
bump-backend-minor:
	@cd backend && uv run python -c "import tomllib; f = open('pyproject.toml', 'rb'); data = tomllib.load(f); f.close(); parts = data['project']['version'].split('.'); new_version = f'{parts[0]}.{int(parts[1])+1}.0'; f = open('pyproject.toml', 'r'); content = f.read(); f.close(); content = content.replace(f'version = \"{data[\"project\"][\"version\"]}\"', f'version = \"{new_version}\"'); f = open('pyproject.toml', 'w'); f.write(content); f.close(); print(f'✅ Backend bumped: {data[\"project\"][\"version\"]} → {new_version}')"

# Bump backend patch version (0.1.0 -> 0.1.1)
bump-backend-patch:
	@cd backend && uv run python -c "import tomllib; f = open('pyproject.toml', 'rb'); data = tomllib.load(f); f.close(); parts = data['project']['version'].split('.'); new_version = f'{parts[0]}.{parts[1]}.{int(parts[2])+1}'; f = open('pyproject.toml', 'r'); content = f.read(); f.close(); content = content.replace(f'version = \"{data[\"project\"][\"version\"]}\"', f'version = \"{new_version}\"'); f = open('pyproject.toml', 'w'); f.write(content); f.close(); print(f'✅ Backend bumped: {data[\"project\"][\"version\"]} → {new_version}')"

# Bump frontend minor version (0.1.0 -> 0.2.0)
bump-frontend-minor:
	@cd frontend && npm version minor --no-git-tag-version && echo "✅ Frontend bumped to $$(node -p 'require(\"./package.json\").version')"

# Bump frontend patch version (0.1.0 -> 0.1.1)
bump-frontend-patch:
	@cd frontend && npm version patch --no-git-tag-version && echo "✅ Frontend bumped to $$(node -p 'require(\"./package.json\").version')"

# Bump all components (minor version)
bump-all-minor:
	@$(MAKE) bump-backend-minor
	@$(MAKE) bump-frontend-minor
	@echo ""
	@echo "✅ All components bumped to minor versions"
	@echo ""
	@$(MAKE) version

# Bump all components (patch version)
bump-all-patch:
	@$(MAKE) bump-backend-patch
	@$(MAKE) bump-frontend-patch
	@echo ""
	@echo "✅ All components bumped to patch versions"
	@echo ""
	@$(MAKE) version

# ════════════════════════════════════════════════════════════════════
# RELEASE MANAGEMENT
# ════════════════════════════════════════════════════════════════════

.PHONY: release-patch release-minor release-major release-tag release-verify

# Helper: get current version from pyproject.toml
define get_version
$(shell cd backend && uv run python -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])")
endef

# Helper: bump version in all 4 files (pyproject.toml, package.json, config.py, CITATION.cff)
# Usage: $(call sync_version,NEW_VERSION)
define sync_version_cmd
	@echo "📦 Syncing version to $(1) across all files..."
	@cd backend && uv run python -c "\
import re; \
f = open('pyproject.toml', 'r'); content = f.read(); f.close(); \
old = re.search(r'version = \"([^\"]+)\"', content).group(1); \
content = content.replace(f'version = \"{old}\"', f'version = \"$(1)\"', 1); \
f = open('pyproject.toml', 'w'); f.write(content); f.close(); \
print(f'   pyproject.toml: {old} → $(1)')"
	@cd frontend && npm version $(1) --no-git-tag-version --allow-same-version > /dev/null && echo "   package.json: → $(1)"
	@cd backend && sed -i 's/APP_VERSION: str = ".*"/APP_VERSION: str = "$(1)"/' app/core/config.py && echo "   config.py: → $(1)"
	@sed -i 's/^version: .*/version: $(1)/' CITATION.cff && echo "   CITATION.cff: → $(1)"
endef

# Verify all 4 version files are in sync
release-verify: ## Verify all version files are in sync
	@echo "🔍 Checking version sync..."
	@BACKEND=$$(cd backend && uv run python -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])") && \
	FRONTEND=$$(cd frontend && node -p "require('./package.json').version") && \
	CONFIG=$$(grep 'APP_VERSION' backend/app/core/config.py | grep -oP '"[^"]+"' | tr -d '"') && \
	CFF=$$(grep '^version:' CITATION.cff | awk '{print $$2}') && \
	echo "   pyproject.toml: $$BACKEND" && \
	echo "   package.json:   $$FRONTEND" && \
	echo "   config.py:      $$CONFIG" && \
	echo "   CITATION.cff:   $$CFF" && \
	if [ "$$BACKEND" = "$$FRONTEND" ] && [ "$$BACKEND" = "$$CONFIG" ] && [ "$$BACKEND" = "$$CFF" ]; then \
		echo "" && echo "✅ All versions in sync: $$BACKEND"; \
	else \
		echo "" && echo "❌ Version mismatch! Run 'make release-patch' or fix manually." && exit 1; \
	fi

# Bump patch (0.2.0 → 0.2.1), commit, and tag
release-patch: ## Bump patch version, commit, tag (then: git push && git push --tags)
	$(eval CURRENT := $(call get_version))
	$(eval NEW := $(shell echo $(CURRENT) | awk -F. '{print $$1"."$$2"."$$3+1}'))
	@echo "🚀 Release: $(CURRENT) → $(NEW)"
	$(call sync_version_cmd,$(NEW))
	@echo ""
	@git add backend/pyproject.toml frontend/package.json frontend/package-lock.json backend/app/core/config.py CITATION.cff
	@git commit -m "chore: bump version to $(NEW)"
	@git tag -a "v$(NEW)" -m "Release v$(NEW)"
	@echo ""
	@echo "✅ Tagged v$(NEW). Now run:"
	@echo "   git push && git push --tags"

# Bump minor (0.2.0 → 0.3.0), commit, and tag
release-minor: ## Bump minor version, commit, tag (then: git push && git push --tags)
	$(eval CURRENT := $(call get_version))
	$(eval NEW := $(shell echo $(CURRENT) | awk -F. '{print $$1"."$$2+1".0"}'))
	@echo "🚀 Release: $(CURRENT) → $(NEW)"
	$(call sync_version_cmd,$(NEW))
	@echo ""
	@git add backend/pyproject.toml frontend/package.json frontend/package-lock.json backend/app/core/config.py CITATION.cff
	@git commit -m "chore: bump version to $(NEW)"
	@git tag -a "v$(NEW)" -m "Release v$(NEW)"
	@echo ""
	@echo "✅ Tagged v$(NEW). Now run:"
	@echo "   git push && git push --tags"

# Bump major (0.2.0 → 1.0.0), commit, and tag
release-major: ## Bump major version, commit, tag (then: git push && git push --tags)
	$(eval CURRENT := $(call get_version))
	$(eval NEW := $(shell echo $(CURRENT) | awk -F. '{print $$1+1".0.0"}'))
	@echo "🚀 Release: $(CURRENT) → $(NEW)"
	$(call sync_version_cmd,$(NEW))
	@echo ""
	@git add backend/pyproject.toml frontend/package.json frontend/package-lock.json backend/app/core/config.py CITATION.cff
	@git commit -m "chore: bump version to $(NEW)"
	@git tag -a "v$(NEW)" -m "Release v$(NEW)"
	@echo ""
	@echo "✅ Tagged v$(NEW). Now run:"
	@echo "   git push && git push --tags"

# Tag current version without bumping (for initial release)
release-tag: ## Tag current version without bumping (then: git push && git push --tags)
	$(eval CURRENT := $(call get_version))
	@$(MAKE) release-verify
	@echo ""
	@git tag -a "v$(CURRENT)" -m "Release v$(CURRENT)"
	@echo "✅ Tagged v$(CURRENT). Now run:"
	@echo "   git push && git push --tags"

# ════════════════════════════════════════════════════════════════════
# PRODUCTION DEPLOYMENT
# ════════════════════════════════════════════════════════════════════

.PHONY: prod-build prod-up prod-down prod-logs prod-restart prod-health
.PHONY: prod-test-up prod-test-down prod-test-logs prod-test-health
.PHONY: npm-network-create npm-network-check

# Production mode (NPM-integrated, no ports exposed)
prod-build:
	@echo "🔨 Building production images..."
	docker-compose -f docker-compose.prod.yml build --no-cache

prod-up:
	@echo "🚀 Starting production deployment (NPM mode)..."
	@echo "⚠️  Requires 'npm_proxy_network' network to exist!"
	@$(MAKE) npm-network-check
	docker-compose -f docker-compose.prod.yml up -d

prod-down:
	@echo "🛑 Stopping production deployment..."
	docker-compose -f docker-compose.prod.yml down

prod-logs:
	docker-compose -f docker-compose.prod.yml logs -f --tail=100

prod-restart:
	docker-compose -f docker-compose.prod.yml restart

prod-health:
	@echo "=== Production Health Check ==="
	@docker ps --filter "name=kidney_genetics" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" || echo "No containers running"

# Test mode (standalone with exposed ports)
prod-test-up:
	@echo "🧪 Starting production TEST mode (ports exposed)..."
	@echo "Access:"
	@echo "  - Frontend: http://localhost:8080"
	@echo "  - Backend API: http://localhost:8001/api/health"
	@echo "  - Database: localhost:5433"
	docker-compose -f docker-compose.prod.test.yml up -d

prod-test-down:
	@echo "🛑 Stopping test mode..."
	docker-compose -f docker-compose.prod.test.yml down

prod-test-logs:
	docker-compose -f docker-compose.prod.test.yml logs -f --tail=100

prod-test-health:
	@echo "=== Test Mode Health Check ==="
	@echo "Frontend: http://localhost:8080"
	@echo -n "Backend API: "
	@curl -sf http://localhost:8001/api/health >/dev/null && echo "✅ Healthy" || echo "❌ Unhealthy"
	@echo ""
	@docker ps --filter "name=kidney_genetics" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Network management
npm-network-create:
	@echo "🌐 Creating shared npm_proxy_network..."
	@docker network create npm_proxy_network 2>/dev/null || echo "✅ Network already exists"

npm-network-check:
	@docker network inspect npm_proxy_network >/dev/null 2>&1 || \
	(echo "❌ npm_proxy_network missing! Run: make npm-network-create" && exit 1)
	@echo "✅ npm_proxy_network exists"
