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
	@echo "  make db-reset        - Complete database reset (structure + data)"
	@echo "  make db-clean        - Remove all data (keep structure)"
	@echo ""
	@echo "📊 MONITORING:"
	@echo "  make status          - Show system status and statistics"
	@echo ""
	@echo "🔍 CODE QUALITY:"
	@echo "  make lint            - Lint backend code with ruff"
	@echo "  make test            - Run backend tests with pytest"
	@echo ""
	@echo "🧹 CLEANUP:"
	@echo "  make clean-all       - Stop everything and clean data"

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
	@cd backend && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run frontend locally
frontend:
	@echo "Starting frontend..."
	@cd frontend && npm run dev

# ════════════════════════════════════════════════════════════════════
# DATABASE MANAGEMENT
# ════════════════════════════════════════════════════════════════════

# Complete database reset (drop and recreate)
db-reset: services-up
	@echo "🔄 Resetting database completely..."
	@docker exec kidney_genetics_postgres psql -U kidney_user -d postgres -c "DROP DATABASE IF EXISTS kidney_genetics;" 2>/dev/null || true
	@docker exec kidney_genetics_postgres psql -U kidney_user -d postgres -c "CREATE DATABASE kidney_genetics;"
	@echo "📦 Running migrations..."
	@cd backend && uv run alembic upgrade head
	@echo "🎯 Initializing progress tracking..."
	@cd backend && uv run python -c "from sqlalchemy import create_engine, text; from app.core.config import settings; from datetime import datetime, timezone; engine = create_engine(settings.DATABASE_URL); conn = engine.connect(); sources = ['PubTator', 'PanelApp', 'HPO', 'ClinGen', 'GenCC', 'Literature', 'Evidence_Aggregation', 'HGNC_Normalization']; [conn.execute(text('INSERT INTO data_source_progress (source_name, status, progress_percentage, current_operation, created_at, updated_at) VALUES (:source, \\'idle\\', 0, \\'Ready to start\\', :now, :now) ON CONFLICT (source_name) DO UPDATE SET status = \\'idle\\', progress_percentage = 0, current_operation = \\'Ready to start\\', updated_at = :now'), {'source': source, 'now': datetime.now(timezone.utc)}) for source in sources]; conn.commit(); conn.close(); print('Progress tracking initialized')"
	@echo "✅ Database reset complete!"

# Clean all data from database (keep structure)
db-clean:
	@echo "🧹 Cleaning database data..."
	@cd backend && uv run python -c "\
from sqlalchemy import create_engine, text; \
from app.core.config import settings; \
engine = create_engine(settings.DATABASE_URL); \
with engine.connect() as conn: \
    tables = ['gene_evidence', 'gene_curations', 'genes', 'data_source_progress']; \
    for table in tables: \
        try: \
            result = conn.execute(text(f'DELETE FROM {table}')); \
            conn.commit(); \
            print(f'  ✓ Cleaned {result.rowcount} rows from {table}'); \
        except Exception as e: \
            print(f'  ✗ Error cleaning {table}: {e}');"
	@echo "✅ Database cleaned!"

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
	@docker volume rm kidney-genetics-db_postgres_data 2>/dev/null || true
	@rm -rf backend/.cache 2>/dev/null || true
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

# Create log directory if it doesn't exist
$(shell mkdir -p logs)