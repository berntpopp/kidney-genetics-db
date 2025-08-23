# Static Ingestion System Refactoring Plan

## Executive Summary

This document outlines a surgical refactoring to eliminate the complex and failing "static ingestion" system, replacing it with a unified "hybrid" source pattern. This will fix the evidence aggregation bug for Diagnostic Panels and Literature sources while dramatically simplifying the codebase.

## Current Problems

1. **Over-engineered Architecture**: Three separate database tables (`static_sources`, `static_evidence_uploads`, `static_source_audit`) for what should be simple file ingestion
2. **Evidence Aggregation Bug**: Multiple uploads for the same source create duplicate evidence records instead of merging them
3. **Complex Processing Logic**: 959 lines of complex batch normalization and chunked processing in `StaticContentProcessor`
4. **Inconsistent Patterns**: Static sources use a completely different pattern than automated pipeline sources
5. **View Complexity**: Database views need special handling for `static_*` source naming

## Proposed Solution

### Core Strategy

Transform "static" sources into "hybrid" sources that:
- Inherit from `UnifiedDataSource` base class (consistent with automated sources)
- Handle file uploads through simple API endpoints
- Perform in-memory aggregation before database writes
- Use the same evidence storage pattern as automated sources

### Key Benefits

- **Consistency**: All sources use the same base class and patterns
- **Simplicity**: Remove 3 database tables and ~1,500 lines of code
- **Reliability**: Fix aggregation bug through proper merge logic
- **Maintainability**: Single pattern for all data sources

## Implementation Plan

### Phase 1: Create Hybrid Source Classes

#### 1.1 DiagnosticPanelsSource

Create `backend/app/pipeline/sources/unified/diagnostic_panels.py`:

```python
import logging
from typing import Any
import pandas as pd
from io import BytesIO
from sqlalchemy.orm import Session
from collections import defaultdict
import json

from .base import UnifiedDataSource
from app.core.progress_tracker import ProgressTracker
from app.models.gene import Gene, GeneEvidence

logger = logging.getLogger(__name__)

class DiagnosticPanelsSource(UnifiedDataSource):
    """
    Hybrid data source for commercial diagnostic panels.
    Accepts file uploads and aggregates panel/provider information.
    """
    
    @property
    def source_name(self) -> str:
        return "DiagnosticPanels"

    @property
    def namespace(self) -> str:
        return "diagnosticpanels"

    def _get_default_ttl(self) -> int:
        # Manual uploads, cache indefinitely
        return 86400 * 365

    async def fetch_raw_data(self, file_content: bytes, file_type: str, provider_name: str) -> pd.DataFrame:
        """Parse uploaded file and inject provider metadata."""
        logger.info(f"Processing {file_type} file for provider: {provider_name}")
        
        if file_type == 'json':
            data = json.loads(file_content)
            # Handle scraper output format
            if isinstance(data, dict) and 'genes' in data:
                gene_list = data['genes']
            elif isinstance(data, list):
                gene_list = data
            else:
                raise ValueError(f"Invalid JSON structure. Expected 'genes' array or list.")
            df = pd.DataFrame(gene_list)
        elif file_type in ['csv', 'tsv']:
            sep = '\t' if file_type == 'tsv' else ','
            df = pd.read_csv(BytesIO(file_content), sep=sep)
        else:  # Excel
            df = pd.read_excel(BytesIO(file_content))
        
        # Inject provider name for aggregation
        df['provider'] = provider_name
        return df

    async def process_data(self, df: pd.DataFrame) -> dict[str, Any]:
        """Aggregate panel and provider data by gene."""
        gene_data = defaultdict(lambda: {
            "panels": set(),
            "providers": set(),
            "confidence_scores": []
        })
        
        for _, row in df.iterrows():
            # Extract gene symbol
            symbol = row.get("symbol") or row.get("gene_symbol") or row.get("gene")
            if not symbol or pd.isna(symbol):
                continue
            
            symbol = str(symbol).strip().upper()
            
            # Aggregate panels
            if "panels" in row:
                panels = row["panels"]
                if isinstance(panels, str):
                    panels = [panels]
                elif pd.notna(panels):
                    panels = list(panels) if hasattr(panels, '__iter__') else [panels]
                else:
                    panels = []
                gene_data[symbol]["panels"].update(str(p) for p in panels if p)
            
            # Track provider
            if "provider" in row and pd.notna(row["provider"]):
                gene_data[symbol]["providers"].add(row["provider"])
            
            # Collect confidence scores
            if "confidence" in row and pd.notna(row["confidence"]):
                gene_data[symbol]["confidence_scores"].append(row["confidence"])

        # Convert to serializable format
        result = {}
        for symbol, data in gene_data.items():
            # Calculate aggregate confidence
            confidence_scores = data["confidence_scores"]
            if confidence_scores:
                # Use highest confidence
                confidence_map = {"high": 3, "medium": 2, "low": 1}
                max_conf = max(confidence_scores, 
                             key=lambda x: confidence_map.get(str(x).lower(), 0))
                aggregate_confidence = max_conf
            else:
                aggregate_confidence = "medium"
            
            result[symbol] = {
                "panels": sorted(list(data["panels"])),
                "providers": sorted(list(data["providers"])),
                "confidence": aggregate_confidence,
                "panel_count": len(data["panels"]),
                "provider_count": len(data["providers"])
            }
        
        return result

    async def store_evidence(
        self, 
        db: Session, 
        gene_data: dict[str, Any], 
        source_detail: str | None = None
    ) -> None:
        """
        Store evidence with MERGE semantics for hybrid sources.
        This is the core fix for the aggregation problem.
        """
        if not gene_data:
            return

        # Get all gene IDs
        gene_symbols = list(gene_data.keys())
        gene_map = {
            g.approved_symbol: g.id 
            for g in db.query(Gene).filter(Gene.approved_symbol.in_(gene_symbols))
        }
        
        # Get existing evidence for these genes
        existing_evidence = {
            e.gene_id: e 
            for e in db.query(GeneEvidence).filter(
                GeneEvidence.gene_id.in_(gene_map.values()),
                GeneEvidence.source_name == self.source_name
            )
        }

        for symbol, data in gene_data.items():
            gene_id = gene_map.get(symbol)
            if not gene_id:
                logger.warning(f"Gene {symbol} not found in database")
                continue

            if gene_id in existing_evidence:
                # MERGE: Update existing evidence
                record = existing_evidence[gene_id]
                current_data = record.evidence_data or {}
                
                # Merge panels
                current_panels = set(current_data.get("panels", []))
                current_panels.update(data["panels"])
                
                # Merge providers
                current_providers = set(current_data.get("providers", []))
                current_providers.update(data["providers"])
                
                # Update evidence
                record.evidence_data = {
                    "panels": sorted(list(current_panels)),
                    "providers": sorted(list(current_providers)),
                    "confidence": data.get("confidence", "medium"),
                    "panel_count": len(current_panels),
                    "provider_count": len(current_providers)
                }
                record.source_detail = f"{len(current_providers)} providers, {len(current_panels)} panels"
                record.updated_at = datetime.utcnow()
                
                logger.info(f"Merged evidence for {symbol}: {len(current_panels)} panels from {len(current_providers)} providers")
            else:
                # CREATE: New evidence record
                record = GeneEvidence(
                    gene_id=gene_id,
                    source_name=self.source_name,
                    source_detail=f"{data['provider_count']} providers, {data['panel_count']} panels",
                    evidence_data=data
                )
                db.add(record)
                logger.info(f"Created evidence for {symbol}: {data['panel_count']} panels from {data['provider_count']} providers")
        
        db.commit()

    def is_kidney_related(self, record: dict[str, Any]) -> bool:
        # Manual curation implies kidney relevance
        return True
```

#### 1.2 LiteratureSource

Create `backend/app/pipeline/sources/unified/literature.py`:

```python
import logging
from typing import Any
import pandas as pd
from io import BytesIO
from sqlalchemy.orm import Session
from collections import defaultdict
import json
from datetime import datetime

from .base import UnifiedDataSource
from app.models.gene import Gene, GeneEvidence

logger = logging.getLogger(__name__)

class LiteratureSource(UnifiedDataSource):
    """
    Hybrid data source for literature references.
    Accepts file uploads and aggregates publication data.
    """
    
    @property
    def source_name(self) -> str:
        return "Literature"

    @property
    def namespace(self) -> str:
        return "literature"

    def _get_default_ttl(self) -> int:
        # Manual uploads, cache indefinitely
        return 86400 * 365

    async def fetch_raw_data(self, file_content: bytes, file_type: str, source_name: str) -> pd.DataFrame:
        """Parse uploaded literature file."""
        logger.info(f"Processing {file_type} literature file from: {source_name}")
        
        if file_type == 'json':
            data = json.loads(file_content)
            if isinstance(data, dict) and 'references' in data:
                ref_list = data['references']
            elif isinstance(data, list):
                ref_list = data
            else:
                raise ValueError("Invalid JSON structure for literature data")
            df = pd.DataFrame(ref_list)
        elif file_type in ['csv', 'tsv']:
            sep = '\t' if file_type == 'tsv' else ','
            df = pd.read_csv(BytesIO(file_content), sep=sep)
        else:
            df = pd.read_excel(BytesIO(file_content))
        
        # Add source tracking
        df['source'] = source_name
        return df

    async def process_data(self, df: pd.DataFrame) -> dict[str, Any]:
        """Aggregate literature references by gene."""
        gene_data = defaultdict(lambda: {
            "references": [],
            "pmids": set(),
            "sources": set()
        })
        
        for _, row in df.iterrows():
            symbol = row.get("gene_symbol") or row.get("symbol") or row.get("gene")
            if not symbol or pd.isna(symbol):
                continue
            
            symbol = str(symbol).strip().upper()
            
            # Create reference object
            ref = {
                "pmid": row.get("pmid"),
                "title": row.get("title"),
                "authors": row.get("authors"),
                "year": row.get("year"),
                "journal": row.get("journal"),
                "evidence_type": row.get("evidence_type", "association")
            }
            
            # Only add if has PMID
            if ref["pmid"] and pd.notna(ref["pmid"]):
                pmid = str(ref["pmid"])
                if pmid not in gene_data[symbol]["pmids"]:
                    gene_data[symbol]["references"].append(ref)
                    gene_data[symbol]["pmids"].add(pmid)
            
            # Track source
            if "source" in row and pd.notna(row["source"]):
                gene_data[symbol]["sources"].add(row["source"])

        # Convert to serializable format
        result = {}
        for symbol, data in gene_data.items():
            result[symbol] = {
                "references": data["references"],
                "publication_count": len(data["pmids"]),
                "sources": sorted(list(data["sources"]))
            }
        
        return result

    async def store_evidence(
        self, 
        db: Session, 
        gene_data: dict[str, Any], 
        source_detail: str | None = None
    ) -> None:
        """Store literature evidence with merge semantics."""
        if not gene_data:
            return

        gene_symbols = list(gene_data.keys())
        gene_map = {
            g.approved_symbol: g.id 
            for g in db.query(Gene).filter(Gene.approved_symbol.in_(gene_symbols))
        }
        
        existing_evidence = {
            e.gene_id: e 
            for e in db.query(GeneEvidence).filter(
                GeneEvidence.gene_id.in_(gene_map.values()),
                GeneEvidence.source_name == self.source_name
            )
        }

        for symbol, data in gene_data.items():
            gene_id = gene_map.get(symbol)
            if not gene_id:
                continue

            if gene_id in existing_evidence:
                # Merge with existing
                record = existing_evidence[gene_id]
                current_data = record.evidence_data or {}
                
                # Merge references by PMID
                current_refs = {r.get("pmid"): r for r in current_data.get("references", [])}
                for new_ref in data["references"]:
                    if new_ref.get("pmid"):
                        current_refs[new_ref["pmid"]] = new_ref
                
                # Update evidence
                record.evidence_data = {
                    "references": list(current_refs.values()),
                    "publication_count": len(current_refs),
                    "sources": sorted(list(set(current_data.get("sources", [])) | set(data["sources"])))
                }
                record.source_detail = f"{len(current_refs)} publications"
                record.updated_at = datetime.utcnow()
            else:
                # Create new
                record = GeneEvidence(
                    gene_id=gene_id,
                    source_name=self.source_name,
                    source_detail=f"{data['publication_count']} publications",
                    evidence_data=data
                )
                db.add(record)
        
        db.commit()

    def is_kidney_related(self, record: dict[str, Any]) -> bool:
        return True  # Manually curated
```

### Phase 2: Update Source Registry

#### 2.1 Register New Sources

Update `backend/app/pipeline/sources/unified/__init__.py`:

```python
from .base import UnifiedDataSource
from .clingen import ClinGenUnifiedSource
from .gencc import GenCCUnifiedSource
from .hpo import HPOUnifiedSource
from .panelapp import PanelAppUnifiedSource
from .pubtator import PubTatorUnifiedSource
from .diagnostic_panels import DiagnosticPanelsSource  # NEW
from .literature import LiteratureSource  # NEW

# Source registry
SOURCE_MAP = {
    "GenCC": GenCCUnifiedSource,
    "PanelApp": PanelAppUnifiedSource,
    "PubTator": PubTatorUnifiedSource,
    "HPO": HPOUnifiedSource,
    "ClinGen": ClinGenUnifiedSource,
    "DiagnosticPanels": DiagnosticPanelsSource,  # NEW
    "Literature": LiteratureSource,  # NEW
}

def get_unified_source(source_name: str, **kwargs) -> UnifiedDataSource:
    """Factory function to get source instance."""
    source_class = SOURCE_MAP.get(source_name)
    if not source_class:
        raise ValueError(f"Unknown source: {source_name}")
    return source_class(**kwargs)

__all__ = [
    "UnifiedDataSource",
    "SOURCE_MAP",
    "get_unified_source",
    # ... existing exports ...
    "DiagnosticPanelsSource",
    "LiteratureSource",
]
```

### Phase 3: Create New Ingestion API

#### 3.1 Simple Upload Endpoint

Replace `backend/app/api/endpoints/ingestion.py`:

```python
"""
Hybrid source file upload API.
Simplified replacement for complex static ingestion system.
"""
import logging
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.pipeline.sources.unified import get_unified_source

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/sources", tags=["Hybrid Sources"])

# Define which sources support file uploads
UPLOAD_SOURCES = {"DiagnosticPanels", "Literature"}

@router.post("/{source_name}/upload")
async def upload_evidence_file(
    source_name: str,
    file: UploadFile = File(...),
    provider_name: str | None = None,
    db: Session = Depends(get_db)
):
    """
    Upload evidence file for hybrid sources.
    
    Args:
        source_name: Name of the source (DiagnosticPanels or Literature)
        file: The file to upload (JSON, CSV, TSV, or Excel)
        provider_name: Optional provider/source identifier
        db: Database session
    
    Returns:
        Upload status and statistics
    """
    # Validate source
    if source_name not in UPLOAD_SOURCES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source '{source_name}' does not support file uploads. Available: {UPLOAD_SOURCES}"
        )
    
    # Get source processor
    try:
        source = get_unified_source(source_name, db_session=db)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    
    # Determine file type
    file_type = file.filename.split('.')[-1].lower() if file.filename else 'json'
    if file_type not in ['json', 'csv', 'tsv', 'xlsx', 'xls']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {file_type}"
        )
    
    # Use filename as provider if not specified
    if not provider_name:
        provider_name = file.filename.split('.')[0] if file.filename else 'unknown'
    
    try:
        # Read file content
        file_content = await file.read()
        
        # Process through source pipeline
        raw_data = await source.fetch_raw_data(file_content, file_type, provider_name)
        processed_data = await source.process_data(raw_data)
        
        # Store with merge semantics
        await source.store_evidence(db, processed_data, provider_name)
        
        # Return statistics
        return {
            "status": "success",
            "source": source_name,
            "provider": provider_name,
            "filename": file.filename,
            "genes_processed": len(processed_data),
            "message": f"Successfully processed and merged evidence for {len(processed_data)} genes"
        }
        
    except Exception as e:
        logger.error(f"Failed to process upload for {source_name}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Processing failed: {str(e)}"
        )

@router.get("/{source_name}/status")
async def get_source_status(
    source_name: str,
    db: Session = Depends(get_db)
):
    """Get status and statistics for a hybrid source."""
    if source_name not in UPLOAD_SOURCES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source '{source_name}' not found"
        )
    
    from app.models.gene import GeneEvidence
    
    # Get evidence count
    evidence_count = db.query(GeneEvidence).filter(
        GeneEvidence.source_name == source_name
    ).count()
    
    # Get unique genes
    unique_genes = db.query(GeneEvidence.gene_id).filter(
        GeneEvidence.source_name == source_name
    ).distinct().count()
    
    return {
        "source": source_name,
        "evidence_records": evidence_count,
        "unique_genes": unique_genes,
        "supports_upload": True
    }
```

### Phase 4: Database Migration

#### 4.1 Update Views

Create migration `backend/alembic/versions/003_update_views_for_hybrid_sources.py`:

```python
"""Update views for hybrid sources

Revision ID: 003
Revises: 002
"""
from alembic import op
from app.db.replaceable_objects import ReplaceableObject

def upgrade() -> None:
    # Update evidence_source_counts view to handle new source names
    op.execute("""
        CREATE OR REPLACE VIEW evidence_source_counts AS
        SELECT ge.id AS evidence_id,
            ge.gene_id,
            g.approved_symbol,
            ge.source_name,
            CASE ge.source_name
                WHEN 'PanelApp' THEN COALESCE(jsonb_array_length(ge.evidence_data -> 'panels'), 0)::bigint
                WHEN 'HPO' THEN (COALESCE(jsonb_array_length(ge.evidence_data -> 'hpo_terms'), 0) + 
                                COALESCE(jsonb_array_length(ge.evidence_data -> 'diseases'), 0))::bigint
                WHEN 'PubTator' THEN COALESCE((ge.evidence_data ->> 'publication_count')::integer, 
                                             jsonb_array_length(ge.evidence_data -> 'pmids'))::bigint
                WHEN 'Literature' THEN COALESCE((ge.evidence_data ->> 'publication_count')::integer, 
                                              jsonb_array_length(ge.evidence_data -> 'references'))::bigint
                WHEN 'DiagnosticPanels' THEN COALESCE((ge.evidence_data ->> 'panel_count')::integer, 
                                                     jsonb_array_length(ge.evidence_data -> 'panels'))::bigint
                ELSE 0::bigint
            END AS source_count
        FROM gene_evidence ge
        JOIN genes g ON ge.gene_id = g.id
    """)

def downgrade() -> None:
    # Restore original view
    pass
```

#### 4.2 Remove Old Tables

Create migration `backend/alembic/versions/004_remove_static_ingestion_tables.py`:

```python
"""Remove static ingestion tables

Revision ID: 004
Revises: 003
"""
from alembic import op

def upgrade() -> None:
    # Drop tables in correct order (dependencies first)
    op.drop_table('static_source_audit')
    op.drop_table('static_evidence_uploads')
    op.drop_table('static_sources')
    
    # Log completion
    print("Successfully removed static ingestion tables")

def downgrade() -> None:
    # Not implementing downgrade - fresh database preferred
    raise NotImplementedError("Downgrade not supported for this migration")
```

### Phase 5: Code Cleanup

#### 5.1 Delete Obsolete Files

Remove the following files:
- `backend/app/core/static_ingestion.py` (959 lines)
- `backend/app/models/static_ingestion.py` (82 lines)
- `backend/app/schemas/ingestion.py` (146 lines)

#### 5.2 Update Imports

Remove any imports of the deleted modules from:
- `backend/app/models/__init__.py`
- `backend/app/schemas/__init__.py`
- `backend/app/api/endpoints/__init__.py`

### Phase 6: Testing

#### 6.1 Unit Tests

Create `backend/tests/test_hybrid_sources.py`:

```python
import pytest
from app.pipeline.sources.unified import DiagnosticPanelsSource, LiteratureSource

@pytest.mark.asyncio
async def test_diagnostic_panels_aggregation(db_session):
    """Test that multiple uploads merge correctly."""
    source = DiagnosticPanelsSource(db_session=db_session)
    
    # First upload
    data1 = await source.process_data(pd.DataFrame([
        {"symbol": "PKD1", "panels": ["panel1"], "provider": "mayo"}
    ]))
    await source.store_evidence(db_session, data1, "mayo")
    
    # Second upload - should merge
    data2 = await source.process_data(pd.DataFrame([
        {"symbol": "PKD1", "panels": ["panel2"], "provider": "invitae"}
    ]))
    await source.store_evidence(db_session, data2, "invitae")
    
    # Verify merged evidence
    from app.models.gene import GeneEvidence
    evidence = db_session.query(GeneEvidence).filter(
        GeneEvidence.source_name == "DiagnosticPanels"
    ).first()
    
    assert evidence is not None
    assert len(evidence.evidence_data["panels"]) == 2
    assert len(evidence.evidence_data["providers"]) == 2
    assert "mayo" in evidence.evidence_data["providers"]
    assert "invitae" in evidence.evidence_data["providers"]

@pytest.mark.asyncio
async def test_literature_deduplication(db_session):
    """Test that duplicate PMIDs are not added."""
    source = LiteratureSource(db_session=db_session)
    
    # Upload with duplicate PMID
    data = await source.process_data(pd.DataFrame([
        {"gene_symbol": "PKD1", "pmid": "12345", "title": "Title 1"},
        {"gene_symbol": "PKD1", "pmid": "12345", "title": "Title 2"}
    ]))
    
    assert len(data["PKD1"]["references"]) == 1
    assert data["PKD1"]["publication_count"] == 1
```

#### 6.2 Integration Tests

```python
from fastapi.testclient import TestClient

def test_upload_diagnostic_panel(client: TestClient):
    """Test file upload endpoint."""
    response = client.post(
        "/api/sources/DiagnosticPanels/upload",
        files={"file": ("mayo.json", b'{"genes": [{"symbol": "PKD1", "panels": ["panel1"]}]}', "application/json")},
        data={"provider_name": "mayo_clinic"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["genes_processed"] == 1

def test_merge_behavior(client: TestClient):
    """Test that multiple uploads merge correctly."""
    # First upload
    client.post(
        "/api/sources/DiagnosticPanels/upload",
        files={"file": ("mayo.json", b'{"genes": [{"symbol": "HNF1B", "panels": ["panel1"]}]}', "application/json")}
    )
    
    # Second upload - should merge
    response = client.post(
        "/api/sources/DiagnosticPanels/upload",
        files={"file": ("invitae.json", b'{"genes": [{"symbol": "HNF1B", "panels": ["panel2"]}]}', "application/json")}
    )
    
    assert response.status_code == 200
    # Verify in database that only one evidence record exists with merged data
```

## Migration Steps

### Pre-Migration Checklist
- [ ] Backup database
- [ ] Document current static source configurations
- [ ] Export any important audit logs
- [ ] Test in development environment

### Migration Execution

1. **Deploy New Code**
   ```bash
   git checkout feature/hybrid-sources
   git merge main
   ```

2. **Run Migrations**
   ```bash
   cd backend
   alembic upgrade head
   ```

3. **Verify Migration**
   ```sql
   -- Check tables are removed
   SELECT table_name FROM information_schema.tables 
   WHERE table_schema = 'public' 
   AND table_name LIKE 'static_%';
   
   -- Check new evidence
   SELECT source_name, COUNT(*) 
   FROM gene_evidence 
   WHERE source_name IN ('DiagnosticPanels', 'Literature')
   GROUP BY source_name;
   ```

4. **Re-upload Data**
   ```bash
   # Re-upload diagnostic panels
   curl -X POST http://localhost:8000/api/sources/DiagnosticPanels/upload \
     -F "file=@mayo_clinic.json" \
     -F "provider_name=mayo_clinic"
   
   curl -X POST http://localhost:8000/api/sources/DiagnosticPanels/upload \
     -F "file=@invitae.json" \
     -F "provider_name=invitae"
   ```

5. **Verify Aggregation**
   ```sql
   -- Check for proper merging
   SELECT gene_id, evidence_data
   FROM gene_evidence
   WHERE source_name = 'DiagnosticPanels'
   AND evidence_data->>'provider_count'::text::int > 1;
   ```

### Post-Migration Validation

1. **API Testing**
   - Upload test files for each source type
   - Verify merge behavior with duplicate genes
   - Check error handling for invalid files

2. **Database Validation**
   - Verify no duplicate evidence records per gene/source
   - Check evidence_data structure is correct
   - Validate views return expected counts

3. **Performance Testing**
   - Upload large files (>1000 genes)
   - Verify response times are acceptable
   - Check database query performance

## Rollback Plan

If issues arise:

1. **Restore Database**
   ```bash
   pg_restore -d kidney_genetics backup.sql
   ```

2. **Revert Code**
   ```bash
   git revert HEAD
   git push
   ```

3. **Restore Old Tables** (if needed)
   ```sql
   -- Re-create tables from backup schema
   ```

## Success Metrics

- **Code Reduction**: ~1,500 lines removed
- **Table Reduction**: 3 tables eliminated
- **Bug Fix**: Evidence properly aggregates across uploads
- **Consistency**: All sources use same base pattern
- **Simplicity**: Single API endpoint for uploads
- **Performance**: <2 second response for 1000-gene uploads

## Future Enhancements

1. **Batch Upload API**: Accept multiple files in single request
2. **Validation Rules**: Add configurable validation per source
3. **Upload History**: Track uploads in cache or lightweight table
4. **Async Processing**: Use background tasks for large files
5. **S3 Integration**: Direct upload from S3 buckets

## Conclusion

This refactoring eliminates unnecessary complexity while fixing the critical aggregation bug. The unified pattern makes the system more maintainable and extensible. The implementation is straightforward and can be completed in 1-2 days with proper testing.