# CalVer Data Releases with Temporal Database Versioning

**GitHub Issue**: #24
**Status**: Planning
**Priority**: High (Research Reproducibility)
**Effort**: 5-7 days

## Problem Statement

Need mechanism to:
- Create citable point-in-time snapshots with DOIs
- Enable research reproducibility
- View historical data in web UI
- Track changes between releases

**Current**: Only "latest" data available, no versioning.

## Proposed Solution

**CalVer + Valid Time Ranges** (SQL:2011 temporal pattern)

### Key Benefits

- **91% storage savings** - Only changed genes create new rows
- **<50ms queries** - GiST indexes on temporal ranges
- **Native PostgreSQL** - No extensions required
- **Simple to implement** - Just 2 columns + 1 index + 1 view

### Versioning Format

**CalVer `YYYY.MM`** (e.g., 2025.01, 2025.04, 2025.07)

Examples:
- `2025.01` - January 2025 release
- `2025.04` - April 2025 release
- `2025.10` - October 2025 release

## How It Works

### Publishing a Release

```
1. Admin creates draft release (e.g., "2025.10")
2. On publish: System closes current time ranges
   UPDATE genes
   SET valid_to = '2025-10-15 00:00:00'::timestamptz
   WHERE valid_to = 'infinity'::timestamptz
3. All current rows get closing timestamp
4. Export JSON with temporal query
5. Calculate SHA256 checksum
6. Mark as published
```

### After Publish

- New changes automatically have `valid_from = NOW()` and `valid_to = 'infinity'`
- Old data remains queryable by timestamp
- Only changed genes create new rows (storage efficient)

## Database Schema

### Migration: Add Temporal Columns

```sql
-- File: backend/alembic/versions/XXXX_add_temporal_versioning.py

"""Add temporal versioning to genes table

Revision ID: temporal_001
Revises: previous_revision
Create Date: 2025-10-03
"""

def upgrade():
    # Add temporal columns
    op.add_column('genes',
        sa.Column('valid_from', sa.TIMESTAMP(timezone=True),
                  nullable=False, server_default=sa.text('NOW()')))

    op.add_column('genes',
        sa.Column('valid_to', sa.TIMESTAMP(timezone=True),
                  nullable=False, server_default=sa.text("'infinity'::timestamptz")))

    # Create GiST index for temporal queries
    op.execute("""
        CREATE INDEX idx_genes_valid_time ON genes
        USING gist (tstzrange(valid_from, valid_to));
    """)

    # Create view for current genes
    op.execute("""
        CREATE VIEW genes_current AS
        SELECT * FROM genes
        WHERE valid_to = 'infinity'::timestamptz;
    """)

def downgrade():
    op.execute("DROP VIEW IF EXISTS genes_current;")
    op.execute("DROP INDEX IF EXISTS idx_genes_valid_time;")
    op.drop_column('genes', 'valid_to')
    op.drop_column('genes', 'valid_from')
```

###Query Examples

```sql
-- Current genes (fast - uses view)
SELECT * FROM genes_current;

-- Specific release (fast - GiST indexed)
SELECT * FROM genes
WHERE tstzrange(valid_from, valid_to) @> '2025-10-15'::timestamptz;

-- All versions of a gene (audit trail)
SELECT approved_symbol, valid_from, valid_to, classification
FROM genes
WHERE hgnc_id = 'HGNC:9008'
ORDER BY valid_from DESC;

-- Changed genes between two releases
SELECT g1.approved_symbol
FROM genes g1
JOIN genes g2 ON g1.hgnc_id = g2.hgnc_id
WHERE tstzrange(g1.valid_from, g1.valid_to) @> '2025-10-15'::timestamptz
  AND tstzrange(g2.valid_from, g2.valid_to) @> '2025-07-15'::timestamptz
  AND g1.classification != g2.classification;
```

## Backend Implementation

### 1. Data Release Model

```python
# backend/app/models/data_release.py

from sqlalchemy import Column, String, Text, DateTime, Boolean, Integer
from sqlalchemy.sql import func
from app.db.database import Base

class DataRelease(Base):
    __tablename__ = "data_releases"

    id = Column(Integer, primary_key=True)
    version = Column(String(20), unique=True, nullable=False)  # "2025.10"
    release_date = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(20), default="draft")  # draft, published

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    published_at = Column(DateTime(timezone=True), nullable=True)
    published_by_id = Column(Integer, ForeignKey("users.id"))

    # Statistics
    gene_count = Column(Integer, nullable=True)
    total_evidence_count = Column(Integer, nullable=True)

    # Export
    export_file_path = Column(String(500), nullable=True)
    export_checksum = Column(String(64), nullable=True)  # SHA256

    # Citation
    doi = Column(String(100), nullable=True)  # Optional Zenodo DOI
    citation_text = Column(Text, nullable=True)

    # Notes
    release_notes = Column(Text, nullable=True)
```

### 2. Release Service

```python
# backend/app/services/release_service.py

from sqlalchemy.orm import Session
from sqlalchemy import text
import json
import hashlib
from pathlib import Path
from datetime import datetime

class ReleaseService:
    def __init__(self, db: Session):
        self.db = db

    async def create_release(self, version: str, user_id: int) -> DataRelease:
        """Create a draft release"""
        release = DataRelease(
            version=version,
            status="draft",
            created_by_id=user_id
        )
        self.db.add(release)
        self.db.commit()
        return release

    async def publish_release(self, release_id: int, user_id: int):
        """Publish a release - close temporal ranges"""
        release = self.db.query(DataRelease).get(release_id)

        if release.status == "published":
            raise ValueError("Release already published")

        # Close current time ranges
        publish_time = datetime.now()
        self.db.execute(text("""
            UPDATE genes
            SET valid_to = :publish_time
            WHERE valid_to = 'infinity'::timestamptz
        """), {"publish_time": publish_time})

        # Export data
        export_path = await self._export_release(release.version, publish_time)
        checksum = self._calculate_checksum(export_path)

        # Update release record
        release.status = "published"
        release.published_at = publish_time
        release.published_by_id = user_id
        release.export_file_path = str(export_path)
        release.export_checksum = checksum
        release.gene_count = self._count_genes(publish_time)

        self.db.commit()
        return release

    async def _export_release(self, version: str, timestamp):
        """Export genes to JSON file"""
        export_dir = Path("exports")
        export_dir.mkdir(exist_ok=True)
        export_file = export_dir / f"kidney-genetics-db_{version}.json"

        # Query genes at specific timestamp
        genes = self.db.execute(text("""
            SELECT
                approved_symbol,
                hgnc_id,
                classification,
                evidence_score,
                annotations
            FROM genes
            WHERE tstzrange(valid_from, valid_to) @> :timestamp
            ORDER BY approved_symbol
        """), {"timestamp": timestamp}).fetchall()

        # Build export structure
        export_data = {
            "version": version,
            "release_date": timestamp.isoformat(),
            "gene_count": len(genes),
            "genes": [dict(row._mapping) for row in genes]
        }

        # Write to file
        with open(export_file, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)

        return export_file

    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum"""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def _count_genes(self, timestamp) -> int:
        """Count genes at specific timestamp"""
        result = self.db.execute(text("""
            SELECT COUNT(*)
            FROM genes
            WHERE tstzrange(valid_from, valid_to) @> :timestamp
        """), {"timestamp": timestamp})
        return result.scalar()
```

## API Endpoints

```python
# backend/app/api/endpoints/releases.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.auth import get_current_admin_user
from app.services.release_service import ReleaseService

router = APIRouter()

@router.get("/releases")
async def list_releases(db: Session = Depends(get_db)):
    """List all releases"""
    return db.query(DataRelease).order_by(DataRelease.version.desc()).all()

@router.get("/releases/{version}")
async def get_release(version: str, db: Session = Depends(get_db)):
    """Get release metadata"""
    release = db.query(DataRelease).filter_by(version=version).first()
    if not release:
        raise HTTPException(404, "Release not found")
    return release

@router.get("/releases/{version}/genes")
async def get_release_genes(
    version: str,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """Get genes from specific release"""
    release = db.query(DataRelease).filter_by(version=version).first()
    if not release:
        raise HTTPException(404)

    # Query genes at release timestamp
    genes = db.execute(text("""
        SELECT * FROM genes
        WHERE tstzrange(valid_from, valid_to) @> :timestamp
        ORDER BY approved_symbol
        LIMIT :limit OFFSET :offset
    """), {
        "timestamp": release.published_at,
        "limit": limit,
        "offset": offset
    }).fetchall()

    return {
        "version": version,
        "release_date": release.published_at,
        "total": release.gene_count,
        "genes": [dict(g._mapping) for g in genes]
    }

@router.get("/releases/{version}/export")
async def download_export(version: str, db: Session = Depends(get_db)):
    """Download JSON export"""
    release = db.query(DataRelease).filter_by(version=version).first()
    if not release or not release.export_file_path:
        raise HTTPException(404)

    return FileResponse(
        release.export_file_path,
        media_type="application/json",
        filename=f"kidney-genetics-db_{version}.json"
    )

@router.post("/releases", dependencies=[Depends(get_current_admin_user)])
async def create_release(
    version: str,
    release_notes: str = "",
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """Create draft release (admin only)"""
    service = ReleaseService(db)
    return await service.create_release(version, current_user.id)

@router.post("/releases/{id}/publish", dependencies=[Depends(get_current_admin_user)])
async def publish_release(
    id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """Publish release (admin only)"""
    service = ReleaseService(db)
    return await service.publish_release(id, current_user.id)
```

## Frontend Implementation

### 1. Releases Page

```vue
<!-- frontend/src/views/ReleasesPage.vue -->
<template>
  <v-container>
    <h1 class="text-h4 mb-4">Data Releases</h1>

    <v-card v-for="release in releases" :key="release.version" class="mb-4">
      <v-card-title>
        Version {{ release.version }}
        <v-chip :color="release.status === 'published' ? 'success' : 'warning'" class="ml-2" size="small">
          {{ release.status }}
        </v-chip>
      </v-card-title>

      <v-card-text>
        <div><strong>Release Date:</strong> {{ formatDate(release.published_at) }}</div>
        <div><strong>Genes:</strong> {{ release.gene_count?.toLocaleString() }}</div>
        <div v-if="release.doi"><strong>DOI:</strong> <a :href="`https://doi.org/${release.doi}`">{{ release.doi }}</a></div>
        <div v-if="release.citation_text" class="mt-2">
          <strong>Citation:</strong>
          <code class="text-caption">{{ release.citation_text }}</code>
          <v-btn icon="mdi-content-copy" size="x-small" @click="copyCitation(release.citation_text)" />
        </div>
      </v-card-text>

      <v-card-actions>
        <v-btn :to="`/releases/${release.version}/genes`" color="primary">Browse Genes</v-btn>
        <v-btn v-if="release.export_file_path" :href="`/api/releases/${release.version}/export`" variant="outlined">
          <v-icon start>mdi-download</v-icon>
          Download JSON
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-container>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '@/services/api'

const releases = ref([])

onMounted(async () => {
  const response = await api.get('/releases')
  releases.value = response.data
})

function copyCitation(text) {
  navigator.clipboard.writeText(text)
}

function formatDate(date) {
  return date ? new Date(date).toLocaleDateString() : 'Draft'
}
</script>
```

## Optional: Zenodo DOI Integration

**Simple approach using Zenodo GitHub integration:**

1. **Tag release**: `git tag v2025.10 && git push --tags`
2. **Zenodo webhook** automatically mints DOI
3. **Store DOI** in release record via admin UI

**Alternative: Direct Zenodo API** (more complex):
- Create deposition via Zenodo API
- Upload JSON file
- Publish and get DOI
- Store in database

## Implementation Timeline

### Week 1: Database & Backend (3-4 days)
- [ ] Create migration for temporal columns
- [ ] Create GiST index
- [ ] Create genes_current view
- [ ] `DataRelease` model
- [ ] `ReleaseService` implementation
- [ ] Test temporal queries

### Week 2: API & Frontend (2-3 days)
- [ ] API endpoints for releases
- [ ] JSON export functionality
- [ ] Frontend releases list page
- [ ] Frontend release browser
- [ ] Citation display

### Week 3: Optional Enhancements (2 days)
- [ ] Zenodo integration
- [ ] Admin UI for release management
- [ ] Diff viewer between releases
- [ ] Performance testing

## Acceptance Criteria

**Database**:
- [ ] Migration adds `valid_from`, `valid_to` columns
- [ ] GiST index on `tstzrange(valid_from, valid_to)`
- [ ] `genes_current` view created
- [ ] Temporal queries <50ms (verified)

**Backend**:
- [ ] `DataRelease` model with CalVer version
- [ ] `ReleaseService.publish_release()` closes time ranges
- [ ] JSON export with temporal query
- [ ] SHA256 checksum calculation
- [ ] API endpoints functional

**Frontend**:
- [ ] Releases list page
- [ ] Release gene browser
- [ ] Citation display with copy button
- [ ] Download export button

**Performance**:
- [ ] Storage test: Only changed genes create new rows
- [ ] Query test: <50ms for temporal queries
- [ ] Export test: <5s for 1000 genes

## References

- **PostgreSQL Range Types**: https://www.postgresql.org/docs/current/rangetypes.html
- **SQL:2011 Temporal Features**: ISO/IEC 9075-2:2011
- **Ensembl Release Cycle**: https://www.ensembl.org/info/website/archives/index.html
- **UniProt Versioning**: https://www.uniprot.org/help/synchronization
- **CalVer**: https://calver.org/
- **Zenodo**: https://zenodo.org/
- **GitHub Issue**: #24
