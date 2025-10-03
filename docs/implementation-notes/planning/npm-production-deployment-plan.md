# Nginx Proxy Manager Production Deployment Plan

**GitHub Issue**: #22
**Status**: Planning
**Priority**: High (Production Blocker)
**Effort**: 2-3 days

## Problem Statement

Current Docker setup is development-focused and not production-ready:
- Direct port exposure (3000, 8000, 5432) not suitable for production
- No SSL/TLS termination
- No reverse proxy configuration
- No automated certificate management
- Missing production optimizations (logging, resource limits, health checks)
- Not compatible with standard reverse proxy managers like NPM

## Proposed Solution

Create production-ready Docker Compose setup compatible with **Nginx Proxy Manager (NPM)**

### Architecture

```
┌─────────────────────────────────────────────┐
│  Nginx Proxy Manager (NPM)                  │
│  - SSL/TLS termination (Let's Encrypt)      │
│  - Domain routing                           │
│  - Access lists & authentication            │
└──────────────────┬──────────────────────────┘
                   │ (Internal Docker Network)
        ┌──────────┼──────────┬────────┐
        ↓          ↓          ↓        ↓
   ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
   │Frontend│ │Backend │ │Postgres│ │ Redis  │
   │ (nginx)│ │FastAPI │ │   DB   │ │ Cache  │
   └────────┘ └────────┘ └────────┘ └────────┘
```

### Key Features

**1. Internal Docker Network**
- No direct port exposure to host
- NPM communicates via internal bridge network
- Database accessible only to backend
- Secure service-to-service communication

**2. Production Optimizations**
- Health checks for all services
- Resource limits (CPU, memory)
- Structured logging with rotation
- Restart policies (unless-stopped)
- Multi-stage build for smaller images

**3. Security**
- No exposed database ports
- Environment-based secrets (.env files)
- NPM handles SSL certificates automatically
- Optional basic auth via NPM
- Non-root container users

## Implementation Files

### 1. `docker-compose.prod.yml`

```yaml
version: '3.8'

services:
  # PostgreSQL Database
  db:
    image: postgres:14-alpine
    container_name: kidney-genetics-db-prod
    networks:
      - kidney-genetics-internal
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data_prod:/var/lib/postgresql/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  # Redis Cache
  redis:
    image: redis:7-alpine
    container_name: kidney-genetics-redis-prod
    networks:
      - kidney-genetics-internal
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M

  # Backend API
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile.prod
    container_name: kidney-genetics-api-prod
    networks:
      - kidney-genetics-internal
    environment:
      DATABASE_URL: postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}
      REDIS_URL: redis://redis:6379/0
      ENVIRONMENT: production
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 1G
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  # Frontend
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.prod
      args:
        VITE_API_URL: ${VITE_API_URL}
    container_name: kidney-genetics-frontend-prod
    networks:
      - kidney-genetics-internal
    depends_on:
      - backend
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:80"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M

networks:
  kidney-genetics-internal:
    driver: bridge
    name: kidney-genetics-prod

volumes:
  postgres_data_prod:
    name: kidney-genetics-postgres-prod
```

### 2. `backend/Dockerfile.prod`

```dockerfile
# Multi-stage build for production
FROM python:3.11-slim as builder

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install UV
RUN pip install uv

# Copy dependency files
WORKDIR /app
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Production stage
FROM python:3.11-slim

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 appuser

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Set PATH to use virtual environment
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### 3. `frontend/Dockerfile.prod`

```dockerfile
# Build stage
FROM node:20-alpine as builder

WORKDIR /app

# Copy package files
COPY package*.json ./
RUN npm ci --only=production

# Copy source and build
COPY . .
ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy custom nginx config
COPY nginx.prod.conf /etc/nginx/conf.d/default.conf

# Copy built files
COPY --from=builder /app/dist /usr/share/nginx/html

# Create non-root user
RUN chown -R nginx:nginx /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

### 4. `frontend/nginx.prod.conf`

```nginx
server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/xml+rss application/json;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Vue Router history mode
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Health check endpoint
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
```

### 5. `.env.production` (Example)

```bash
# Database
POSTGRES_DB=kidney_genetics
POSTGRES_USER=kidney_genetics_user
POSTGRES_PASSWORD=CHANGE_ME_IN_PRODUCTION

# Backend
ENVIRONMENT=production
SECRET_KEY=CHANGE_ME_GENERATE_SECURE_KEY

# Frontend
VITE_API_URL=https://api.yourdomain.com
```

### 6. `docs/deployment/npm-setup.md`

```markdown
# Nginx Proxy Manager Setup Guide

## Prerequisites
- Domain name (e.g., kidney-genetics.yourdomain.com)
- NPM already running on your server

## Steps

### 1. Start Production Stack

```bash
# Copy environment template
cp .env.production .env

# Edit .env with your secure values
nano .env

# Start services
docker-compose -f docker-compose.prod.yml up -d
```

### 2. Configure NPM Proxy Host

1. Open NPM web UI (usually http://your-server:81)
2. Add Proxy Host:
   - **Domain Names**: kidney-genetics.yourdomain.com
   - **Scheme**: http
   - **Forward Hostname**: kidney-genetics-frontend-prod
   - **Forward Port**: 80
   - **Block Common Exploits**: ✓
   - **Websockets Support**: ✓

3. SSL Tab:
   - **SSL Certificate**: Request New SSL Certificate
   - **Force SSL**: ✓
   - **HTTP/2 Support**: ✓
   - **Email**: your@email.com
   - **Agree to Let's Encrypt TOS**: ✓

### 3. Configure API Proxy Host

1. Add another Proxy Host:
   - **Domain Names**: api.kidney-genetics.yourdomain.com
   - **Scheme**: http
   - **Forward Hostname**: kidney-genetics-api-prod
   - **Forward Port**: 8000
   - Configure SSL same as above

### 4. Verify Deployment

```bash
# Check service health
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f backend
```

Visit https://kidney-genetics.yourdomain.com
```

## Migration Strategy

### Phase 1: Infrastructure Setup (Day 1)
- [ ] Create `docker-compose.prod.yml`
- [ ] Create production Dockerfiles
- [ ] Create nginx production config
- [ ] Test local build

### Phase 2: Production Configuration (Day 2)
- [ ] Create `.env.production` template
- [ ] Document environment variables
- [ ] Add health checks
- [ ] Configure logging

### Phase 3: NPM Integration (Day 3)
- [ ] Write NPM setup guide
- [ ] Test with NPM locally
- [ ] Document SSL setup
- [ ] Create deployment checklist

### Phase 4: Deployment (Day 4)
- [ ] Deploy to staging
- [ ] Configure NPM proxy hosts
- [ ] Test SSL certificates
- [ ] Performance testing
- [ ] Document rollback procedure

## Benefits

**One-Command Deployment**:
```bash
docker-compose -f docker-compose.prod.yml up -d
```

**NPM Provides**:
- Web UI for SSL and domain management
- Automatic Let's Encrypt certificate renewal
- Access control lists
- Basic authentication
- Rate limiting

**Production-Grade**:
- Structured logging with rotation
- Health checks and auto-restart
- Resource limits
- Security hardening

## Security Checklist

- [ ] Change all default passwords
- [ ] Generate secure SECRET_KEY
- [ ] Database not exposed to host
- [ ] Use environment variables for secrets
- [ ] Enable NPM access lists (optional)
- [ ] Configure firewall rules
- [ ] Set up automated backups
- [ ] Review nginx security headers

## Performance Considerations

**Resource Limits**:
- Backend: 2 CPUs, 1GB RAM
- Frontend: 1 CPU, 512MB RAM
- Database: 2 CPUs, 2GB RAM
- Redis: 1 CPU, 512MB RAM

**Scaling Options**:
- Horizontal: Multiple backend replicas
- Vertical: Increase resource limits
- Database: PostgreSQL connection pooling

## Monitoring

**Health Endpoints**:
- Frontend: `http://frontend/health`
- Backend: `http://backend:8000/health`
- Database: `pg_isready`
- Redis: `redis-cli ping`

**Logging**:
- JSON format
- 10MB max size
- 3 file rotation
- Centralized with Docker logging drivers

## Acceptance Criteria

- [ ] Services start with single command
- [ ] No ports exposed to host (NPM only)
- [ ] SSL certificates auto-renew
- [ ] Health checks working
- [ ] Logs rotating properly
- [ ] Resource limits enforced
- [ ] Non-root containers
- [ ] NPM setup documented
- [ ] Rollback procedure documented

## References

- **Nginx Proxy Manager**: https://nginxproxymanager.com/
- **Docker Production Best Practices**: https://docs.docker.com/develop/dev-best-practices/
- **Let's Encrypt**: https://letsencrypt.org/
- **GitHub Issue**: #22

## Future Enhancements

- [ ] Add Prometheus monitoring
- [ ] Grafana dashboards
- [ ] Automated backups
- [ ] Blue-green deployment
- [ ] CI/CD integration
