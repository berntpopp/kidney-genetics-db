# Kidney Genetics Database - Development Makefile
# Usage: make [command]

.PHONY: help clean-db reset-db restart-backend restart-frontend restart-all stop-all test-pubtator status clean-cache

# Default target - show help
help:
	@echo "Available commands:"
	@echo "  make clean-db        - Remove all data from database tables"
	@echo "  make reset-db        - Clean database and reset progress tracking"
	@echo "  make restart-backend - Stop and restart the backend server"
	@echo "  make restart-frontend- Stop and restart the frontend dev server"
	@echo "  make restart-all     - Restart both backend and frontend"
	@echo "  make stop-all        - Stop all running services"
	@echo "  make test-pubtator   - Run PubTator with test configuration (20 pages)"
	@echo "  make status          - Show status of all services and data sources"
	@echo "  make clean-cache     - Clear all caches (PubTator, HGNC)"
	@echo "  make fresh-start     - Complete fresh start (clean DB + restart all)"

# Clean all data from database
clean-db:
	@echo "Cleaning database..."
	@cd backend && uv run python -c "\
from sqlalchemy import create_engine, text; \
from app.core.config import settings; \
engine = create_engine(settings.DATABASE_URL); \
with engine.connect() as conn: \
    tables = ['gene_evidence', 'gene_curations', 'genes', 'data_source_progress']; \
    for table in tables: \
        try: \
            result = conn.execute(text(f'DELETE FROM {table}')); \
            print(f'  Deleted {result.rowcount} rows from {table}'); \
        except Exception as e: \
            print(f'  Error cleaning {table}: {e}'); \
    conn.commit(); \
    print('Database cleaned successfully!');"

# Reset database and progress tracking
reset-db: clean-db
	@echo "Resetting progress tracking..."
	@cd backend && uv run python -c "\
from sqlalchemy import create_engine, text; \
from app.core.config import settings; \
from datetime import datetime, timezone; \
engine = create_engine(settings.DATABASE_URL); \
with engine.connect() as conn: \
    sources = ['PubTator', 'PanelApp', 'HPO', 'ClinGen', 'GenCC', 'OMIM', 'Literature', 'Evidence_Aggregation', 'HGNC_Normalization']; \
    for source in sources: \
        conn.execute(text(''' \
            INSERT INTO data_source_progress (source_name, status, progress_percentage, current_operation, created_at, updated_at) \
            VALUES (:source, 'idle', 0, 'Ready to start', :now, :now) \
            ON CONFLICT (source_name) \
            DO UPDATE SET status = 'idle', progress_percentage = 0, current_operation = 'Ready to start', updated_at = :now \
        '''), {'source': source, 'now': datetime.now(timezone.utc)}); \
    conn.commit(); \
    print('Progress tracking reset successfully!');"

# Stop backend server
stop-backend:
	@echo "Stopping backend server..."
	@pkill -f "uvicorn app.main:app" || true
	@sleep 1

# Stop frontend server
stop-frontend:
	@echo "Stopping frontend server..."
	@pkill -f "vite.*5173" || true
	@sleep 1

# Stop all services
stop-all: stop-backend stop-frontend
	@echo "All services stopped"

# Start backend server
start-backend:
	@echo "Starting backend server..."
	@cd backend && nohup uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 > ../logs/backend.log 2>&1 &
	@sleep 3
	@echo "Backend server started on http://localhost:8000"

# Start frontend server
start-frontend:
	@echo "Starting frontend server..."
	@cd frontend && nohup npm run dev > ../logs/frontend.log 2>&1 &
	@sleep 3
	@echo "Frontend server started on http://localhost:5173"

# Restart backend
restart-backend: stop-backend start-backend
	@echo "Backend restarted successfully"

# Restart frontend
restart-frontend: stop-frontend start-frontend
	@echo "Frontend restarted successfully"

# Restart all services
restart-all: stop-all
	@$(MAKE) start-backend
	@$(MAKE) start-frontend
	@echo "All services restarted successfully"

# Complete fresh start
fresh-start: stop-all reset-db clean-cache
	@echo "Starting fresh environment..."
	@$(MAKE) start-backend
	@$(MAKE) start-frontend
	@echo "Fresh environment ready!"
	@echo "  Backend: http://localhost:8000/docs"
	@echo "  Frontend: http://localhost:5173"

# Test PubTator with limited pages
test-pubtator:
	@echo "Triggering PubTator test run (20 pages)..."
	@curl -X POST "http://localhost:8000/api/progress/trigger/PubTator" \
		-H "Content-Type: application/json" \
		-s | python3 -m json.tool || echo "Failed to trigger PubTator"

# Show status of all data sources
status:
	@echo "Data Source Status:"
	@echo "==================="
	@curl -s http://localhost:8000/api/progress/status | python3 scripts/show_status.py || echo "Backend not responding"
	@echo ""
	@echo "Database Statistics:"
	@echo "==================="
	@cd backend && uv run python -c "\
from sqlalchemy import create_engine, text; \
from app.core.config import settings; \
engine = create_engine(settings.DATABASE_URL); \
with engine.connect() as conn: \
    genes = conn.execute(text('SELECT COUNT(*) FROM genes')).scalar(); \
    evidence = conn.execute(text('SELECT COUNT(*) FROM gene_evidence')).scalar(); \
    curations = conn.execute(text('SELECT COUNT(*) FROM gene_curations')).scalar(); \
    print(f'  Genes: {genes}'); \
    print(f'  Evidence Records: {evidence}'); \
    print(f'  Curations: {curations}');" \
	|| echo "Could not fetch database statistics"

# Clear all caches
clean-cache:
	@echo "Clearing caches..."
	@rm -rf backend/.cache/pubtator/* 2>/dev/null || true
	@rm -rf backend/.cache/hgnc/* 2>/dev/null || true
	@echo "Caches cleared"

# Create log directory if it doesn't exist
$(shell mkdir -p logs)

# Watch logs
logs-backend:
	@tail -f logs/backend.log

logs-frontend:
	@tail -f logs/frontend.log

logs:
	@tail -f logs/*.log