# Ensembl & UniProt System Integration Plan

**Related Issue**: [#29 - Add gene structure and protein domain annotations](https://github.com/berntpopp/kidney-genetics-db/issues/29)
**Related Plans**:
- [gene-protein-visualization.md](./gene-protein-visualization.md)
- [visualization-integration-ux-analysis.md](./visualization-integration-ux-analysis.md)
**Date**: 2026-01-11
**Status**: Ready for Implementation
**Last Review**: 2026-01-11 (API testing verified, patterns aligned with codebase)

---

## Executive Summary

This document details how to integrate Ensembl and UniProt as new annotation sources into the existing kidney-genetics-db annotation system. The integration follows established patterns from the 8 existing annotation sources (HGNC, gnomAD, GTEx, ClinVar, HPO, MPO/MGI, STRING PPI, Descartes).

### Key Integration Points

| Component | File/Location | Changes Required |
|-----------|---------------|------------------|
| **Backend Source Classes** | `backend/app/pipeline/sources/annotations/` | Create `ensembl.py`, `uniprot.py` |
| **Configuration** | `backend/config/annotations.yaml` | Add Ensembl/UniProt config |
| **Source Registration** | `backend/app/pipeline/sources/annotations/__init__.py` | Export new classes |
| **Pipeline Integration** | `backend/app/pipeline/annotation_pipeline.py` | Register in `self.sources` dict |
| **API Endpoints** | `backend/app/api/endpoints/gene_annotations.py` | Add update task functions |
| **Admin Dashboard** | `frontend/src/views/admin/AdminAnnotations.vue` | Auto-discovered (no changes) |

---

## Current System Architecture

### Two Pipeline Systems

The codebase has TWO distinct pipeline systems:

```
┌─────────────────────────────────────────────────────────────────┐
│                    DATA INGESTION PIPELINE                       │
│           (AdminPipeline.vue - /admin/pipeline)                  │
├─────────────────────────────────────────────────────────────────┤
│  PanelApp, ClinGen, GenCC, HPO, PubTator, Literature            │
│  Purpose: Import gene-disease associations into database         │
│  Output: Populates genes, evidence tables                        │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    ANNOTATION PIPELINE                           │
│         (AdminAnnotations.vue - /admin/annotations)              │
├─────────────────────────────────────────────────────────────────┤
│  HGNC, gnomAD, GTEx, ClinVar, HPO, MPO/MGI, STRING PPI, Descartes│
│  Purpose: Enrich existing genes with external data               │
│  Output: Populates gene_annotations table (JSONB)                │
│                                                                  │
│  >>> NEW: Ensembl (gene structure), UniProt (protein domains) <<<│
└─────────────────────────────────────────────────────────────────┘
```

**Ensembl and UniProt belong in the ANNOTATION PIPELINE** because they:
- Enrich existing genes (don't create new ones)
- Store structured JSONB data in `gene_annotations`
- Are fetched on-demand or via scheduled updates
- Support batch operations for efficiency

### Existing Annotation Sources (8 Total)

| Source | Type | Update Frequency | Cache TTL | Rate Limit |
|--------|------|------------------|-----------|------------|
| HGNC | REST API | Quarterly | 90 days | 2 req/s |
| gnomAD | GraphQL | Quarterly | 90 days | 3 req/s |
| GTEx | REST API (2-step) | Quarterly | 90 days | 3 req/s |
| ClinVar | REST API (2-step) | Weekly | 7 days | 2.8 req/s |
| HPO | REST API (multi-step) | Quarterly | 90 days | 10 req/s |
| MPO/MGI | REST API (hierarchical) | Weekly | 90 days | 2 req/s |
| STRING PPI | Local files + scoring | Quarterly | 90 days | N/A |
| Descartes | CSV download | Quarterly | 90 days | N/A |

### New Sources to Add

| Source | Type | Update Frequency | Cache TTL | Rate Limit |
|--------|------|------------------|-----------|------------|
| **Ensembl** | REST POST batch | Monthly | 30 days | 15 req/s |
| **UniProt** | REST OR query | Monthly | 30 days | 5 req/s |

---

## Backend Integration

### 1. Configuration (`backend/config/annotations.yaml`)

Add to the existing configuration file:

```yaml
# Add to annotations section in annotations.yaml

ensembl:
  display_name: Ensembl
  description: Gene structure data - exons, transcripts, genomic coordinates
  base_url: https://rest.ensembl.org
  update_frequency: monthly
  is_active: true
  priority: 11  # High priority for structural data
  requests_per_second: 15.0  # Ensembl allows 15 req/s (55k/hour)
  max_retries: 5
  cache_ttl_days: 30
  use_http_cache: true
  circuit_breaker_threshold: 5
  batch_size: 500  # Safety margin (API limit: 1000)
  # Verified 2026-01-11: POST /lookup/symbol/homo_sapiens with expand=1
  # 8 genes: 5.2s, 571 genes: ~15s estimated (1 request)

uniprot:
  display_name: UniProt
  description: Protein domains and structural features
  base_url: https://rest.uniprot.org
  update_frequency: monthly
  is_active: true
  priority: 11  # High priority for structural data
  requests_per_second: 5.0
  max_retries: 5
  cache_ttl_days: 30
  use_http_cache: true
  circuit_breaker_threshold: 5
  batch_size: 100  # UniProt OR query hard limit: 100 conditions
  # Verified 2026-01-11: OR query with reviewed:true filter
  # 8 genes: 0.48s, 571 genes: ~10s (6 requests)
```

### 2. Source Classes

Create two new files following the `BaseAnnotationSource` pattern:

**File**: `backend/app/pipeline/sources/annotations/ensembl.py`

Key implementation points (see gene-protein-visualization.md for full code):
- Inherit from `BaseAnnotationSource`
- Use `@retry_with_backoff` decorator for fetch methods
- Use `SimpleRateLimiter` from `retry_utils.py` (NOT custom implementation)
- Implement `fetch_annotation(gene)` for single gene
- Implement `fetch_batch(genes)` using POST `/lookup/symbol/homo_sapiens`
- **Implement `_is_valid_annotation()`** for Ensembl-specific validation
- Use MANE Select transcripts from HGNC annotations
- Return exon structure, coordinates, transcript info

**File**: `backend/app/pipeline/sources/annotations/uniprot.py`

Key implementation points:
- Inherit from `BaseAnnotationSource`
- Use `@retry_with_backoff` decorator for fetch methods
- Use `SimpleRateLimiter` from `retry_utils.py` (NOT custom implementation)
- Implement `fetch_annotation(gene)` for single gene
- Implement `fetch_batch(genes)` using OR query with 100-gene chunks
- **Implement `_is_valid_annotation()`** for UniProt-specific validation
- **Use semaphore** to limit concurrent batch requests (like ClinVar)
- Handle empty results (NOT error key - UniProt returns `{"results": []}`)
- Return protein domains, Pfam/InterPro references

#### Required Pattern: `_is_valid_annotation()` Override

Both sources MUST implement this method (following ClinVar pattern at `clinvar.py:542-551`):

```python
# In EnsemblAnnotationSource
def _is_valid_annotation(self, annotation_data: dict) -> bool:
    """Validate Ensembl annotation data."""
    if not super()._is_valid_annotation(annotation_data):
        return False

    # Ensembl-specific: must have gene_id and exons
    required_fields = ["ensembl_id", "gene_symbol", "exons"]
    has_required = all(field in annotation_data for field in required_fields)

    # Must have at least one exon
    if has_required and annotation_data.get("exons"):
        return len(annotation_data["exons"]) > 0
    return False

# In UniProtAnnotationSource
def _is_valid_annotation(self, annotation_data: dict) -> bool:
    """Validate UniProt annotation data."""
    if not super()._is_valid_annotation(annotation_data):
        return False

    # UniProt-specific: must have accession and length
    required_fields = ["accession", "protein_name", "length"]
    return all(field in annotation_data for field in required_fields)
```

#### Required Pattern: Use SimpleRateLimiter

Use the existing `SimpleRateLimiter` from `app/core/retry_utils.py` instead of `apply_rate_limit()`:

```python
from app.core.retry_utils import SimpleRateLimiter

class EnsemblAnnotationSource(BaseAnnotationSource):
    def __init__(self, session: Session):
        super().__init__(session)
        # Use SimpleRateLimiter from retry_utils.py (line 385-409)
        self.rate_limiter = SimpleRateLimiter(
            requests_per_second=self.requests_per_second
        )

    async def fetch_annotation(self, gene: Gene) -> dict[str, Any] | None:
        await self.rate_limiter.wait()  # Better than apply_rate_limit()
        # ... rest of implementation
```

### 3. Source Registration

**File**: `backend/app/pipeline/sources/annotations/__init__.py`

```python
# Add to imports
from .ensembl import EnsemblAnnotationSource
from .uniprot import UniProtAnnotationSource

# Add to __all__
__all__ = [
    "BaseAnnotationSource",
    "ClinVarAnnotationSource",
    "DescartesAnnotationSource",
    "EnsemblAnnotationSource",      # NEW
    "GnomADAnnotationSource",
    "GTExAnnotationSource",
    "HGNCAnnotationSource",
    "HPOAnnotationSource",
    "MPOMGIAnnotationSource",
    "StringPPIAnnotationSource",
    "UniProtAnnotationSource",      # NEW
]
```

### 4. Pipeline Registration

**File**: `backend/app/pipeline/annotation_pipeline.py`

```python
# Add to self.sources dict (around line 45-55)
from app.pipeline.sources.annotations.ensembl import EnsemblAnnotationSource
from app.pipeline.sources.annotations.uniprot import UniProtAnnotationSource

self.sources = {
    "hgnc": HGNCAnnotationSource,
    "gnomad": GnomADAnnotationSource,
    "gtex": GTExAnnotationSource,
    "descartes": DescartesAnnotationSource,
    "mpo_mgi": MPOMGIAnnotationSource,
    "string_ppi": StringPPIAnnotationSource,
    "hpo": HPOAnnotationSource,
    "clinvar": ClinVarAnnotationSource,
    "ensembl": EnsemblAnnotationSource,     # NEW
    "uniprot": UniProtAnnotationSource,     # NEW
}
```

### 5. API Endpoint Integration

**File**: `backend/app/api/endpoints/gene_annotations.py`

Add update task functions following existing pattern:

```python
# Add imports at top
from app.pipeline.sources.annotations.ensembl import EnsemblAnnotationSource
from app.pipeline.sources.annotations.uniprot import UniProtAnnotationSource


async def _update_ensembl_annotation(gene: Gene, db: Session):
    """Background task to update Ensembl annotation for a gene."""
    from app.core.cache_service import get_cache_service

    try:
        source = EnsemblAnnotationSource(db)
        success = await source.update_gene(gene)

        if success:
            cache_service = get_cache_service(db)
            await cache_service.delete(f"{gene.id}:*", namespace="annotations")
            await logger.info(
                "Ensembl annotation updated",
                gene_symbol=gene.approved_symbol,
                gene_id=gene.id
            )
        else:
            await logger.warning(
                "Failed to update Ensembl annotation",
                gene_symbol=gene.approved_symbol
            )
    except Exception as e:
        await logger.error(
            f"Error updating Ensembl annotation: {str(e)}",
            gene_symbol=gene.approved_symbol,
            exc_info=True
        )


async def _update_uniprot_annotation(gene: Gene, db: Session):
    """Background task to update UniProt annotation for a gene."""
    from app.core.cache_service import get_cache_service

    try:
        source = UniProtAnnotationSource(db)
        success = await source.update_gene(gene)

        if success:
            cache_service = get_cache_service(db)
            await cache_service.delete(f"{gene.id}:*", namespace="annotations")
            await logger.info(
                "UniProt annotation updated",
                gene_symbol=gene.approved_symbol,
                gene_id=gene.id
            )
        else:
            await logger.warning(
                "Failed to update UniProt annotation",
                gene_symbol=gene.approved_symbol
            )
    except Exception as e:
        await logger.error(
            f"Error updating UniProt annotation: {str(e)}",
            gene_symbol=gene.approved_symbol,
            exc_info=True
        )


# Update the update_gene_annotations endpoint (around line 218-234)
# Add to the switch statement in the endpoint:
elif source_name == "ensembl":
    background_tasks.add_task(_update_ensembl_annotation, gene, db)
elif source_name == "uniprot":
    background_tasks.add_task(_update_uniprot_annotation, gene, db)


# Update the default sources list (around line 186-188)
# Change from:
#   sources: list[str] = Query(
#       ["hgnc", "gnomad", "gtex", "hpo", "clinvar", "string_ppi"], ...
#   )
# To:
sources: list[str] = Query(
    ["hgnc", "gnomad", "gtex", "hpo", "clinvar", "string_ppi", "ensembl", "uniprot"],
    description="Annotation sources to update"
)
```

### 6. Database Considerations

**No schema changes required!**

The existing `gene_annotations` table with JSONB storage handles new sources automatically:

```sql
-- Existing table structure (no changes needed)
CREATE TABLE gene_annotations (
    id SERIAL PRIMARY KEY,
    gene_id INTEGER REFERENCES genes(id),
    source VARCHAR(50) NOT NULL,           -- 'ensembl' or 'uniprot'
    version VARCHAR(50),
    annotations JSONB,                     -- Stores all structured data
    metadata JSONB,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    UNIQUE(gene_id, source)
);

-- Example Ensembl annotation (stored in annotations JSONB)
{
    "gene_symbol": "PKD1",
    "gene_id": "ENSG00000008710",
    "chromosome": "16",
    "start": 2138710,
    "end": 2185899,
    "strand": "+",
    "canonical_transcript": {
        "ensembl_transcript_id": "ENST00000262304",
        "refseq_transcript_id": "NM_001009944.3",
        "is_mane_select": true
    },
    "exons": [
        {"number": 1, "start": 2138710, "end": 2138900, "size": 191},
        ...
    ],
    "exon_count": 46,
    "gene_length": 47189
}

-- Example UniProt annotation
{
    "gene_symbol": "PKD1",
    "accession": "P98161",
    "protein_name": "Polycystin-1",
    "length": 4303,
    "domains": [
        {"type": "Domain", "name": "PKD repeat", "start": 1234, "end": 1345},
        ...
    ],
    "domain_count": 12,
    "pfam_references": [...],
    "interpro_references": [...]
}
```

---

## Admin Dashboard Integration

### Automatic Discovery

**No frontend changes required for basic integration!**

The admin dashboard automatically discovers annotation sources from the backend:

1. **AdminAnnotations.vue** calls `GET /api/annotations/sources`
2. Backend returns all registered sources including Ensembl/UniProt
3. Sources appear in the "Annotation Sources" table automatically
4. Play button triggers update for individual sources
5. "Run Full Update" includes all active sources

### Admin Features Available Out-of-the-Box

After backend integration, admins can:

| Feature | How It Works |
|---------|--------------|
| **View sources in table** | Automatic from `/api/annotations/sources` |
| **See last update time** | Stored in `annotation_sources` table |
| **Trigger individual update** | Play button → `POST /api/annotations/pipeline/update-missing/{source}` |
| **Include in full update** | Checkbox in selective strategy |
| **See in statistics** | "Data Sources" count increments to 10 |
| **Test gene lookup** | Gene ID + source filter dropdown |

### Source Filter Dropdown Update

**File**: `frontend/src/views/admin/AdminAnnotations.vue`

The source filter dropdown is hardcoded. Update it to include new sources:

```javascript
// Around line 664-666, update sourceFilterOptions:
const sourceFilterOptions = [
  'hgnc',
  'gnomad',
  'gtex',
  'hpo',
  'clinvar',
  'string_ppi',
  'descartes',
  'mpo_mgi',
  'ensembl',   // NEW
  'uniprot'    // NEW
]
```

---

## Batch Processing Strategy

### Ensembl Batch Implementation

```python
# In EnsemblAnnotationSource.fetch_batch()
import asyncio
from app.core.retry_utils import SimpleRateLimiter, retry_with_backoff, RetryConfig
import httpx

class EnsemblAnnotationSource(BaseAnnotationSource):
    source_name = "ensembl"
    display_name = "Ensembl"
    version = "1.0"

    def __init__(self, session: Session):
        super().__init__(session)
        # Use SimpleRateLimiter from retry_utils.py
        self.rate_limiter = SimpleRateLimiter(
            requests_per_second=self.requests_per_second
        )

    @retry_with_backoff(config=RetryConfig(max_retries=5))
    async def fetch_batch(self, genes: list[Gene]) -> dict[int, dict[str, Any]]:
        """
        Batch fetch using Ensembl POST /lookup/symbol endpoint.

        Performance (validated 2026-01-11):
        - Max 1000 symbols per request (using 500 for safety)
        - 8 genes with expand=True: 5.2s
        - 571 genes: ~15s total (1-2 requests)
        """
        client = await self.get_http_client()
        results = {}

        symbols = [g.approved_symbol for g in genes]
        gene_by_symbol = {g.approved_symbol.upper(): g for g in genes}

        # Use batch_size from config (default 500, max 1000)
        chunk_size = min(self.batch_size, 1000)

        for i in range(0, len(symbols), chunk_size):
            chunk = symbols[i:i + chunk_size]
            await self.rate_limiter.wait()  # Use SimpleRateLimiter

            try:
                response = await client.post(
                    f"{self.base_url}/lookup/symbol/homo_sapiens",
                    json={"symbols": chunk},
                    params={"expand": 1},
                    headers={"Content-Type": "application/json"},
                    timeout=300.0  # 5 min for large batches
                )

                # CRITICAL: Check status code before parsing JSON
                if response.status_code != 200:
                    logger.sync_warning(
                        f"Ensembl batch request failed",
                        status_code=response.status_code,
                        batch_size=len(chunk)
                    )
                    continue

                data = response.json()
                for symbol, gene_data in data.items():
                    if isinstance(gene_data, dict) and "error" not in gene_data:
                        gene = gene_by_symbol.get(symbol.upper())
                        if gene:
                            results[gene.id] = self._parse_ensembl_response(gene_data, symbol)

            except httpx.HTTPStatusError as e:
                logger.sync_error(
                    "Ensembl batch HTTP error",
                    status_code=e.response.status_code,
                    batch_start=i
                )
                raise  # Let retry decorator handle it

        return results
```

### UniProt Batch Implementation

```python
# In UniProtAnnotationSource.fetch_batch()
import asyncio
from app.core.retry_utils import SimpleRateLimiter, retry_with_backoff, RetryConfig
import httpx

class UniProtAnnotationSource(BaseAnnotationSource):
    source_name = "uniprot"
    display_name = "UniProt"
    version = "1.0"

    # Concurrent request limit (like ClinVar pattern)
    max_concurrent_batch_fetches = 2

    def __init__(self, session: Session):
        super().__init__(session)
        # Use SimpleRateLimiter from retry_utils.py
        self.rate_limiter = SimpleRateLimiter(
            requests_per_second=self.requests_per_second
        )

    async def fetch_batch(self, genes: list[Gene]) -> dict[int, dict[str, Any]]:
        """
        Batch fetch using UniProt OR query with chunking.

        Performance (validated 2026-01-11):
        - Max 100 OR conditions per query (HARD LIMIT!)
        - 8 genes: 0.48s
        - 571 genes: ~10s with 6 requests
        """
        results = {}

        gene_by_symbol = {g.approved_symbol.upper(): g for g in genes}
        symbols = [g.approved_symbol for g in genes]

        # UniProt hard limit: 100 OR conditions
        chunk_size = min(self.batch_size, 100)

        # Use semaphore to limit concurrent requests (like ClinVar at line 450)
        semaphore = asyncio.Semaphore(self.max_concurrent_batch_fetches)

        async def fetch_chunk_with_semaphore(chunk: list[str], chunk_num: int):
            async with semaphore:
                return await self._fetch_uniprot_chunk(chunk, chunk_num)

        # Create tasks for all chunks
        tasks = []
        chunks = [symbols[i:i + chunk_size] for i in range(0, len(symbols), chunk_size)]
        for chunk_num, chunk in enumerate(chunks):
            tasks.append(fetch_chunk_with_semaphore(chunk, chunk_num))

        # Execute with limited concurrency
        chunk_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        for chunk_result in chunk_results:
            if isinstance(chunk_result, Exception):
                logger.sync_error(f"UniProt chunk failed: {chunk_result}")
                continue
            if chunk_result:
                for gene_name, annotation in chunk_result.items():
                    gene = gene_by_symbol.get(gene_name.upper())
                    if gene and gene.id not in results:
                        results[gene.id] = annotation

        return results

    @retry_with_backoff(config=RetryConfig(max_retries=5))
    async def _fetch_uniprot_chunk(
        self, chunk: list[str], chunk_num: int
    ) -> dict[str, dict[str, Any]]:
        """Fetch a single chunk with retry logic."""
        await self.rate_limiter.wait()
        client = await self.get_http_client()

        # Build OR query
        query_parts = [
            f"(gene:{s} AND organism_id:9606 AND reviewed:true)"
            for s in chunk
        ]
        query = " OR ".join(query_parts)

        response = await client.get(
            f"{self.base_url}/uniprotkb/search",
            params={
                "query": query,
                "format": "json",
                "fields": "accession,id,protein_name,sequence,ft_domain,ft_region,xref_pfam,xref_interpro,gene_names",
                "size": 500
            },
            timeout=60.0
        )

        # CRITICAL: Check status code before parsing JSON
        if response.status_code != 200:
            logger.sync_warning(
                f"UniProt chunk request failed",
                status_code=response.status_code,
                chunk_num=chunk_num
            )
            return {}

        data = response.json()
        results = {}

        # UniProt returns {"results": []} NOT {"error": ...}
        for entry in data.get("results", []):
            gene_name = entry.get("genes", [{}])[0].get("geneName", {}).get("value", "")
            if gene_name:
                results[gene_name.upper()] = self._parse_uniprot_response(entry, gene_name)

        return results
```

---

## Scheduled Updates

### Add to Scheduler Configuration

The annotation scheduler is configured in `backend/app/core/scheduler.py`. Add Ensembl/UniProt to monthly updates:

```python
# In scheduler configuration, add monthly job for structural data

scheduler.add_job(
    func=run_annotation_update,
    trigger=CronTrigger(day=1, hour=4, minute=0),  # 1st of month, 4 AM
    id="monthly_structural",
    name="Monthly Structural Data Update",
    kwargs={
        "strategy": "selective",
        "sources": ["ensembl", "uniprot"],
        "force": False
    },
    replace_existing=True
)
```

### Recommended Update Schedule

| Source | Frequency | Rationale |
|--------|-----------|-----------|
| Ensembl | Monthly | Gene structure rarely changes |
| UniProt | Monthly | Protein domains are stable |

---

## Testing Strategy

### 1. Unit Tests

**File**: `backend/tests/test_ensembl_source.py`

```python
@pytest.mark.asyncio
async def test_ensembl_batch_fetch(mock_session):
    """Test batch fetching from Ensembl."""
    source = EnsemblAnnotationSource(mock_session)

    # Mock genes
    genes = [MagicMock(id=1, approved_symbol="PKD1")]

    # Mock HTTP response
    with patch.object(source, 'get_http_client') as mock_client:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "PKD1": {
                "id": "ENSG00000008710",
                "seq_region_name": "16",
                "start": 2138710,
                "end": 2185899,
                "strand": 1,
                "Transcript": [...]
            }
        }
        mock_client.return_value.post = AsyncMock(return_value=mock_response)

        results = await source.fetch_batch(genes)

        assert 1 in results
        assert results[1]["gene_id"] == "ENSG00000008710"
```

### 2. Integration Tests

```python
@pytest.mark.integration
async def test_ensembl_api_live():
    """Test live Ensembl API (requires network)."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://rest.ensembl.org/lookup/symbol/homo_sapiens",
            json={"symbols": ["PKD1"]},
            params={"expand": 1},
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "PKD1" in data
```

### 3. Manual Testing Checklist

- [ ] Create source classes and run `make test`
- [ ] Start backend and check `GET /api/annotations/sources` returns 10 sources
- [ ] Login to admin dashboard, verify Ensembl/UniProt appear in table
- [ ] Use "Gene Annotation Lookup" to test a gene (e.g., gene_id=1, source=ensembl)
- [ ] Click play button on Ensembl row, verify update runs
- [ ] Run "Selective" update with only Ensembl selected
- [ ] Run "Full Update" and verify all 10 sources process
- [ ] Check database: `SELECT * FROM gene_annotations WHERE source='ensembl' LIMIT 5`

---

## Implementation Checklist

### Phase 1: Backend Source Classes
- [ ] Create `backend/app/pipeline/sources/annotations/ensembl.py`
- [ ] Create `backend/app/pipeline/sources/annotations/uniprot.py`
- [ ] Add configuration to `backend/config/annotations.yaml`
- [ ] Register in `__init__.py` exports

### Phase 2: Pipeline Integration
- [ ] Add to `annotation_pipeline.py` sources dict
- [ ] Add update task functions to `gene_annotations.py`
- [ ] Update default sources list in API endpoint
- [ ] Add to endpoint switch statement

### Phase 3: Testing
- [ ] Write unit tests for both sources
- [ ] Run existing test suite (`make test`)
- [ ] Manual test via admin dashboard
- [ ] Verify batch operations work correctly

### Phase 4: Admin Dashboard (Optional)
- [ ] Update `sourceFilterOptions` array (minor)
- [ ] Verify sources appear in table automatically
- [ ] Test all admin actions work

### Phase 5: Documentation
- [ ] Update `docs/features/annotations.md`
- [ ] Add API documentation for new sources
- [ ] Update this file with completion status

---

## Performance Projections

### Full Database Update (571 genes)

| Source | Strategy | Requests | Time | Notes |
|--------|----------|----------|------|-------|
| Ensembl | POST batch | 1 | ~3-4 min | Single request with expand |
| UniProt | OR chunks | 6 | ~12 sec | 100 genes per request |
| **Total** | Parallel | 7 | **~4 min** | Dominated by Ensembl |

### Incremental Update (10 new genes)

| Source | Strategy | Requests | Time |
|--------|----------|----------|------|
| Ensembl | Individual | 10 | ~10 sec |
| UniProt | Individual | 10 | ~3 sec |
| **Total** | - | 20 | **~15 sec** |

---

## Risk Mitigation

### API Rate Limits

| API | Limit | Mitigation |
|-----|-------|------------|
| Ensembl | 15 req/s, 55k/hour | Built-in rate limiting, batch POST |
| UniProt | No explicit limit | Conservative 5 req/s, OR query batching |

### Error Handling

```python
# All sources use retry_with_backoff decorator
@retry_with_backoff(config=RetryConfig(
    max_retries=3,
    initial_delay=1.0,
    max_delay=60.0,
    exponential_base=2.0,
    jitter=True,
    retry_on_status_codes=(429, 500, 502, 503, 504)
))
async def fetch_annotation(self, gene: Gene) -> dict | None:
    ...
```

### Circuit Breaker

Both sources inherit circuit breaker from `BaseAnnotationSource`:
- Threshold: 5 consecutive failures
- Opens circuit, returns None for all requests
- Auto-resets after cooldown period

---

## References

### API Documentation (Verified 2026-01-11)
- [Ensembl REST API](https://rest.ensembl.org/)
- [Ensembl POST Symbol Lookup](https://rest.ensembl.org/documentation/info/symbol_post) - Max 1000 symbols
- [Ensembl Rate Limits](https://github.com/Ensembl/ensembl-rest/wiki/Rate-Limits) - 15 req/s, 55k/hour
- [UniProt REST API](https://www.uniprot.org/help/api)
- [UniProt Batch Retrieval](https://www.uniprot.org/help/api_batch_retrieval) - Max 100k IDs per job
- [UniProt Query Syntax](https://www.uniprot.org/help/api_queries)

### Codebase References
- [BaseAnnotationSource](../../../backend/app/pipeline/sources/annotations/base.py) - Abstract base class
- [ClinVarAnnotationSource](../../../backend/app/pipeline/sources/annotations/clinvar.py) - Reference implementation
- [retry_utils.py](../../../backend/app/core/retry_utils.py) - SimpleRateLimiter, RetryConfig
- [annotations.yaml](../../../backend/config/annotations.yaml) - Configuration file
- [gene-protein-visualization.md](./gene-protein-visualization.md) - Visualization plan

---

**Document Status**: Ready for Implementation
**Author**: Expert System Analysis
**Last Updated**: 2026-01-11
**Review Status**: ✅ API endpoints verified, patterns aligned with codebase
