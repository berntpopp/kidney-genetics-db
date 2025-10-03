# Automated Database Backup Plan

**GitHub Issue**: #23
**Status**: Planning
**Priority**: High (Data Protection)
**Effort**: 1-2 days

## Problem Statement

Current backup system requires manual execution:
- No automated daily backups
- No retention policy
- Manual restore process
- Backup files accumulate without cleanup

**Current State**: `make db-backup-full` exists but is manual only.

## Proposed Solution

**Keep It Simple: Cron + Shell Scripts**
- No Python service
- No APScheduler integration
- No complex logic
- Just proven Unix tools

### Architecture

```
┌──────────────────────────────────────┐
│  Cron (system or Docker)             │
│  - Daily at 2 AM                     │
│  - Runs backup script                │
└────────────┬─────────────────────────┘
             ↓
┌──────────────────────────────────────┐
│  backup-database.sh                  │
│  - pg_dump to .sql.gz                │
│  - Timestamp naming                  │
│  - Success/failure logging           │
└────────────┬─────────────────────────┘
             ↓
┌──────────────────────────────────────┐
│  cleanup-old-backups.sh              │
│  - Keep last 7 days only             │
│  - Find + delete older files         │
└──────────────────────────────────────┘
```

## Implementation

### 1. Backup Script (`scripts/backup-database.sh`)

```bash
#!/bin/bash
set -e

# Configuration
BACKUP_DIR="backups"
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
BACKUP_FILE="${BACKUP_DIR}/backup_${TIMESTAMP}.sql.gz"
LOG_FILE="${BACKUP_DIR}/backup.log"

# Create backup directory if it doesn't exist
mkdir -p "${BACKUP_DIR}"

# Log function
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "${LOG_FILE}"
}

# Perform backup
log "Starting database backup..."

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Execute pg_dump with compression
PGPASSWORD="${POSTGRES_PASSWORD}" pg_dump \
    -h "${POSTGRES_HOST:-localhost}" \
    -p "${POSTGRES_PORT:-5432}" \
    -U "${POSTGRES_USER}" \
    -d "${POSTGRES_DB}" \
    --no-owner \
    --no-acl \
    | gzip > "${BACKUP_FILE}"

# Check if backup was successful
if [ $? -eq 0 ]; then
    BACKUP_SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
    log "✓ Backup successful: ${BACKUP_FILE} (${BACKUP_SIZE})"
    exit 0
else
    log "✗ Backup failed!"
    exit 1
fi
```

### 2. Cleanup Script (`scripts/cleanup-old-backups.sh`)

```bash
#!/bin/bash
set -e

BACKUP_DIR="backups"
RETENTION_DAYS=7
LOG_FILE="${BACKUP_DIR}/backup.log"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "${LOG_FILE}"
}

log "Cleaning up backups older than ${RETENTION_DAYS} days..."

# Find and delete old backups
DELETED=$(find "${BACKUP_DIR}" \
    -name "backup_*.sql.gz" \
    -type f \
    -mtime +${RETENTION_DAYS} \
    -delete \
    -print | wc -l)

if [ "${DELETED}" -gt 0 ]; then
    log "✓ Deleted ${DELETED} old backup(s)"
else
    log "No old backups to delete"
fi
```

### 3. Restore Script (`scripts/restore-database.sh`)

```bash
#!/bin/bash
set -e

# Usage: ./restore-database.sh backups/backup_2025-10-03_02-00-00.sql.gz

BACKUP_FILE=$1
SAFETY_BACKUP="backups/pre-restore_$(date +%Y-%m-%d_%H-%M-%S).sql.gz"
LOG_FILE="backups/restore.log"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "${LOG_FILE}"
}

# Validate backup file
if [ -z "${BACKUP_FILE}" ]; then
    echo "Usage: $0 <backup_file.sql.gz>"
    exit 1
fi

if [ ! -f "${BACKUP_FILE}" ]; then
    log "✗ Backup file not found: ${BACKUP_FILE}"
    exit 1
fi

# Verify it's a gzipped file
if ! file "${BACKUP_FILE}" | grep -q "gzip compressed"; then
    log "✗ File is not gzipped: ${BACKUP_FILE}"
    exit 1
fi

# Create safety backup before restore
log "Creating safety backup before restore..."
./scripts/backup-database.sh

# Load environment
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Restore database
log "Restoring from ${BACKUP_FILE}..."

# Drop and recreate database
PGPASSWORD="${POSTGRES_PASSWORD}" psql \
    -h "${POSTGRES_HOST:-localhost}" \
    -p "${POSTGRES_PORT:-5432}" \
    -U "${POSTGRES_USER}" \
    -d postgres \
    -c "DROP DATABASE IF EXISTS ${POSTGRES_DB};"

PGPASSWORD="${POSTGRES_PASSWORD}" psql \
    -h "${POSTGRES_HOST:-localhost}" \
    -p "${POSTGRES_PORT:-5432}" \
    -U "${POSTGRES_USER}" \
    -d postgres \
    -c "CREATE DATABASE ${POSTGRES_DB};"

# Restore from backup
gunzip -c "${BACKUP_FILE}" | \
    PGPASSWORD="${POSTGRES_PASSWORD}" psql \
    -h "${POSTGRES_HOST:-localhost}" \
    -p "${POSTGRES_PORT:-5432}" \
    -U "${POSTGRES_USER}" \
    -d "${POSTGRES_DB}"

if [ $? -eq 0 ]; then
    log "✓ Restore successful from ${BACKUP_FILE}"
    log "Safety backup saved to: ${SAFETY_BACKUP}"
else
    log "✗ Restore failed!"
    exit 1
fi
```

### 4. Cron Setup

**System Cron** (`/etc/crontab` or `crontab -e`):
```cron
# Daily backup at 2 AM
0 2 * * * cd /path/to/kidney-genetics-db && ./scripts/backup-database.sh

# Cleanup at 2:05 AM
5 2 * * * cd /path/to/kidney-genetics-db && ./scripts/cleanup-old-backups.sh
```

**Docker Cron** (add to docker-compose.yml):
```yaml
services:
  backup-cron:
    image: alpine:latest
    container_name: kidney-genetics-backup-cron
    volumes:
      - ./scripts:/scripts
      - ./backups:/backups
      - ./.env:/.env:ro
    networks:
      - kidney-genetics-internal
    command: >
      sh -c "
        apk add --no-cache postgresql-client dcron &&
        echo '0 2 * * * cd /app && /scripts/backup-database.sh' | crontab - &&
        echo '5 2 * * * cd /app && /scripts/cleanup-old-backups.sh' | crontab - &&
        crond -f -l 2
      "
    restart: unless-stopped
```

### 5. Makefile Integration

```makefile
# Makefile additions

.PHONY: backup backup-restore backup-setup backup-list backup-cleanup

backup:  ## Manually trigger database backup
	@./scripts/backup-database.sh

backup-restore:  ## Restore database from backup
	@if [ -z "$(file)" ]; then \
		echo "Usage: make backup-restore file=backups/backup_YYYY-MM-DD_HH-MM-SS.sql.gz"; \
		exit 1; \
	fi
	@./scripts/restore-database.sh $(file)

backup-setup:  ## Setup automated backups via cron
	@echo "Setting up cron jobs..."
	@(crontab -l 2>/dev/null; echo "0 2 * * * cd $(PWD) && ./scripts/backup-database.sh") | crontab -
	@(crontab -l 2>/dev/null; echo "5 2 * * * cd $(PWD) && ./scripts/cleanup-old-backups.sh") | crontab -
	@echo "✓ Cron jobs installed"
	@crontab -l

backup-list:  ## List available backups
	@echo "Available backups:"
	@ls -lh backups/backup_*.sql.gz 2>/dev/null || echo "No backups found"

backup-cleanup:  ## Manually run backup cleanup
	@./scripts/cleanup-old-backups.sh
```

## Optional: Admin UI Upload Feature

**Backend API** (`backend/app/api/endpoints/admin/backups.py`):

```python
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from app.core.auth import get_current_admin_user
import hashlib
import gzip
import shutil
from pathlib import Path

router = APIRouter()

BACKUP_DIR = Path("backups")
MAX_SIZE = 500 * 1024 * 1024  # 500MB

@router.post("/upload")
async def upload_backup(
    file: UploadFile = File(...),
    current_user = Depends(get_current_admin_user)
):
    """Upload a backup file (admin only)"""

    # Validate filename
    if not file.filename.endswith(".sql.gz"):
        raise HTTPException(400, "Only .sql.gz files allowed")

    # Prevent path traversal
    safe_filename = Path(file.filename).name
    if safe_filename != file.filename:
        raise HTTPException(400, "Invalid filename")

    # Read file with size limit
    content = await file.read(MAX_SIZE + 1)
    if len(content) > MAX_SIZE:
        raise HTTPException(413, "File too large (max 500MB)")

    # Verify gzip format
    try:
        gzip.decompress(content[:100])  # Test first 100 bytes
    except:
        raise HTTPException(400, "Invalid gzip format")

    # Calculate checksum
    sha256 = hashlib.sha256(content).hexdigest()

    # Save file
    backup_path = BACKUP_DIR / safe_filename
    with open(backup_path, "wb") as f:
        f.write(content)

    # Log upload
    logger.info(
        f"Backup uploaded by {current_user.username}",
        filename=safe_filename,
        size=len(content),
        checksum=sha256
    )

    return {
        "filename": safe_filename,
        "size": len(content),
        "checksum": sha256,
        "path": str(backup_path)
    }
```

## Implementation Timeline

### Day 1: Core Scripts
- [ ] Write `backup-database.sh`
- [ ] Write `cleanup-old-backups.sh`
- [ ] Write `restore-database.sh`
- [ ] Test scripts locally
- [ ] Add execute permissions

### Day 2: Integration
- [ ] Add Makefile targets
- [ ] Document cron setup
- [ ] Test full backup/restore cycle
- [ ] Create `.env` variable documentation
- [ ] Add logging directory to .gitignore

### Day 3: Optional Admin UI (if needed)
- [ ] Create upload API endpoint
- [ ] Add admin UI upload component
- [ ] Test upload security
- [ ] Document upload procedure

## Acceptance Criteria

- [ ] Daily backups run automatically at 2 AM
- [ ] Backups compressed with gzip
- [ ] Filename format: `backup_YYYY-MM-DD_HH-MM-SS.sql.gz`
- [ ] Old backups deleted after 7 days
- [ ] Restore script creates safety backup first
- [ ] All operations logged to `backups/backup.log`
- [ ] Makefile targets work correctly
- [ ] Documentation complete
- [ ] Admin upload endpoint (optional) secure

## Benefits

**Simplicity**:
- Just bash + pg_dump + cron
- No Python dependencies
- No APScheduler integration
- Easy to debug

**Reliability**:
- Proven Unix tools
- Simple error handling
- Clear logging
- Safety backups before restore

**Lightweight**:
- No background services
- Minimal resource usage
- Works in any environment

## Security Considerations

- [ ] Backup files excluded from git (`.gitignore`)
- [ ] Database credentials from environment variables
- [ ] Backup directory permissions (700)
- [ ] Log files readable only by owner
- [ ] Upload endpoint admin-only
- [ ] Path traversal prevention
- [ ] File size limits enforced

## Testing Plan

```bash
# Test backup
make backup

# Verify backup exists
make backup-list

# Test restore
make backup-restore file=backups/backup_2025-10-03_02-00-00.sql.gz

# Test cleanup (manually adjust dates for testing)
make backup-cleanup

# Setup cron
make backup-setup

# Verify cron jobs
crontab -l
```

## References

- **pg_dump Documentation**: https://www.postgresql.org/docs/current/app-pgdump.html
- **Cron Format**: https://crontab.guru/
- **GitHub Issue**: #23

## Future Enhancements

- [ ] Off-site backup (S3, Google Cloud Storage)
- [ ] Encryption at rest
- [ ] Backup verification (restore to temp DB)
- [ ] Email notifications on failure
- [ ] Backup size monitoring
- [ ] Incremental backups (WAL archiving)
