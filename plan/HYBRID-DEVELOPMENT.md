# Hybrid Development Modes

## Overview

Flexible development setup allowing different combinations of Docker and local development for optimal developer experience. Inspired by laborberlin/agde-api's approach.

## Development Modes

### 1. Full Docker Mode
All services run in Docker containers with hot reloading.

```bash
# Start everything in Docker
docker-compose -f docker-compose.dev.yml up -d

# Access services
# Frontend: http://localhost:3000
# Backend: http://localhost:8000
# Database: localhost:5432
```

**Pros**: Consistent environment, no local setup needed
**Cons**: Slower reload times, harder debugging

### 2. Hybrid Mode (Recommended)
Database/Redis in Docker, FastAPI and Vue.js run locally for fastest iteration.

```bash
# Start only database and Redis
docker-compose -f docker-compose.services.yml up -d

# Run FastAPI locally (in backend/)
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Run Vue locally (in frontend/)
npm install
npm run dev
```

**Pros**: Fastest hot reload, easy debugging, IDE integration
**Cons**: Need Python/Node.js installed locally

### 3. Backend Hybrid Mode
Database/Redis in Docker, FastAPI locally, Frontend in Docker.

```bash
# Start services and frontend
docker-compose -f docker-compose.services.yml up -d
docker-compose -f docker-compose.yml up frontend -d

# Run FastAPI locally
DATABASE_URL=postgresql://kidney_user:kidney_pass@localhost:5432/kidney_genetics \
uvicorn app.main:app --reload --port 8000
```

### 4. Frontend Hybrid Mode  
All backend services in Docker, Vue.js runs locally.

```bash
# Start backend services
docker-compose up postgres redis backend -d

# Run Vue locally
VITE_API_URL=http://localhost:8000/api npm run dev
```

## Docker Compose Files

### docker-compose.yml
Production-like setup with all services.

### docker-compose.dev.yml
Full development stack with hot reloading:
- PostgreSQL with persistent volumes
- Redis for caching/queues
- FastAPI with code mounting
- Vue with Vite HMR

### docker-compose.services.yml
Only supporting services (DB + Redis) for hybrid development:
```yaml
services:
  postgres:
    image: postgres:14-alpine
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

## Makefile Commands

Inspired by agde-api's Makefile for convenient development:

```makefile
# Development (Full Docker)
make dev-up        # Start full Docker environment
make dev-down      # Stop Docker environment
make dev-logs      # Show logs
make dev-restart   # Restart services

# Hybrid Development (Recommended)
make hybrid-up     # Start DB/Redis + run FastAPI/Vue locally
make hybrid-down   # Stop services
make services-up   # Start only DB/Redis
make local-backend # Run FastAPI locally (assumes services running)
make local-frontend # Run Vue locally (assumes services running)

# Database
make db-migrate    # Run Alembic migrations
make db-reset      # Reset development database
make db-shell      # PostgreSQL shell access

# Utilities
make clean         # Clean up containers and volumes
make init-data     # Load sample data
```

## Environment Configuration

### .env for Hybrid Development
```env
# Database (when running locally)
DATABASE_URL=postgresql://kidney_user:kidney_pass@localhost:5432/kidney_genetics

# Redis (when running locally)  
REDIS_URL=redis://localhost:6379

# API Configuration
SECRET_KEY=dev-secret-key
ENVIRONMENT=development
DEBUG=true

# Frontend (when running locally)
VITE_API_URL=http://localhost:8000/api

# External APIs
PANELAPP_UK_URL=https://panelapp.genomicsengland.co.uk/api/v1
PANELAPP_AU_URL=https://panelapp.agha.umccr.org/api/v1
```

## Development Workflow Examples

### Daily Development (Hybrid Mode)
```bash
# Morning: Start services
make services-up

# Terminal 1: Backend with auto-reload
cd backend
uvicorn app.main:app --reload

# Terminal 2: Frontend with HMR
cd frontend  
npm run dev

# Terminal 3: Run pipeline
cd backend
python -m app.pipeline.run

# Evening: Stop services
make services-down
```

### Testing Database Changes
```bash
# Start only PostgreSQL
docker-compose -f docker-compose.services.yml up postgres -d

# Run migrations
cd backend
alembic upgrade head

# Test with psql
docker exec -it kidney_genetics_postgres psql -U kidney_user -d kidney_genetics
```

### Debugging Backend
```bash
# Start services
make services-up

# Run FastAPI with debugger (VS Code)
# Launch configuration in .vscode/launch.json
{
  "name": "FastAPI Debug",
  "type": "python",
  "request": "launch",
  "module": "uvicorn",
  "args": ["app.main:app", "--reload", "--port", "8000"],
  "env": {
    "DATABASE_URL": "postgresql://kidney_user:kidney_pass@localhost:5432/kidney_genetics"
  }
}
```

## Benefits of Hybrid Approach

1. **Fastest Development**: Local hot reload is much faster than Docker volumes
2. **Better Debugging**: Native debugger integration in IDEs
3. **Flexible Setup**: Choose what to run locally vs Docker
4. **Resource Efficient**: Only run what you need
5. **Easy Onboarding**: New developers can start with full Docker

## Troubleshooting

### Port Conflicts
If ports are already in use, modify docker-compose.services.yml:
```yaml
postgres:
  ports:
    - "5433:5432"  # Use different port
```

Then update DATABASE_URL:
```bash
DATABASE_URL=postgresql://kidney_user:kidney_pass@localhost:5433/kidney_genetics
```

### Database Connection Issues
```bash
# Check if PostgreSQL is running
docker ps | grep postgres

# Check PostgreSQL logs
docker logs kidney_genetics_postgres

# Test connection
docker exec -it kidney_genetics_postgres pg_isready -U kidney_user
```

### Permission Issues
If you get permission errors with volumes:
```bash
# Fix ownership
sudo chown -R $USER:$USER ./postgres_data
```