# Development Guide

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Node.js 18+ (for local frontend development)
- Python 3.11+ (for local backend development)

### 1. Clone and Setup
```bash
# Clone the repository
git clone <repo-url>
cd kidney-genetics-db

# Copy environment variables
cp .env.example .env
# Edit .env with your configuration
```

### 2. Start with Docker
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

Services will be available at:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Database: localhost:5432

### 3. Run Data Pipeline
```bash
# Execute pipeline to fetch data from all sources
docker-compose exec backend python -m app.pipeline.run

# Or trigger via API
curl -X POST http://localhost:8000/api/pipeline/run \
  -H "Authorization: Bearer <token>"
```

## Local Development

### Backend Development
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload --port 8000
```

### Frontend Development
```bash
cd frontend
npm install
npm run dev  # Starts on http://localhost:3000
```

### Database Access
```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U kidney_user -d kidney_genetics

# Backup database
docker-compose exec postgres pg_dump -U kidney_user kidney_genetics > backup.sql

# Restore database
docker-compose exec -T postgres psql -U kidney_user kidney_genetics < backup.sql
```

## Project Structure

```
kidney-genetics-db/
├── backend/          # FastAPI backend
│   ├── app/
│   │   ├── api/      # API endpoints
│   │   ├── models/   # Database models
│   │   ├── pipeline/ # Data processing
│   │   └── main.py   # Application entry
│   └── requirements.txt
├── frontend/         # Vue.js frontend
│   ├── src/
│   │   ├── api/      # API client
│   │   ├── components/
│   │   └── views/
│   └── package.json
├── docker-compose.yml
└── init.sql         # Database schema
```

## Data Sources

The pipeline fetches data from 5 core sources:

1. **PanelApp** (UK & Australia) - Gene panels via API
2. **Literature** - Manual curation from Excel files
3. **Diagnostic Panels** - Web scraping from commercial providers
4. **HPO** - Human Phenotype Ontology API
5. **PubTator** - Literature mining API

## Testing

### Backend Tests
```bash
cd backend
pytest tests/ -v
```

### Frontend Tests
```bash
cd frontend
npm run test
```

## Deployment

### Production Build
```bash
# Build production images
docker-compose -f docker-compose.prod.yml build

# Deploy with environment variables
docker-compose -f docker-compose.prod.yml up -d
```

## Troubleshooting

### Database Connection Issues
- Check PostgreSQL is running: `docker-compose ps`
- Verify credentials in `.env` file
- Check logs: `docker-compose logs postgres`

### API Errors
- Check backend logs: `docker-compose logs backend`
- Verify API is accessible: `curl http://localhost:8000/health`
- Check database migrations: `docker-compose exec backend alembic current`

### Frontend Build Issues
- Clear node_modules: `rm -rf frontend/node_modules && npm install`
- Check API URL in `.env`: `VITE_API_URL`
- Verify backend is running: `docker-compose ps backend`

## Contributing

1. Create a feature branch
2. Make changes and test locally
3. Run linters and tests
4. Submit pull request

## License

See LICENSE file for details.