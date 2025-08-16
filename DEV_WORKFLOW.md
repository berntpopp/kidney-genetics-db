# Development Workflow Guide

## Quick Start

### Hybrid Development (Recommended)
```bash
# Start database in Docker, run API/Frontend locally
make hybrid-up

# Then in separate terminals:
cd backend && uv run uvicorn app.main:app --reload
cd frontend && npm run dev
```

### Full Docker Development
```bash
# Start all services in Docker
make dev-up

# View logs
make dev-logs
```

## Available Make Commands

### 🚀 Development Modes
- `make hybrid-up` - Start DB in Docker + instructions for local development
- `make hybrid-down` - Stop all hybrid mode services
- `make dev-up` - Start all services in Docker containers
- `make dev-down` - Stop all Docker services
- `make dev-logs` - Show Docker logs (follow mode)

### 🔧 Service Management
- `make services-up` - Start only database in Docker
- `make services-down` - Stop Docker services

### 🗄️ Database Management
- `make db-reset` - Complete database reset (drops & recreates with migrations)
- `make db-clean` - Remove all data but keep structure

### 📊 Monitoring
- `make status` - Show comprehensive system status:
  - Docker services status
  - Local processes (backend/frontend)
  - Database statistics
  - Data source progress

### 🧹 Cleanup
- `make clean-all` - Stop everything and clean all data

## Development Workflows

### Starting Fresh Development
```bash
# Complete reset and start
make db-reset
make hybrid-up

# Run in separate terminals
cd backend && uv run uvicorn app.main:app --reload
cd frontend && npm run dev
```

### Checking System Status
```bash
# See what's running and database state
make status
```

### Switching Between Modes

#### From Hybrid to Docker:
```bash
make hybrid-down
make dev-up
```

#### From Docker to Hybrid:
```bash
make dev-down
make hybrid-up
# Then start local services
```

## Data Source Management

### Trigger Data Sources
```bash
# Through the API (when backend is running)
curl -X POST http://localhost:8000/api/progress/trigger/PanelApp
curl -X POST http://localhost:8000/api/progress/trigger/PubTator
```

### Monitor Progress
- Visit http://localhost:5173 for real-time progress in UI
- Use `make status` for command-line view

## Configuration

### Environment Variables
Create `.env` file in backend directory:
```env
DATABASE_URL=postgresql://kidney_user:kidney_pass@localhost:5432/kidney_genetics
SECRET_KEY=your-secret-key
ENVIRONMENT=development
```

### PubTator Settings
Edit `backend/app/core/config.py`:
```python
PUBTATOR_MAX_PAGES: int = 20  # Pages to fetch per run
PUBTATOR_MIN_PUBLICATIONS: int = 3  # Min publications for gene
PUBTATOR_BATCH_SIZE: int = 100  # PMIDs per batch
```

## Access Points

- **Frontend**: http://localhost:5173 (hybrid) or http://localhost:3000 (docker)
- **Backend API**: http://localhost:8000/docs
- **Database**: PostgreSQL on localhost:5432
  - User: kidney_user
  - Password: kidney_pass
  - Database: kidney_genetics

## Troubleshooting

### Port Already in Use
```bash
# Find and kill process using port
lsof -i :8000  # or :5173, :5432
kill -9 <PID>

# Or use make commands
make hybrid-down
make dev-down
```

### Database Connection Issues
```bash
# Check if database is running
docker ps | grep kidney_genetics_postgres

# Reset database
make db-reset
```

### Backend Won't Start
```bash
# Check dependencies
cd backend
uv pip install -e .

# Check database is accessible
docker exec kidney_genetics_postgres pg_isready
```

### Frontend Issues
```bash
# Reinstall dependencies
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run dev
```

## Testing

### Backend Tests
```bash
cd backend
uv run pytest
```

### Frontend Tests
```bash
cd frontend
npm run test
```

### Linting
```bash
# Backend
cd backend && uv run ruff check . --fix

# Frontend
cd frontend && npm run lint && npm run format
```

## Docker Management

### View Container Logs
```bash
# All services
make dev-logs

# Specific service
docker logs kidney_genetics_postgres -f
docker logs kidney_genetics_api -f
```

### Shell Access
```bash
# Database shell
docker exec -it kidney_genetics_postgres psql -U kidney_user -d kidney_genetics

# Backend shell (if using Docker)
docker exec -it kidney_genetics_api bash
```

### Clean Docker Resources
```bash
# Complete cleanup
make clean-all

# Manual cleanup
docker-compose down -v  # Remove volumes too
docker system prune -a  # Clean all unused resources
```

## Notes

- Hybrid mode is recommended for active development (faster hot-reload)
- Docker mode is useful for testing production-like environment
- Database persists data in Docker volume
- Backend uses `uv` for Python package management
- Frontend uses Vite for fast HMR (Hot Module Replacement)