# Installation Guide

**Detailed environment setup for the Kidney Genetics Database**

## Overview

This guide covers complete installation and configuration for development. For a quick start, see the [Quick Start Guide](quick-start.md).

## System Requirements

### Required Software

| Software | Minimum Version | Recommended | Purpose |
|----------|----------------|-------------|---------|
| Python | 3.11 | 3.11+ | Backend runtime |
| Node.js | 18.0 | 20.0+ | Frontend runtime |
| PostgreSQL | 14.0 | 15.0+ | Database |
| Docker | 20.10 | Latest | Containerization |
| Docker Compose | 2.0 | Latest | Multi-container |
| Make | 3.81 | Latest | Build automation |
| Git | 2.30 | Latest | Version control |

### Operating Systems

- ✅ Linux (Ubuntu 20.04+, Debian 11+)
- ✅ macOS (11.0+)
- ✅ Windows (WSL2 required)

### Hardware Requirements

**Minimum**:
- 4 GB RAM
- 2 CPU cores
- 5 GB disk space

**Recommended**:
- 8 GB RAM
- 4 CPU cores
- 10 GB disk space

## Step-by-Step Installation

### 1. Install System Dependencies

#### Ubuntu/Debian
```bash
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3-pip \
                    nodejs npm postgresql-client \
                    docker.io docker-compose make git
```

#### macOS (using Homebrew)
```bash
brew install python@3.11 node postgresql@15 docker docker-compose make git
```

#### Windows (WSL2)
```bash
# In WSL2 terminal
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3-pip \
                    nodejs npm postgresql-client make git

# Install Docker Desktop for Windows (with WSL2 backend)
# Download from: https://www.docker.com/products/docker-desktop
```

### 2. Install UV Package Manager

UV is used for Python package management (not pip/poetry):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Verify installation:
```bash
uv --version
```

### 3. Clone Repository

```bash
git clone <repository-url>
cd kidney-genetics-db
```

### 4. Backend Setup

```bash
cd backend

# Create virtual environment
uv venv

# Install dependencies
uv sync

# Verify installation
uv run python --version  # Should be 3.11+
```

### 5. Frontend Setup

```bash
cd ../frontend

# Install dependencies
npm install

# Verify installation
npm --version
node --version
```

### 6. Environment Configuration

```bash
cd ..

# Copy example environment file
cp .env.example .env

# Edit configuration
nano .env
```

#### Required Environment Variables

```bash
# Database
DATABASE_URL=postgresql://kidney_user:kidney_pass@localhost:5432/kidney_genetics

# JWT
JWT_SECRET_KEY=<generate-random-string>
JWT_ALGORITHM=HS256

# Admin
ADMIN_EMAIL=admin@kidney-genetics.local
ADMIN_PASSWORD=<secure-password>

# API Keys (optional but recommended)
NCBI_API_KEY=<your-ncbi-api-key>
```

#### Generate JWT Secret

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 7. Database Setup

#### Option A: Docker (Recommended)

```bash
make hybrid-up
```

This will:
- Start PostgreSQL in Docker
- Create database schema
- Run migrations
- Seed initial data

#### Option B: Local PostgreSQL

If you have PostgreSQL installed locally:

```bash
# Create user and database
sudo -u postgres psql
CREATE USER kidney_user WITH PASSWORD 'kidney_pass';
CREATE DATABASE kidney_genetics OWNER kidney_user;
\q

# Run migrations
cd backend
uv run alembic upgrade head

# Seed data
uv run python -m app.db.init_db
```

### 8. Verify Installation

```bash
make status
```

Expected output:
```
✅ Database: Running
✅ Backend: Ready
✅ Frontend: Ready
```

## Development Environment Modes

### Hybrid Mode (Recommended)

Database in Docker, services local:

```bash
make hybrid-up    # Start database
make backend      # Terminal 1
make frontend     # Terminal 2
```

**Advantages**:
- Fast hot reload
- Easy debugging
- Direct code access
- Fast dependency updates

### Full Docker Mode

All services in Docker:

```bash
make dev-up
```

**Advantages**:
- Consistent environment
- Easy to share
- Isolated from host

## Post-Installation Tasks

### 1. Create Admin User

```bash
cd backend
uv run python -m app.scripts.create_admin \
  --email admin@kidney-genetics.local \
  --password <secure-password>
```

### 2. Run Initial Data Pipeline

```bash
# Start backend first
make backend

# In another terminal, trigger pipeline
curl -X POST http://localhost:8000/api/pipeline/run \
  -H "Authorization: Bearer <admin-token>"
```

### 3. Verify Data

```bash
# Check gene count
curl http://localhost:8000/api/genes | jq '.meta.total'

# Should show 571+ genes
```

## IDE Configuration

### VSCode

Install recommended extensions:
- Python (Microsoft)
- Pylance
- Vue - Official
- ESLint
- Prettier

#### Settings (.vscode/settings.json)

```json
{
  "python.defaultInterpreterPath": "./backend/.venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "editor.formatOnSave": true,
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff"
  },
  "[vue]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  }
}
```

### PyCharm

1. Open project
2. File → Settings → Project → Python Interpreter
3. Add interpreter → Existing → `./backend/.venv/bin/python`
4. Enable Ruff for linting

## Troubleshooting Installation

### UV Installation Fails

**Error**: "command not found: uv"

**Solution**:
```bash
# Add to PATH
export PATH="$HOME/.cargo/bin:$PATH"

# Add to ~/.bashrc or ~/.zshrc
echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### Database Connection Issues

**Error**: "Connection refused"

**Solution**:
```bash
# Check Docker is running
docker ps

# Check database logs
docker logs kidney-genetics-db-postgres-1

# Verify DATABASE_URL in .env
```

### Port Conflicts

**Error**: "Address already in use"

**Solution**:
```bash
# Find process using port
lsof -i :8000  # Backend
lsof -i :5173  # Frontend
lsof -i :5432  # Database

# Kill process
kill -9 <PID>

# Or change ports in .env
```

### Node Modules Issues

**Error**: "Cannot find module"

**Solution**:
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

## Uninstallation

To completely remove the development environment:

```bash
# Stop all services
make clean-all

# Remove Docker volumes
docker volume rm $(docker volume ls -q | grep kidney-genetics)

# Remove virtual environments
rm -rf backend/.venv
rm -rf frontend/node_modules

# Remove generated files
rm -rf backend/__pycache__
rm -rf backend/.pytest_cache
```

## Next Steps

1. **[Development Workflow](development-workflow.md)** - Daily development guide
2. **[Developer Guides](../guides/developer/)** - Comprehensive guides
3. **[Architecture](../architecture/)** - System design
4. **[CLAUDE.md](../../CLAUDE.md)** - Complete guidelines

## Support

For installation issues:
- Check [Troubleshooting Guide](../troubleshooting/common-issues.md)
- Review [Developer Guides](../guides/developer/)
- Create an issue in the repository

---

**Estimated Setup Time**: 15-30 minutes
**Difficulty**: Intermediate
**Last Updated**: September 2025