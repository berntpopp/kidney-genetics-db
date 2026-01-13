# ARQ Worker Deployment Guide

This guide covers deploying the ARQ (Async Redis Queue) worker for background pipeline jobs.

## Overview

ARQ is used for long-running annotation pipeline tasks that need to survive web server restarts. Tasks like ClinVar annotation (which queries NCBI APIs with rate limiting) can take several hours for 5000+ genes.

**Benefits of ARQ worker:**
- Tasks survive web server restarts/reloads
- Proper job timeout handling for long-running tasks
- Redis-based job persistence
- Built-in retry with exponential backoff
- Health monitoring

## Prerequisites

1. **Redis Server** - Required for ARQ job queue
2. **Python environment** with `arq` package installed

## Quick Start

### 1. Start Redis

Using Docker (recommended):
```bash
# Start Redis using docker-compose
make hybrid-up  # Includes Redis service
```

Or manually:
```bash
docker run -d --name redis -p 6379:6379 redis:7-alpine
```

### 2. Configure Environment

Add to your `.env` file:
```bash
# Enable ARQ worker mode
USE_ARQ_WORKER=True

# Redis connection
REDIS_URL=redis://localhost:6379/0

# Worker configuration
ARQ_QUEUE_NAME=kidney_genetics_tasks
ARQ_MAX_JOBS=3
ARQ_JOB_TIMEOUT=21600  # 6 hours for long annotation pipelines
```

### 3. Start the ARQ Worker

```bash
cd backend
uv run arq app.core.arq_worker.WorkerSettings
```

Or using Make:
```bash
make worker
```

## Configuration Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `USE_ARQ_WORKER` | `False` | Enable ARQ mode (True) or in-process tasks (False) |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL |
| `ARQ_QUEUE_NAME` | `kidney_genetics_tasks` | Name of the job queue |
| `ARQ_MAX_JOBS` | `3` | Maximum concurrent jobs per worker |
| `ARQ_JOB_TIMEOUT` | `21600` | Default job timeout in seconds (6 hours) |

## Per-Job Timeouts

Different task types have different timeouts:

| Task | Timeout | Use Case |
|------|---------|----------|
| `run_pipeline_task` | 2 hours | Single source updates (ClinVar, Ensembl) |
| `run_annotation_pipeline_task` | 6 hours | Full pipeline with all sources |

These are configured in `app/core/arq_worker.py` using ARQ's `func()` wrapper.

## Production Deployment

### Docker Compose

Add the worker service to your `docker-compose.yml`:

```yaml
arq-worker:
  build:
    context: ./backend
    dockerfile: Dockerfile
  container_name: kidney_genetics_worker
  command: ["arq", "app.core.arq_worker.WorkerSettings"]
  environment:
    - DATABASE_URL=postgresql://kidney_user:kidney_pass@db:5432/kidney_genetics
    - REDIS_URL=redis://redis:6379/0
    - USE_ARQ_WORKER=True
  depends_on:
    db:
      condition: service_healthy
    redis:
      condition: service_healthy
  restart: unless-stopped
```

### Systemd Service

Create `/etc/systemd/system/kidney-genetics-worker.service`:

```ini
[Unit]
Description=Kidney Genetics ARQ Worker
After=network.target redis.service postgresql.service

[Service]
Type=simple
User=kidney
WorkingDirectory=/opt/kidney-genetics/backend
Environment="PATH=/opt/kidney-genetics/backend/.venv/bin"
ExecStart=/opt/kidney-genetics/backend/.venv/bin/arq app.core.arq_worker.WorkerSettings
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable kidney-genetics-worker
sudo systemctl start kidney-genetics-worker
```

## Monitoring

### Health Check

ARQ automatically reports health status to Redis. Check worker status:

```bash
# Using redis-cli
redis-cli GET arq:health-check

# Using the API (when implemented)
curl http://localhost:8000/api/admin/worker-status
```

### Logs

Worker logs include job IDs for tracing:

```bash
# View worker logs
journalctl -u kidney-genetics-worker -f

# Or in Docker
docker logs kidney_genetics_worker -f
```

## Troubleshooting

### Worker not picking up jobs

1. Check Redis connection: `redis-cli ping`
2. Verify `USE_ARQ_WORKER=True` in API environment
3. Check queue name matches: `ARQ_QUEUE_NAME`

### Jobs timing out

1. Increase `ARQ_JOB_TIMEOUT` for default timeout
2. Check per-job timeouts in `arq_worker.py`
3. For ClinVar/Ensembl annotation, 2+ hours is normal due to rate limiting

### Database connection errors

1. Ensure `DATABASE_URL` is accessible from worker container/host
2. Check connection pool limits in PostgreSQL
3. Worker creates its own connections separate from API

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   FastAPI   │────▶│    Redis    │◀────│ ARQ Worker  │
│   (API)     │     │   (Queue)   │     │  (Jobs)     │
└─────────────┘     └─────────────┘     └─────────────┘
       │                                       │
       └───────────────┬───────────────────────┘
                       ▼
               ┌─────────────┐
               │ PostgreSQL  │
               │  (Data)     │
               └─────────────┘
```

- **API** enqueues jobs to Redis
- **Worker** picks up jobs from Redis
- Both connect to PostgreSQL for data
- Progress tracked in database (survives restarts)

## References

- [ARQ Documentation](https://arq-docs.helpmanual.io/)
- [ARQ GitHub](https://github.com/python-arq/arq)
- [Redis Documentation](https://redis.io/docs/)
