# Migration Squashing Plan (CORRECTED)
## Database Schema Consolidation - Tables Only

### ⚠️ CRITICAL: Architecture Understanding
- **Migrations**: Handle ONLY tables, indexes, constraints
- **Views**: Managed by `app/db/views.py` using ReplaceableObject pattern
- **View Creation**: Done at application startup or via manual refresh
- **Current State**: 7 migrations accumulated → squash to 1

### 🎯 Goal: Single Clean Migration
From: `001_initial_complete` → ... → `86bdb75bc293` (7 files)
To: `000_complete_schema` (1 file)

## EXECUTION PLAN

### Step 1: Full Backup (MANDATORY)
```bash
# Create timestamped backup directory
mkdir -p backups/$(date +%Y%m%d)
cd backups/$(date +%Y%m%d)

# 1.1 Complete database backup
docker exec kidney-genetics-db_postgres_1 pg_dump -U postgres kidney_genetics_db > full_backup.sql

# 1.2 Schema only (for reference)
docker exec kidney-genetics-db_postgres_1 pg_dump -U postgres kidney_genetics_db --schema-only > schema_only.sql

# 1.3 Data only (for restore)
docker exec kidney-genetics-db_postgres_1 pg_dump -U postgres kidney_genetics_db --data-only --disable-triggers > data_only.sql

# 1.4 Current migration state
cd ../../backend
uv run alembic current > ../../backups/$(date +%Y%m%d)/migration_state.txt

# 1.5 List of current genes (validation)
uv run python -c "
from app.core.database import SessionLocal
from app.models import Gene
db = SessionLocal()
print(f'Total genes: {db.query(Gene).count()}')
db.close()
" > ../../backups/$(date +%Y%m%d)/gene_count.txt
```

### Step 2: Export Current Schema as Python
```bash
# Generate schema from current database
uv run python scripts/export_schema.py > current_schema.py
```

Create `scripts/export_schema.py`:
```python
#!/usr/bin/env python
"""Export current database schema for squashed migration"""

from sqlalchemy import create_engine, MetaData, text
from app.core.config import settings
import sys

def export_schema():
    engine = create_engine(settings.DATABASE_URL)
    metadata = MetaData()

    # Reflect all tables (NOT views)
    with engine.connect() as conn:
        # Get only tables, exclude views
        result = conn.execute(text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
            AND table_name != 'alembic_version'
        """))
        tables = [row[0] for row in result]

    # Reflect tables
    metadata.reflect(engine, only=tables)

    print("# Tables found:", tables)
    print("# Use this to create squashed migration")

    for table in metadata.sorted_tables:
        print(f"\n# Table: {table.name}")
        print(f"op.create_table('{table.name}',")
        for column in table.columns:
            print(f"    sa.Column('{column.name}', {column.type}, nullable={column.nullable}),")
        print(")")

        # Indexes
        for index in table.indexes:
            print(f"op.create_index('{index.name}', '{table.name}', {list(index.columns.keys())})")

if __name__ == "__main__":
    export_schema()
```

### Step 3: Create Squashed Migration
```python
# backend/alembic/versions/000_complete_schema.py
"""Complete schema - squashed from all previous migrations

Revision ID: 000_complete_schema
Revises:
Create Date: 2025-09-25

This is the complete database schema, squashed from migrations:
- 001_initial_complete
- 26ebdc5e2006_add_system_logs_table
- c10edba96f55_add_gene_annotation_tables
- 98531cf3dc79_add_user_authentication_fields
- 0801ee5fb7f9_add_pubtator_pmids_index
- fix_gene_staging_cols
- 86bdb75bc293_add_string_ppi_percentiles_view

NOTE: Views are NOT included - they are managed by app/db/views.py
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '000_complete_schema'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Core tables (order matters for foreign keys)

    # 1. Users table
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('is_admin', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_index('ix_users_id', 'users', ['id'])
    op.create_index('ix_users_email', 'users', ['email'])

    # 2. Genes table (primary entity)
    op.create_table('genes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('hgnc_id', sa.String(50), nullable=True),
        sa.Column('approved_symbol', sa.String(100), nullable=False),
        sa.Column('aliases', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('hgnc_id'),
        sa.UniqueConstraint('approved_symbol')
    )
    op.create_index('ix_genes_id', 'genes', ['id'])
    op.create_index('ix_genes_hgnc_id', 'genes', ['hgnc_id'])
    op.create_index('ix_genes_approved_symbol', 'genes', ['approved_symbol'])

    # [Continue with all other tables in dependency order...]

def downgrade():
    # Drop all tables in reverse order
    op.drop_table('users')
    op.drop_table('genes')
    # [etc...]
```

### Step 4: Migration Execution

#### 4.1 Stop All Services
```bash
make hybrid-down
# Verify stopped
docker ps
```

#### 4.2 Create Test Database Copy
```bash
# Create test database
docker exec -it kidney-genetics-db_postgres_1 psql -U postgres -c "CREATE DATABASE kidney_test WITH TEMPLATE kidney_genetics_db"

# Test migration on copy first
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/kidney_test uv run alembic upgrade head
```

#### 4.3 Execute Squash (After Test Success)
```bash
# Clear migration history
uv run python -c "
from sqlalchemy import create_engine, text
from app.core.config import settings
engine = create_engine(settings.DATABASE_URL)
with engine.begin() as conn:
    # Store current schema version
    result = conn.execute(text('SELECT version_num FROM alembic_version'))
    current = result.scalar()
    print(f'Current version: {current}')

    # Clear version table
    conn.execute(text('TRUNCATE alembic_version'))

    # Set to new squashed version
    conn.execute(text(\"INSERT INTO alembic_version VALUES ('000_complete_schema')\"))
    print('Migration table updated')
"

# Archive old migrations
cd backend/alembic/versions
mkdir -p archived_$(date +%Y%m%d)
mv *.py archived_$(date +%Y%m%d)/
# Copy back the new squashed migration
cp /tmp/000_complete_schema.py .
```

#### 4.4 Recreate Views
```bash
# Views are NOT in migrations - recreate them
uv run python -c "
from app.db.views import refresh_all_views
from app.core.database import SessionLocal
db = SessionLocal()
refresh_all_views(db)
db.close()
print('All views recreated')
"
```

#### 4.5 Validation
```bash
# Check schema
uv run alembic check  # Should show no differences

# Verify data
uv run python -c "
from app.core.database import SessionLocal
from app.models import Gene, User, GeneAnnotation
db = SessionLocal()
print(f'Genes: {db.query(Gene).count()}')
print(f'Users: {db.query(User).count()}')
print(f'Annotations: {db.query(GeneAnnotation).count()}')
db.close()
"

# Test API
curl http://localhost:8000/api/genes/?page[number]=1
```

#### 4.6 Start Services
```bash
make hybrid-up
make backend
make frontend
```

### Step 5: Cleanup (After Verification)
```bash
# After 1 week of stable operation
rm -rf backend/alembic/versions/archived_*

# Drop test database
docker exec kidney-genetics-db_postgres_1 psql -U postgres -c "DROP DATABASE kidney_test"
```

## 🚨 Rollback Plan
If anything goes wrong:
```bash
# Stop everything
make hybrid-down

# Restore from backup
docker exec -i kidney-genetics-db_postgres_1 psql -U postgres kidney_genetics_db < backups/$(date +%Y%m%d)/full_backup.sql

# Reset migration state
uv run alembic stamp 86bdb75bc293  # Last known good migration

# Restore old migration files
cp -r backend/alembic/versions/archived_*/*.py backend/alembic/versions/

# Start services
make hybrid-up
```

## Success Criteria
- [ ] All 571+ genes present
- [ ] All user accounts work
- [ ] All annotations intact
- [ ] API returns data
- [ ] Admin panel functional
- [ ] Views display correctly
- [ ] No errors in logs
- [ ] `alembic check` shows no differences