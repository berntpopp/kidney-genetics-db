# Development Workflow Guide

## Quick Start

### Fresh Development Environment
```bash
# Complete fresh start (clean DB + restart all services)
make fresh-start
```

### Check Status
```bash
# Show status of all services and data sources
make status
```

## Available Make Commands

### Database Management
- `make clean-db` - Remove all data from database tables
- `make reset-db` - Clean database and reset progress tracking
- `make clean-cache` - Clear all caches (PubTator, HGNC)

### Service Management
- `make restart-backend` - Stop and restart the backend server
- `make restart-frontend` - Stop and restart the frontend dev server
- `make restart-all` - Restart both backend and frontend
- `make stop-all` - Stop all running services

### Testing
- `make test-pubtator` - Run PubTator with test configuration (20 pages)
- `make status` - Show status of all services and data sources

### Complete Reset
- `make fresh-start` - Complete fresh start (clean DB + restart all)

## Configuration

### PubTator Settings
Edit `backend/app/core/config.py`:
```python
PUBTATOR_MAX_PAGES: int = 20  # Pages to fetch per run
PUBTATOR_MIN_PUBLICATIONS: int = 3  # Min publications for gene inclusion
PUBTATOR_BATCH_SIZE: int = 100  # PMIDs per batch
```

### Batch Normalization
The system now uses batch HGNC normalization with 20-gene batches to reduce API calls:
- Previously: 200+ individual API calls
- Now: ~10 batch API calls for same data

## Development Helper Script

For more complex operations:
```bash
./scripts/dev-helper.sh [command]
```

Commands:
- `check` - Check status of all services
- `clean-restart` - Clean database and restart all services
- `run-source [name]` - Trigger a specific data source
- `monitor` - Monitor progress in real-time
- `quick-test` - Set up minimal test environment

## Access Points

- **Backend API**: http://localhost:8000/docs
- **Frontend**: http://localhost:5173
- **Database**: PostgreSQL on localhost:5432

## Monitoring Logs

```bash
# Watch backend logs
make logs-backend

# Watch frontend logs
make logs-frontend

# Watch all logs
make logs
```

## Troubleshooting

### Server Not Responding
```bash
make stop-all
make start-backend
make start-frontend
```

### Database Issues
```bash
make reset-db
```

### PubTator Stuck
```bash
cd backend
uv run python reset_pubtator.py
```

## Testing Workflow

1. Start fresh environment:
   ```bash
   make fresh-start
   ```

2. Trigger PubTator test:
   ```bash
   make test-pubtator
   ```

3. Monitor progress:
   ```bash
   make status
   ```

4. Check UI at http://localhost:5173

## Key Improvements Implemented

✅ **Batch HGNC Normalization**: Processes genes in 20-gene batches instead of one-by-one
✅ **Centralized Configuration**: All settings in `backend/app/core/config.py`
✅ **Progress Tracking**: Real-time WebSocket updates for all data sources
✅ **UI Organization**: Separated data sources from internal processes
✅ **Development Tools**: Makefile and helper scripts for easy management

## Notes

- PubTator now processes 20 pages by default (configurable)
- Batch normalization reduces API calls by ~95%
- All data sources have real-time progress tracking
- Database can be completely reset for testing