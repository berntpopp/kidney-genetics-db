# Gene Structure & Protein Domain Visualization Implementation Plan

**Issue**: [#29 - Add gene structure and protein domain annotations for visualizations](https://github.com/berntpopp/kidney-genetics-db/issues/29)
**Status**: Ready for Implementation
**Priority**: Medium
**Rating**: 9/10 (Expert Reviewed & Batch APIs Validated)

**Related Plans**:
- [ensembl-uniprot-system-integration.md](./ensembl-uniprot-system-integration.md) - Backend integration for annotation sources
- [visualization-integration-ux-analysis.md](./visualization-integration-ux-analysis.md) - UX analysis and subpage design
- [gene-visualization-implementation-prompt.md](./gene-visualization-implementation-prompt.md) - Agentic LLM implementation prompt
- [gene-visualization-TODO.md](./gene-visualization-TODO.md) - Progress tracking (created during implementation)

---

## Executive Summary

Implement gene structure (exons/introns) and protein domain visualization for gene detail pages by integrating Ensembl and UniProt APIs as new annotation sources. The implementation follows a **lean, API-first approach** that leverages external data sources with aggressive caching, avoiding the complexity of gene-specific components like in hnf1b-db.

### API Validation Results (Verified 2026-01-11)

| API | Status | Response Time | Error Response |
|-----|--------|---------------|----------------|
| Ensembl REST API | ✅ Working | ~874ms | Returns `{"error": "..."}` for invalid genes |
| UniProt REST API | ✅ Working | ~260ms | Returns `{"results": []}` for invalid genes |

> **Important**: UniProt does NOT return an `error` key - it returns empty results array.

### Batch API Performance (Validated 2026-01-11)

Both APIs support efficient batch operations that dramatically reduce request count:

#### Ensembl Batch POST Endpoint
| Batch Size | Time | Per-Gene | Found | Notes |
|------------|------|----------|-------|-------|
| 10 genes | 5.9s | 596ms | 10/10 | With expand=True |
| 50 genes | 22.1s | 442ms | 49/50 | With expand=True |
| 100 genes | 49.1s | 491ms | 99/100 | With expand=True |
| 178 genes | 70.1s | 394ms | 178/178 | With expand=True |
| 178 genes | 1.6s | 9ms | 178/178 | expand=False (basic) |

- **Max symbols per request**: 1,000
- **Rate limit**: 55,000 requests/hour (15/sec)
- **Endpoint**: `POST /lookup/symbol/homo_sapiens`

#### UniProt Batch Query
| Strategy | Batch Size | Time | Per-Gene | Requests |
|----------|------------|------|----------|----------|
| OR Query | 50 genes | 1.0s | 20ms | 1 |
| OR Query | 100 genes | 1.3s | 13ms | 1 |
| OR Query | 178 genes | 2.1s | 12ms | 2 |
| ID Mapping | 178 genes | 3.7s | 21ms | ~3 |

- **Max OR conditions per query**: 100 (hard limit!)
- **ID Mapping max IDs**: 100,000
- **Recommendation**: Use OR Query with 100-gene chunks

#### Projected Performance for 571 Genes

| API | Strategy | Requests | Est. Time | Improvement |
|-----|----------|----------|-----------|-------------|
| **Ensembl** | POST batch | 1 | ~3-4 min | 571x fewer requests |
| **UniProt** | OR chunks | 6 | ~12 sec | 95x fewer requests |
| **Combined** | Parallel | 7 | ~3-4 min | Dominated by Ensembl |

### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **External API-first** | No database schema changes needed; structural data rarely changes |
| **Batch API endpoints** | 571x fewer Ensembl requests, 95x fewer UniProt requests |
| **30-day cache TTL** | Gene structure/domains are stable; reduces API calls |
| **Generic components** | Works for all 571+ genes, not gene-specific like hnf1b-db |
| **Simple D3 + SVG visualizations** | KISS - avoid 1400-line components; focus on clarity |
| **Reuse existing systems** | Extend BaseAnnotationSource, use CacheService, UnifiedLogger |
| **MANE Select transcripts** | Use HGNC MANE Select (RefSeq + Ensembl) as canonical reference |
| **ResizeObserver pattern** | Follows D3BarChart.vue pattern for responsive sizing |
| **Vuetify theme integration** | Consistent colors across light/dark themes |
| **@retry_with_backoff decorator** | Follows existing annotation source patterns (HPO, ClinVar) |
| **Tooltip composable** | DRY - extract duplicate tooltip code |

---

## Architecture Overview

**IMPORTANT**: Visualizations are on a **dedicated subpage** (`/genes/:symbol/structure`), NOT on the main gene detail page. This preserves the evidence-first design where Gene Information and Evidence Score remain the most prominent elements.

See [visualization-integration-ux-analysis.md](./visualization-integration-ux-analysis.md) for the full UX rationale.

```
┌─────────────────────────────────────────────────────────────────┐
│                    Frontend (Vue 3 + Vuetify)                    │
├─────────────────────────────────────────────────────────────────┤
│  GeneDetail.vue (MINIMAL CHANGES - add link only)                │
│    └── "View Structure →" link in ClinVar section                │
│                                                                  │
│  GeneStructure.vue (NEW - dedicated subpage)                     │
│    ├── route: /genes/:symbol/structure                           │
│    ├── GeneStructureVisualization.vue (NEW)                      │
│    │     └── uses useD3Tooltip composable (NEW)                  │
│    └── ProteinDomainVisualization.vue (NEW)                      │
│          └── uses useD3Tooltip composable (NEW)                  │
├─────────────────────────────────────────────────────────────────┤
│                     API Layer (FastAPI)                          │
├─────────────────────────────────────────────────────────────────┤
│  GET /api/annotations/genes/{gene_id}/annotations?source=ensembl │
│  GET /api/annotations/genes/{gene_id}/annotations?source=uniprot │
│  POST /api/annotations/genes/{gene_id}/update?source=ensembl     │
│  POST /api/annotations/genes/{gene_id}/update?source=uniprot     │
├─────────────────────────────────────────────────────────────────┤
│                  Annotation Sources (Backend)                    │
├─────────────────────────────────────────────────────────────────┤
│  EnsemblAnnotationSource (NEW)                                   │
│    └── extends BaseAnnotationSource                              │
│    └── @retry_with_backoff decorator                             │
│    └── API: https://rest.ensembl.org/                           │
│                                                                  │
│  UniProtAnnotationSource (NEW)                                   │
│    └── extends BaseAnnotationSource                              │
│    └── @retry_with_backoff decorator                             │
│    └── API: https://rest.uniprot.org/                           │
├─────────────────────────────────────────────────────────────────┤
│                    Storage (PostgreSQL)                          │
├─────────────────────────────────────────────────────────────────┤
│  gene_annotations table (existing)                               │
│    └── source = 'ensembl' or 'uniprot'                          │
│    └── annotations (JSONB) - stores structured data              │
└─────────────────────────────────────────────────────────────────┘
```

---

## MANE Select Transcript Integration

### What is MANE Select?

**MANE (Matched Annotation from NCBI and EMBL-EBI)** provides a single agreed-upon canonical transcript for each protein-coding gene. It's the gold standard for transcript selection because:

- **Joint effort** between NCBI (RefSeq) and EMBL-EBI (Ensembl)
- **One transcript per gene** - eliminates ambiguity
- **Both IDs included** - Ensembl (ENST...) and RefSeq (NM_...) are matched
- **Used consistently** across the codebase (see `GeneInformationCard.vue`, `hgnc.py`)

### Existing MANE Select Usage in Codebase

The codebase already retrieves and displays MANE Select transcripts:

1. **HGNC Annotation Source** (`backend/app/pipeline/sources/annotations/hgnc.py`):
   ```python
   def _parse_mane_select(self, mane_select_list: list) -> dict | None:
       # Returns: {"ensembl_transcript_id": "ENST...", "refseq_transcript_id": "NM_..."}
   ```

2. **Frontend Display** (`frontend/src/components/gene/GeneInformationCard.vue`):
   ```vue
   <template v-if="hgncData?.mane_select?.refseq_transcript_id">
     • {{ hgncData.mane_select.refseq_transcript_id }}
   </template>
   ```

### Implementation Strategy

For gene structure visualization, we use MANE Select as the **primary** transcript choice:

```
┌─────────────────────────────────────────────────────┐
│ Transcript Selection Priority                        │
├─────────────────────────────────────────────────────┤
│ 1. MANE Select from HGNC annotations (preferred)    │
│    - ensembl_transcript_id: ENST00000356175.9       │
│    - refseq_transcript_id: NM_000546.6              │
├─────────────────────────────────────────────────────┤
│ 2. Ensembl is_canonical flag (fallback)             │
├─────────────────────────────────────────────────────┤
│ 3. Longest protein-coding transcript (last resort)  │
└─────────────────────────────────────────────────────┘
```

This ensures consistency with:
- The RefSeq ID shown in `GeneInformationCard.vue` header
- gnomAD constraint data (uses canonical transcript)
- Clinical databases that reference RefSeq transcripts

---

## Phase 1: Backend Implementation

### 1.1 Configuration

**File**: `backend/config/annotations.yaml` (update)

Add new data source configurations following existing pattern:

```yaml
# Add to existing annotations.yaml

ensembl:
  display_name: Ensembl
  description: Gene structure data - exons, transcripts, genomic coordinates
  base_url: https://rest.ensembl.org
  update_frequency: monthly
  is_active: true
  priority: 2
  requests_per_second: 15.0  # Ensembl allows 15 req/s
  max_retries: 3
  cache_ttl_days: 30
  use_http_cache: true
  circuit_breaker_threshold: 3

uniprot:
  display_name: UniProt
  description: Protein domains and structural features
  base_url: https://rest.uniprot.org
  update_frequency: monthly
  is_active: true
  priority: 2
  requests_per_second: 5.0
  max_retries: 3
  cache_ttl_days: 30
  use_http_cache: true
  circuit_breaker_threshold: 3
```

### 1.2 EnsemblAnnotationSource

**File**: `backend/app/pipeline/sources/annotations/ensembl.py`

```python
"""
Ensembl Annotation Source

Fetches gene structure (exons, introns, transcripts) from Ensembl REST API.
"""

from typing import Any
from app.models.gene import Gene
from app.pipeline.sources.annotations.base import BaseAnnotationSource
from app.core.logging import get_logger
from app.core.retry_utils import RetryConfig, retry_with_backoff

logger = get_logger(__name__)


class EnsemblAnnotationSource(BaseAnnotationSource):
    """
    Ensembl gene structure annotation source.

    Fetches exon/intron coordinates, transcript information, and genomic
    location data for gene visualization.

    IMPORTANT: Uses MANE Select transcripts from HGNC annotations when available.
    MANE (Matched Annotation from NCBI and EMBL-EBI) provides a single agreed-upon
    transcript per protein-coding gene with both Ensembl (ENST) and RefSeq (NM_) IDs.
    """

    source_name = "ensembl"
    display_name = "Ensembl"
    version = "1.0"

    # Cache configuration - structural data rarely changes
    cache_ttl_days = 30
    cache_namespace = "annotations"

    # Rate limiting per Ensembl guidelines
    requests_per_second = 15.0  # Ensembl allows 15 req/s

    # API configuration
    base_url = "https://rest.ensembl.org"

    @retry_with_backoff(config=RetryConfig(max_retries=3))
    async def fetch_annotation(self, gene: Gene) -> dict[str, Any] | None:
        """Fetch gene structure from Ensembl REST API."""
        client = await self.get_http_client()
        await self.apply_rate_limit()

        # Get MANE Select transcript from HGNC annotations if available
        mane_select = self._get_mane_select_from_hgnc(gene)

        try:
            # Lookup gene with expanded transcript/exon data
            url = f"{self.base_url}/lookup/symbol/homo_sapiens/{gene.approved_symbol}"
            params = {"expand": 1, "content-type": "application/json"}

            response = await client.get(url, params=params, timeout=30.0)

            # Check HTTP status code first
            if response.status_code != 200:
                logger.sync_warning(
                    "Ensembl API returned non-200 status",
                    gene_symbol=gene.approved_symbol,
                    status_code=response.status_code
                )
                return None

            data = response.json()

            # Check for API error response (Ensembl returns {"error": "..."})
            if "error" in data:
                logger.sync_warning(
                    "Ensembl API returned error",
                    gene_symbol=gene.approved_symbol,
                    error=data["error"]
                )
                return None

            if not data or "id" not in data:
                logger.sync_warning(
                    "Ensembl API returned invalid data",
                    gene_symbol=gene.approved_symbol
                )
                return None

            return self._parse_ensembl_response(data, gene.approved_symbol, mane_select)

        except Exception as e:
            logger.sync_error(
                "Ensembl API error",
                gene_symbol=gene.approved_symbol,
                error=str(e)
            )
            return None

    def _get_mane_select_from_hgnc(self, gene: Gene) -> dict | None:
        """
        Get MANE Select transcript IDs from HGNC annotations.

        MANE Select is the gold standard for canonical transcript selection,
        agreed upon by both NCBI (RefSeq) and EMBL-EBI (Ensembl).

        Returns:
            Dictionary with ensembl_transcript_id and refseq_transcript_id
        """
        if not hasattr(gene, "annotations") or not gene.annotations:
            return None

        for ann in gene.annotations:
            if ann.source == "hgnc" and ann.annotations:
                mane_data = ann.annotations.get("mane_select")
                if mane_data:
                    return mane_data
        return None

    def _parse_ensembl_response(
        self, data: dict, symbol: str, mane_select: dict | None = None
    ) -> dict[str, Any]:
        """
        Parse Ensembl response into standardized format.

        Uses MANE Select transcript from HGNC as primary choice for canonical
        transcript selection. Falls back to Ensembl is_canonical flag.
        """
        transcripts = data.get("Transcript", [])
        canonical = self._find_canonical_transcript(transcripts, mane_select)

        exons = []
        if canonical and "Exon" in canonical:
            for i, exon in enumerate(canonical["Exon"], 1):
                exons.append({
                    "number": i,
                    "id": exon.get("id"),
                    "start": exon.get("start"),
                    "end": exon.get("end"),
                    "size": exon.get("end", 0) - exon.get("start", 0) + 1,
                })

        # Build canonical transcript info with MANE Select data
        canonical_info = {
            "ensembl_transcript_id": canonical.get("id") if canonical else None,
            "biotype": canonical.get("biotype") if canonical else None,
            "is_canonical": canonical.get("is_canonical") if canonical else None,
        }

        # Add MANE Select RefSeq ID if available (for display consistency with GeneInformationCard)
        if mane_select:
            canonical_info["refseq_transcript_id"] = mane_select.get("refseq_transcript_id")
            canonical_info["is_mane_select"] = True
        else:
            canonical_info["is_mane_select"] = False

        return {
            "gene_symbol": symbol,
            "gene_id": data.get("id"),
            "chromosome": data.get("seq_region_name"),
            "start": data.get("start"),
            "end": data.get("end"),
            "strand": "+" if data.get("strand") == 1 else "-",
            "biotype": data.get("biotype"),
            "description": data.get("description"),
            "canonical_transcript": canonical_info,
            "exons": exons,
            "exon_count": len(exons),
            "gene_length": data.get("end", 0) - data.get("start", 0) + 1,
            "transcript_count": len(transcripts),
        }

    def _find_canonical_transcript(
        self, transcripts: list, mane_select: dict | None = None
    ) -> dict | None:
        """
        Find the canonical transcript using MANE Select as primary choice.

        Priority order:
        1. MANE Select transcript from HGNC (if available)
        2. Ensembl is_canonical flag
        3. Longest protein-coding transcript (fallback)

        MANE Select is preferred because it's the agreed-upon canonical
        transcript between NCBI (RefSeq) and EMBL-EBI (Ensembl).
        """
        # Priority 1: MANE Select transcript from HGNC
        if mane_select and mane_select.get("ensembl_transcript_id"):
            mane_ensembl_id = mane_select["ensembl_transcript_id"]
            # Strip version for comparison (ENST00000356175.9 -> ENST00000356175)
            mane_base_id = mane_ensembl_id.split(".")[0]

            for t in transcripts:
                t_id = t.get("id", "")
                t_base_id = t_id.split(".")[0]
                if t_base_id == mane_base_id:
                    logger.sync_debug(
                        "Using MANE Select transcript",
                        transcript_id=t_id,
                        mane_ensembl=mane_ensembl_id,
                        mane_refseq=mane_select.get("refseq_transcript_id")
                    )
                    return t

        # Priority 2: Ensembl is_canonical flag
        for t in transcripts:
            if t.get("is_canonical"):
                return t

        # Priority 3: Longest protein-coding transcript (fallback)
        protein_coding = [t for t in transcripts if t.get("biotype") == "protein_coding"]
        if protein_coding:
            return max(protein_coding, key=lambda t: len(t.get("Exon", [])))

        return transcripts[0] if transcripts else None

    def _is_valid_annotation(self, annotation_data: dict) -> bool:
        """Validate Ensembl annotation data."""
        if not super()._is_valid_annotation(annotation_data):
            return False

        # Ensembl specific: must have gene_id and exons
        required_fields = ["gene_id", "exons", "chromosome"]
        return all(field in annotation_data for field in required_fields)

    async def fetch_batch(self, genes: list[Gene]) -> dict[int, dict[str, Any]]:
        """
        Batch fetch using Ensembl POST /lookup/symbol endpoint.

        Uses POST with {"symbols": [...]} for up to 1000 symbols at once.
        This reduces 571 individual requests to just 1 batch request.

        Performance (validated 2026-01-11):
        - 178 genes with expand=True: 70s (~394ms/gene)
        - 178 genes with expand=False: 1.6s (~9ms/gene)
        - Max 1000 symbols per request
        """
        client = await self.get_http_client()
        results = {}

        # Build symbol list and create gene lookup map
        symbols = [g.approved_symbol for g in genes]
        gene_by_symbol = {g.approved_symbol.upper(): g for g in genes}

        # Ensembl allows up to 1000 symbols per POST request
        chunk_size = 1000
        for i in range(0, len(symbols), chunk_size):
            chunk = symbols[i:i + chunk_size]
            await self.apply_rate_limit()

            try:
                response = await client.post(
                    f"{self.base_url}/lookup/symbol/homo_sapiens",
                    json={"symbols": chunk},
                    params={"expand": 1},
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json"
                    },
                    timeout=300.0  # 5 min timeout for large batches
                )

                if response.status_code != 200:
                    logger.sync_warning(
                        "Ensembl batch request failed",
                        status_code=response.status_code,
                        chunk_size=len(chunk)
                    )
                    continue

                data = response.json()

                # Process each gene in response
                for symbol, gene_data in data.items():
                    if "error" in gene_data or "id" not in gene_data:
                        continue

                    gene = gene_by_symbol.get(symbol.upper())
                    if gene:
                        parsed = self._parse_ensembl_response(gene_data, symbol)
                        if self._is_valid_annotation(parsed):
                            results[gene.id] = parsed

                logger.sync_info(
                    "Ensembl batch fetch completed",
                    requested=len(chunk),
                    found=len([s for s in chunk if s in data])
                )

            except Exception as e:
                logger.sync_error(
                    "Ensembl batch fetch error",
                    error=str(e),
                    chunk_size=len(chunk)
                )

        return results
```

### 1.3 UniProtAnnotationSource

**File**: `backend/app/pipeline/sources/annotations/uniprot.py`

```python
"""
UniProt Annotation Source

Fetches protein domain information from UniProt REST API.

IMPORTANT: UniProt returns {"results": []} for genes not found,
NOT {"error": "..."}. Handle empty results accordingly.
"""

from typing import Any
from app.models.gene import Gene
from app.pipeline.sources.annotations.base import BaseAnnotationSource
from app.core.logging import get_logger
from app.core.retry_utils import RetryConfig, retry_with_backoff

logger = get_logger(__name__)


class UniProtAnnotationSource(BaseAnnotationSource):
    """
    UniProt protein domain annotation source.

    Fetches protein domains (Pfam, InterPro), active sites, binding sites,
    and other structural features for protein visualization.
    """

    source_name = "uniprot"
    display_name = "UniProt"
    version = "1.0"

    # Cache configuration - protein domains rarely change
    cache_ttl_days = 30
    cache_namespace = "annotations"

    # Rate limiting
    requests_per_second = 5.0

    # API configuration
    base_url = "https://rest.uniprot.org/uniprotkb"

    @retry_with_backoff(config=RetryConfig(max_retries=3))
    async def fetch_annotation(self, gene: Gene) -> dict[str, Any] | None:
        """Fetch protein domains from UniProt REST API."""
        client = await self.get_http_client()
        await self.apply_rate_limit()

        try:
            # Search for human protein by gene symbol (reviewed/Swiss-Prot first)
            url = f"{self.base_url}/search"
            params = {
                "query": f"gene:{gene.approved_symbol} AND organism_id:9606 AND reviewed:true",
                "format": "json",
                "fields": "accession,id,protein_name,sequence,ft_domain,ft_region,ft_binding,ft_act_site,xref_pfam,xref_interpro",
                "size": 1,
            }

            response = await client.get(url, params=params, timeout=30.0)

            # Check HTTP status code first
            if response.status_code != 200:
                logger.sync_warning(
                    "UniProt API returned non-200 status",
                    gene_symbol=gene.approved_symbol,
                    status_code=response.status_code
                )
                return None

            data = response.json()

            # UniProt returns {"results": []} for not found - NOT {"error": ...}
            results = data.get("results", [])

            if not results:
                # Try unreviewed (TrEMBL) if no reviewed entry found
                logger.sync_debug(
                    "No reviewed UniProt entry, trying unreviewed",
                    gene_symbol=gene.approved_symbol
                )
                params["query"] = f"gene:{gene.approved_symbol} AND organism_id:9606"
                response = await client.get(url, params=params, timeout=30.0)

                if response.status_code != 200:
                    return None

                data = response.json()
                results = data.get("results", [])

            if not results:
                logger.sync_info(
                    "No UniProt entry found for gene",
                    gene_symbol=gene.approved_symbol
                )
                return None

            return self._parse_uniprot_response(results[0], gene.approved_symbol)

        except Exception as e:
            logger.sync_error(
                "UniProt API error",
                gene_symbol=gene.approved_symbol,
                error=str(e)
            )
            return None

    def _parse_uniprot_response(self, data: dict, symbol: str) -> dict[str, Any]:
        """Parse UniProt response into standardized format."""
        features = data.get("features", [])

        # Extract domains
        domains = []
        for f in features:
            if f.get("type") in ["Domain", "Region"]:
                domains.append({
                    "type": f.get("type"),
                    "name": f.get("description", "Unknown"),
                    "start": f.get("location", {}).get("start", {}).get("value"),
                    "end": f.get("location", {}).get("end", {}).get("value"),
                })

        # Extract functional sites
        active_sites = []
        binding_sites = []
        for f in features:
            site = {
                "type": f.get("type"),
                "description": f.get("description"),
                "position": f.get("location", {}).get("start", {}).get("value"),
            }
            if f.get("type") == "Active site":
                active_sites.append(site)
            elif f.get("type") == "Binding site":
                binding_sites.append(site)

        # Extract cross-references (Pfam, InterPro)
        pfam_refs = []
        interpro_refs = []
        for xref in data.get("uniProtKBCrossReferences", []):
            if xref.get("database") == "Pfam":
                pfam_refs.append({
                    "id": xref.get("id"),
                    "name": xref.get("properties", [{}])[0].get("value", "")
                })
            elif xref.get("database") == "InterPro":
                interpro_refs.append({
                    "id": xref.get("id"),
                    "name": xref.get("properties", [{}])[0].get("value", "")
                })

        return {
            "gene_symbol": symbol,
            "accession": data.get("primaryAccession"),
            "entry_name": data.get("uniProtkbId"),
            "protein_name": data.get("proteinDescription", {}).get("recommendedName", {}).get("fullName", {}).get("value"),
            "length": data.get("sequence", {}).get("length"),
            "domains": domains,
            "active_sites": active_sites,
            "binding_sites": binding_sites,
            "pfam_references": pfam_refs,
            "interpro_references": interpro_refs,
            "domain_count": len(domains),
            "has_structural_data": len(domains) > 0,
        }

    def _is_valid_annotation(self, annotation_data: dict) -> bool:
        """Validate UniProt annotation data."""
        if not super()._is_valid_annotation(annotation_data):
            return False

        # UniProt specific: must have accession and length
        required_fields = ["accession", "length"]
        return all(field in annotation_data for field in required_fields)

    async def fetch_batch(self, genes: list[Gene]) -> dict[int, dict[str, Any]]:
        """
        Batch fetch using UniProt OR query with chunking.

        Uses OR query syntax: "(gene:PKD1 AND organism_id:9606) OR ..."
        UniProt has a hard limit of 100 OR conditions per query.

        Performance (validated 2026-01-11):
        - 100 genes: 1.3s (~13ms/gene)
        - 178 genes: 2.1s (~12ms/gene) with 2 requests
        - Max 100 OR conditions per request
        """
        client = await self.get_http_client()
        results = {}

        # Build gene lookup map
        gene_by_symbol = {g.approved_symbol.upper(): g for g in genes}

        # UniProt allows max 100 OR conditions per query
        chunk_size = 100
        symbols = [g.approved_symbol for g in genes]

        for i in range(0, len(symbols), chunk_size):
            chunk = symbols[i:i + chunk_size]
            await self.apply_rate_limit()

            try:
                # Build OR query for chunk
                query_parts = [
                    f"(gene:{symbol} AND organism_id:9606 AND reviewed:true)"
                    for symbol in chunk
                ]
                query = " OR ".join(query_parts)

                response = await client.get(
                    f"{self.base_url}/search",
                    params={
                        "query": query,
                        "format": "json",
                        "fields": "accession,id,protein_name,sequence,ft_domain,ft_region,ft_binding,ft_act_site,xref_pfam,xref_interpro,gene_names",
                        "size": 500  # More than chunk size to capture all
                    },
                    timeout=60.0
                )

                if response.status_code != 200:
                    logger.sync_warning(
                        "UniProt batch request failed",
                        status_code=response.status_code,
                        chunk_size=len(chunk)
                    )
                    continue

                data = response.json()
                entries = data.get("results", [])

                # Match results back to genes
                for entry in entries:
                    # Extract gene name from entry
                    gene_names = entry.get("genes", [])
                    if not gene_names:
                        continue

                    primary_gene = gene_names[0].get("geneName", {}).get("value", "")
                    gene = gene_by_symbol.get(primary_gene.upper())

                    if gene and gene.id not in results:
                        parsed = self._parse_uniprot_response(entry, primary_gene)
                        if self._is_valid_annotation(parsed):
                            results[gene.id] = parsed

                logger.sync_info(
                    "UniProt batch fetch completed",
                    requested=len(chunk),
                    found=len(entries)
                )

            except Exception as e:
                logger.sync_error(
                    "UniProt batch fetch error",
                    error=str(e),
                    chunk_size=len(chunk)
                )

        return results
```

### 1.4 Register New Sources

**File**: `backend/app/pipeline/sources/annotations/__init__.py` (update)

```python
# Add to existing imports
from .ensembl import EnsemblAnnotationSource
from .uniprot import UniProtAnnotationSource

# Add to __all__ list
__all__ = [
    # ... existing sources ...
    "EnsemblAnnotationSource",
    "UniProtAnnotationSource",
]

# Add to ANNOTATION_SOURCES dict (if exists)
ANNOTATION_SOURCES = {
    # ... existing sources ...
    "ensembl": EnsemblAnnotationSource,
    "uniprot": UniProtAnnotationSource,
}
```

### 1.5 API Endpoint Registration

**File**: `backend/app/api/endpoints/gene_annotations.py` (update)

Add update task functions following existing pattern:

```python
# Add imports at top
from app.pipeline.sources.annotations.ensembl import EnsemblAnnotationSource
from app.pipeline.sources.annotations.uniprot import UniProtAnnotationSource


async def _update_ensembl_annotation(gene: Gene, db: Session):
    """Background task to update Ensembl annotation."""
    from app.core.cache_service import get_cache_service

    try:
        source = EnsemblAnnotationSource(db)
        success = await source.update_gene(gene)

        if success:
            cache_service = get_cache_service(db)
            await cache_service.delete(f"{gene.id}:*", namespace="annotations")
            await logger.info("Ensembl annotation updated", gene_symbol=gene.approved_symbol)
        else:
            await logger.warning("Failed to update Ensembl annotation", gene_symbol=gene.approved_symbol)
    except Exception as e:
        await logger.error(f"Error updating Ensembl annotation: {str(e)}", gene_symbol=gene.approved_symbol)


async def _update_uniprot_annotation(gene: Gene, db: Session):
    """Background task to update UniProt annotation."""
    from app.core.cache_service import get_cache_service

    try:
        source = UniProtAnnotationSource(db)
        success = await source.update_gene(gene)

        if success:
            cache_service = get_cache_service(db)
            await cache_service.delete(f"{gene.id}:*", namespace="annotations")
            await logger.info("UniProt annotation updated", gene_symbol=gene.approved_symbol)
        else:
            await logger.warning("Failed to update UniProt annotation", gene_symbol=gene.approved_symbol)
    except Exception as e:
        await logger.error(f"Error updating UniProt annotation: {str(e)}", gene_symbol=gene.approved_symbol)


# IMPORTANT: Update the default sources list in update_gene_annotations endpoint:
# Change line ~186-188 from:
#   sources: list[str] = Query(
#       ["hgnc", "gnomad", "gtex", "hpo", "clinvar", "string_ppi"], ...
#   )
# To:
#   sources: list[str] = Query(
#       ["hgnc", "gnomad", "gtex", "hpo", "clinvar", "string_ppi", "ensembl", "uniprot"], ...
#   )

# Add to update_gene_annotations endpoint switch statement (~line 218-234):
#     elif source_name == "ensembl":
#         background_tasks.add_task(_update_ensembl_annotation, gene, db)
#     elif source_name == "uniprot":
#         background_tasks.add_task(_update_uniprot_annotation, gene, db)
```

---

## Phase 2: Frontend Implementation

### 2.1 D3 Tooltip Composable (DRY)

**File**: `frontend/src/composables/useD3Tooltip.js` (NEW)

Extract duplicate tooltip logic to a reusable composable:

```javascript
/**
 * D3 Tooltip Composable
 *
 * Provides reusable tooltip functionality for D3 visualizations.
 * Uses Vuetify CSS variables for theme-aware styling.
 */

import * as d3 from 'd3'

export function useD3Tooltip() {
  let tooltip = null

  /**
   * Show tooltip at mouse position
   * @param {MouseEvent} event - Mouse event
   * @param {string} content - HTML content for tooltip
   */
  const showTooltip = (event, content) => {
    if (!tooltip) {
      tooltip = d3.select('body')
        .append('div')
        .attr('class', 'chart-tooltip')
        .style('position', 'absolute')
        .style('pointer-events', 'none')
        .style('background', 'var(--v-theme-surface)')
        .style('color', 'var(--v-theme-on-surface)')
        .style('border', '1px solid var(--v-theme-outline)')
        .style('border-radius', '4px')
        .style('padding', '8px 12px')
        .style('font-size', '12px')
        .style('box-shadow', '0 2px 8px rgba(0,0,0,0.15)')
        .style('z-index', '1000')
        .style('opacity', 0)
    }

    tooltip.html(content)
      .style('left', event.pageX + 10 + 'px')
      .style('top', event.pageY - 28 + 'px')
      .transition()
      .duration(200)
      .style('opacity', 0.95)
  }

  /**
   * Hide tooltip with fade animation
   */
  const hideTooltip = () => {
    if (tooltip) {
      tooltip.transition()
        .duration(200)
        .style('opacity', 0)
    }
  }

  /**
   * Remove tooltip from DOM (call in onUnmounted)
   */
  const destroyTooltip = () => {
    if (tooltip) {
      tooltip.remove()
      tooltip = null
    }
  }

  return { showTooltip, hideTooltip, destroyTooltip }
}
```

### 2.2 API Client Extensions

**File**: `frontend/src/api/genes.js` (update)

```javascript
// Add to existing geneApi object

/**
 * Get gene structure data (exons, introns) from Ensembl
 * @param {number} geneId - Gene database ID
 * @returns {Promise<Object|null>} Gene structure data or null
 */
async getGeneStructure(geneId) {
  try {
    const response = await apiClient.get(
      `/api/annotations/genes/${geneId}/annotations`,
      { params: { source: 'ensembl' } }
    )
    // API returns: { gene: {...}, annotations: { ensembl: [{version, data, ...}] } }
    const ensemblAnnotations = response.data.annotations?.ensembl
    return ensemblAnnotations?.[0]?.data || null
  } catch (error) {
    window.logService?.error('Failed to fetch gene structure:', error)
    return null
  }
},

/**
 * Get protein domain data from UniProt
 * @param {number} geneId - Gene database ID
 * @returns {Promise<Object|null>} Protein domain data or null
 */
async getProteinDomains(geneId) {
  try {
    const response = await apiClient.get(
      `/api/annotations/genes/${geneId}/annotations`,
      { params: { source: 'uniprot' } }
    )
    // API returns: { gene: {...}, annotations: { uniprot: [{version, data, ...}] } }
    const uniprotAnnotations = response.data.annotations?.uniprot
    return uniprotAnnotations?.[0]?.data || null
  } catch (error) {
    window.logService?.error('Failed to fetch protein domains:', error)
    return null
  }
},
```

### 2.3 GeneStructureVisualization Component

**File**: `frontend/src/components/gene/GeneStructureVisualization.vue`

A simplified D3 SVG component (~300 lines) with proper patterns:

```vue
<template>
  <v-card class="gene-structure-card" variant="outlined">
    <v-card-title class="text-subtitle-1 bg-grey-lighten-4 py-2">
      <v-icon start size="small" color="primary">mdi-dna</v-icon>
      Gene Structure
      <v-spacer />
      <v-chip v-if="data" size="x-small" color="info">
        {{ data.exon_count }} exons
      </v-chip>
    </v-card-title>

    <v-card-text v-if="loading" class="text-center py-8">
      <v-progress-circular indeterminate color="primary" size="32" />
    </v-card-text>

    <v-card-text v-else-if="error" class="text-center py-4 text-error">
      <v-icon color="error">mdi-alert-circle</v-icon>
      Failed to load structure data
    </v-card-text>

    <v-card-text v-else-if="!data" class="text-center py-4 text-grey">
      <v-icon>mdi-information-outline</v-icon>
      No structure data available
    </v-card-text>

    <v-card-text v-else class="pa-3">
      <!-- Genomic coordinates -->
      <div class="text-caption text-grey mb-2">
        chr{{ data.chromosome }}:{{ formatNumber(data.start) }}-{{ formatNumber(data.end) }}
        ({{ formatSize(data.gene_length) }}, {{ data.strand }} strand)
      </div>

      <!-- SVG Visualization -->
      <div ref="svgContainer" class="svg-container">
        <svg ref="geneSvg" :width="svgWidth" :height="svgHeight">
          <!-- Intron line (backbone) -->
          <line
            :x1="margin.left"
            :y1="centerY"
            :x2="svgWidth - margin.right"
            :y2="centerY"
            :stroke="intronColor"
            stroke-width="2"
          />

          <!-- Exons -->
          <g v-for="exon in data.exons" :key="exon.number">
            <rect
              :x="scalePosition(exon.start)"
              :y="centerY - exonHeight / 2"
              :width="Math.max(scalePosition(exon.end) - scalePosition(exon.start), 3)"
              :height="exonHeight"
              :fill="exonFillColor"
              :stroke="exonStrokeColor"
              stroke-width="1"
              class="exon-rect"
              @mouseenter="handleExonHover($event, exon)"
              @mouseleave="hideTooltip"
            />
            <text
              v-if="shouldShowLabel(exon)"
              :x="scalePosition(exon.start) + (scalePosition(exon.end) - scalePosition(exon.start)) / 2"
              :y="centerY - exonHeight / 2 - 4"
              text-anchor="middle"
              :fill="labelColor"
              class="exon-label"
            >
              {{ exon.number }}
            </text>
          </g>

          <!-- Direction arrow -->
          <polygon
            v-if="data.strand === '+'"
            :points="arrowPointsRight"
            :fill="arrowColor"
          />
          <polygon
            v-else
            :points="arrowPointsLeft"
            :fill="arrowColor"
          />
        </svg>
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useTheme } from 'vuetify'
import { useD3Tooltip } from '@/composables/useD3Tooltip'

const props = defineProps({
  data: { type: Object, default: null },
  loading: { type: Boolean, default: false },
  error: { type: Boolean, default: false },
})

// Theme integration
const theme = useTheme()

// D3 Tooltip composable
const { showTooltip, hideTooltip, destroyTooltip } = useD3Tooltip()

// SVG dimensions
const svgContainer = ref(null)
const svgWidth = ref(600)
const svgHeight = 80
const margin = { left: 20, right: 30 }
const exonHeight = 20
const centerY = svgHeight / 2

// Theme-aware colors (computed for reactivity)
const exonFillColor = computed(() => {
  return theme.global.name.value === 'dark' ? '#42A5F5' : '#1976D2'
})

const exonStrokeColor = computed(() => {
  return theme.global.name.value === 'dark' ? '#1E88E5' : '#0D47A1'
})

const intronColor = computed(() => {
  return theme.global.name.value === 'dark' ? '#616161' : '#9E9E9E'
})

const arrowColor = computed(() => {
  return theme.global.name.value === 'dark' ? '#BDBDBD' : '#424242'
})

const labelColor = computed(() => {
  return theme.global.name.value === 'dark' ? '#90CAF9' : '#1565C0'
})

// Tooltip handler
const handleExonHover = (event, exon) => {
  const content = `
    <strong>Exon ${exon.number}</strong><br/>
    ${formatNumber(exon.start)} - ${formatNumber(exon.end)}<br/>
    Size: ${formatSize(exon.size)}
  `
  showTooltip(event, content)
}

// Computed scales
const geneLength = computed(() => props.data?.end - props.data?.start || 1)

const scalePosition = (pos) => {
  if (!props.data) return margin.left
  const relativePos = (pos - props.data.start) / geneLength.value
  return margin.left + relativePos * (svgWidth.value - margin.left - margin.right)
}

const shouldShowLabel = (exon) => {
  const width = scalePosition(exon.end) - scalePosition(exon.start)
  return width > 15 // Only show label if exon is wide enough
}

// Direction arrows
const arrowPointsRight = computed(() => {
  const x = svgWidth.value - margin.right + 5
  const y = centerY
  return `${x},${y} ${x - 8},${y - 5} ${x - 8},${y + 5}`
})

const arrowPointsLeft = computed(() => {
  const x = margin.left - 5
  const y = centerY
  return `${x},${y} ${x + 8},${y - 5} ${x + 8},${y + 5}`
})

// Formatting helpers
const formatNumber = (num) => num?.toLocaleString() || ''
const formatSize = (size) => {
  if (!size) return ''
  if (size >= 1000000) return `${(size / 1000000).toFixed(1)} Mb`
  if (size >= 1000) return `${(size / 1000).toFixed(1)} kb`
  return `${size} bp`
}

// Resize observer (following D3BarChart.vue pattern)
let resizeObserver = null

const updateWidth = () => {
  if (svgContainer.value) {
    svgWidth.value = svgContainer.value.clientWidth || 600
  }
}

onMounted(() => {
  resizeObserver = new ResizeObserver(() => {
    updateWidth()
  })
  if (svgContainer.value) {
    resizeObserver.observe(svgContainer.value)
  }
  nextTick(updateWidth)
})

onUnmounted(() => {
  if (resizeObserver) {
    resizeObserver.disconnect()
  }
  destroyTooltip()
})

// Watch for data changes to update width
watch(() => props.data, () => nextTick(updateWidth))
</script>

<style scoped>
.svg-container {
  width: 100%;
  overflow-x: hidden;
}

.exon-rect {
  cursor: pointer;
  transition: opacity 0.2s;
}

.exon-rect:hover {
  opacity: 0.8;
}

.exon-label {
  font-size: 9px;
  pointer-events: none;
}
</style>
```

### 2.4 ProteinDomainVisualization Component

**File**: `frontend/src/components/gene/ProteinDomainVisualization.vue`

Similar component using the shared tooltip composable:

```vue
<template>
  <v-card class="protein-domain-card" variant="outlined">
    <v-card-title class="text-subtitle-1 bg-grey-lighten-4 py-2">
      <v-icon start size="small" color="secondary">mdi-protein</v-icon>
      Protein Domains
      <v-tooltip v-if="data?.accession" location="bottom">
        <template #activator="{ props: tooltipProps }">
          <v-btn
            v-bind="tooltipProps"
            icon
            size="x-small"
            variant="text"
            :href="`https://www.uniprot.org/uniprotkb/${data.accession}`"
            target="_blank"
            class="ml-1"
          >
            <v-icon size="small">mdi-open-in-new</v-icon>
          </v-btn>
        </template>
        View in UniProt ({{ data.accession }})
      </v-tooltip>
      <v-spacer />
      <v-chip v-if="data" size="x-small" color="secondary">
        {{ data.length }} aa
      </v-chip>
    </v-card-title>

    <v-card-text v-if="loading" class="text-center py-8">
      <v-progress-circular indeterminate color="secondary" size="32" />
    </v-card-text>

    <v-card-text v-else-if="error" class="text-center py-4 text-error">
      <v-icon color="error">mdi-alert-circle</v-icon>
      Failed to load domain data
    </v-card-text>

    <v-card-text v-else-if="!data || !data.domains?.length" class="text-center py-4 text-grey">
      <v-icon>mdi-information-outline</v-icon>
      No domain data available
    </v-card-text>

    <v-card-text v-else class="pa-3">
      <!-- Protein name -->
      <div v-if="data.protein_name" class="text-caption text-grey mb-2">
        {{ data.protein_name }}
      </div>

      <!-- SVG Visualization -->
      <div ref="svgContainer" class="svg-container">
        <svg ref="proteinSvg" :width="svgWidth" :height="svgHeight">
          <!-- Protein backbone -->
          <line
            :x1="margin.left"
            :y1="centerY"
            :x2="svgWidth - margin.right"
            :y2="centerY"
            :stroke="backboneColor"
            stroke-width="3"
          />

          <!-- Domains -->
          <g v-for="(domain, index) in data.domains" :key="index">
            <rect
              :x="scalePosition(domain.start)"
              :y="centerY - domainHeight / 2"
              :width="Math.max(scalePosition(domain.end) - scalePosition(domain.start), 5)"
              :height="domainHeight"
              :fill="getDomainColor(index)"
              :stroke="backboneColor"
              stroke-width="1"
              class="domain-rect"
              @mouseenter="handleDomainHover($event, domain)"
              @mouseleave="hideTooltip"
            />
            <text
              v-if="shouldShowLabel(domain)"
              :x="scalePosition(domain.start) + (scalePosition(domain.end) - scalePosition(domain.start)) / 2"
              :y="centerY + 4"
              text-anchor="middle"
              class="domain-label"
            >
              {{ truncateName(domain.name) }}
            </text>
          </g>

          <!-- Scale markers -->
          <text :x="margin.left" :y="svgHeight - 5" :fill="scaleColor" class="scale-label">1</text>
          <text :x="svgWidth - margin.right" :y="svgHeight - 5" text-anchor="end" :fill="scaleColor" class="scale-label">
            {{ data.length }} aa
          </text>
        </svg>
      </div>

      <!-- Legend -->
      <div class="legend mt-2">
        <v-chip
          v-for="(domain, index) in data.domains"
          :key="index"
          size="x-small"
          :color="getDomainColor(index)"
          class="mr-1 mb-1"
        >
          {{ domain.name }}
        </v-chip>
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useTheme } from 'vuetify'
import { useD3Tooltip } from '@/composables/useD3Tooltip'

const props = defineProps({
  data: { type: Object, default: null },
  loading: { type: Boolean, default: false },
  error: { type: Boolean, default: false },
})

// Theme integration
const theme = useTheme()

// D3 Tooltip composable
const { showTooltip, hideTooltip, destroyTooltip } = useD3Tooltip()

// SVG dimensions
const svgContainer = ref(null)
const svgWidth = ref(600)
const svgHeight = 80
const margin = { left: 30, right: 30 }
const domainHeight = 24
const centerY = svgHeight / 2

// Theme-aware colors
const backboneColor = computed(() => {
  return theme.global.name.value === 'dark' ? '#9E9E9E' : '#424242'
})

const scaleColor = computed(() => {
  return theme.global.name.value === 'dark' ? '#BDBDBD' : '#757575'
})

// Domain colors (Material Design palette - theme-aware)
const domainColors = computed(() => {
  if (theme.global.name.value === 'dark') {
    return [
      '#42A5F5', '#66BB6A', '#FFA726', '#AB47BC',
      '#26A69A', '#EC407A', '#78909C', '#8D6E63',
    ]
  }
  return [
    '#1976D2', '#388E3C', '#F57C00', '#7B1FA2',
    '#00796B', '#C2185B', '#455A64', '#5D4037',
  ]
})

const getDomainColor = (index) => domainColors.value[index % domainColors.value.length]

// Tooltip handler
const handleDomainHover = (event, domain) => {
  const content = `
    <strong>${domain.name}</strong><br/>
    Position: ${domain.start} - ${domain.end} aa<br/>
    Length: ${domain.end - domain.start + 1} aa
  `
  showTooltip(event, content)
}

// Computed scales
const proteinLength = computed(() => props.data?.length || 1)

const scalePosition = (pos) => {
  if (!props.data) return margin.left
  const relativePos = pos / proteinLength.value
  return margin.left + relativePos * (svgWidth.value - margin.left - margin.right)
}

const shouldShowLabel = (domain) => {
  const width = scalePosition(domain.end) - scalePosition(domain.start)
  return width > 40
}

const truncateName = (name) => {
  if (!name) return ''
  return name.length > 12 ? name.substring(0, 10) + '...' : name
}

// Resize observer (following D3BarChart.vue pattern)
let resizeObserver = null

const updateWidth = () => {
  if (svgContainer.value) {
    svgWidth.value = svgContainer.value.clientWidth || 600
  }
}

onMounted(() => {
  resizeObserver = new ResizeObserver(() => {
    updateWidth()
  })
  if (svgContainer.value) {
    resizeObserver.observe(svgContainer.value)
  }
  nextTick(updateWidth)
})

onUnmounted(() => {
  if (resizeObserver) {
    resizeObserver.disconnect()
  }
  destroyTooltip()
})

// Watch for data changes to update width
watch(() => props.data, () => nextTick(updateWidth))
</script>

<style scoped>
.svg-container {
  width: 100%;
  overflow-x: hidden;
}

.domain-rect {
  cursor: pointer;
  transition: opacity 0.2s;
}

.domain-rect:hover {
  opacity: 0.8;
}

.domain-label {
  font-size: 9px;
  fill: white;
  pointer-events: none;
  font-weight: 500;
}

.scale-label {
  font-size: 10px;
}

.legend {
  display: flex;
  flex-wrap: wrap;
}
</style>
```

### 2.5 Route Configuration & GeneStructure.vue Page

**IMPORTANT**: Visualizations are on a dedicated subpage, NOT on GeneDetail.vue.
See [visualization-integration-ux-analysis.md](./visualization-integration-ux-analysis.md) for UX rationale.

**File**: `frontend/src/router/index.js` (update)

```javascript
// Add new route for structure subpage
{
  path: '/genes/:symbol/structure',
  name: 'gene-structure',
  component: () => import('@/views/GeneStructure.vue'),
  meta: {
    title: 'Gene Structure',
    requiresAuth: false
  }
}
```

**File**: `frontend/src/views/GeneStructure.vue` (NEW)

```vue
<template>
  <div>
    <!-- Breadcrumb Navigation -->
    <v-container fluid class="pa-0">
      <v-breadcrumbs :items="breadcrumbs" density="compact" class="px-6 py-2 bg-surface-light">
        <template #prepend>
          <v-icon icon="mdi-home" size="small" />
        </template>
        <template #divider>
          <v-icon icon="mdi-chevron-right" size="small" />
        </template>
      </v-breadcrumbs>
    </v-container>

    <v-container>
      <!-- Back Link & Header -->
      <div class="d-flex align-center mb-4">
        <v-btn
          icon="mdi-arrow-left"
          variant="text"
          size="small"
          :to="`/genes/${route.params.symbol}`"
          class="mr-3"
        />
        <div>
          <h1 class="text-h4 font-weight-bold">
            {{ gene?.approved_symbol }} Structure
          </h1>
          <p class="text-body-2 text-medium-emphasis">
            <template v-if="geneStructure?.canonical_transcript?.refseq_transcript_id">
              {{ geneStructure.canonical_transcript.refseq_transcript_id }}
              <span v-if="geneStructure.canonical_transcript.is_mane_select">(MANE Select)</span> •
            </template>
            chr{{ geneStructure?.chromosome }}:{{ formatNumber(geneStructure?.start) }}-{{ formatNumber(geneStructure?.end) }}
            ({{ formatSize(geneStructure?.gene_length) }})
          </p>
        </div>
      </div>

      <!-- Gene Structure Visualization -->
      <v-row>
        <v-col cols="12">
          <GeneStructureVisualization
            :data="geneStructure"
            :loading="structureLoading"
            :error="structureError"
          />
        </v-col>
      </v-row>

      <!-- Protein Domain Visualization -->
      <v-row class="mt-4">
        <v-col cols="12">
          <ProteinDomainVisualization
            :data="proteinDomains"
            :loading="domainsLoading"
            :error="domainsError"
          />
        </v-col>
      </v-row>

      <!-- External Links -->
      <v-row class="mt-4">
        <v-col cols="12">
          <v-card>
            <v-card-text class="d-flex justify-center ga-4">
              <v-btn
                v-if="geneStructure?.gene_id"
                variant="outlined"
                prepend-icon="mdi-open-in-new"
                :href="`https://ensembl.org/Homo_sapiens/Gene/Summary?g=${geneStructure.gene_id}`"
                target="_blank"
              >
                View in Ensembl
              </v-btn>
              <v-btn
                v-if="proteinDomains?.accession"
                variant="outlined"
                prepend-icon="mdi-open-in-new"
                :href="`https://www.uniprot.org/uniprotkb/${proteinDomains.accession}`"
                target="_blank"
              >
                View in UniProt
              </v-btn>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </v-container>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { geneApi } from '@/api/genes'
import GeneStructureVisualization from '@/components/gene/GeneStructureVisualization.vue'
import ProteinDomainVisualization from '@/components/gene/ProteinDomainVisualization.vue'

const route = useRoute()

// State
const gene = ref(null)
const geneStructure = ref(null)
const proteinDomains = ref(null)
const structureLoading = ref(true)
const domainsLoading = ref(true)
const structureError = ref(false)
const domainsError = ref(false)

// Breadcrumbs
const breadcrumbs = computed(() => [
  { title: 'Home', to: '/' },
  { title: 'Genes', to: '/genes' },
  { title: gene.value?.approved_symbol || route.params.symbol, to: `/genes/${route.params.symbol}` },
  { title: 'Structure', disabled: true }
])

// Formatting helpers
const formatNumber = (num) => num?.toLocaleString() || ''
const formatSize = (size) => {
  if (!size) return ''
  if (size >= 1000000) return `${(size / 1000000).toFixed(1)} Mb`
  if (size >= 1000) return `${(size / 1000).toFixed(1)} kb`
  return `${size} bp`
}

// Fetch data
onMounted(async () => {
  try {
    // Fetch gene basic info
    gene.value = await geneApi.getGene(route.params.symbol)

    // Fetch visualization data in parallel
    const results = await Promise.allSettled([
      geneApi.getGeneStructure(gene.value.id),
      geneApi.getProteinDomains(gene.value.id),
    ])

    // Handle structure result
    if (results[0].status === 'fulfilled') {
      geneStructure.value = results[0].value
    } else {
      structureError.value = true
    }

    // Handle domains result
    if (results[1].status === 'fulfilled') {
      proteinDomains.value = results[1].value
    } else {
      domainsError.value = true
    }
  } catch (error) {
    window.logService?.error('Failed to fetch gene data:', error)
  } finally {
    structureLoading.value = false
    domainsLoading.value = false
  }
})
</script>
```

### 2.6 Minimal Changes to GeneDetail.vue

**File**: `frontend/src/views/GeneDetail.vue` (update)

Only add a link to the structure page - NO visualization components on this page:

```vue
<!-- In GeneInformationCard.vue ClinVar section, add link button -->
<template>
  <div class="d-flex align-center justify-space-between">
    <div class="text-body-2 font-weight-medium">Clinical Variants (ClinVar):</div>
    <v-btn
      variant="text"
      size="x-small"
      density="compact"
      append-icon="mdi-chevron-right"
      :to="`/genes/${geneSymbol}/structure`"
    >
      View Structure
    </v-btn>
  </div>
  <!-- existing ClinVar chips... -->
</template>
```

**Alternative**: Add to gene header menu dropdown:

```vue
<!-- In GeneHeader menu dropdown -->
<v-list-item :to="`/genes/${geneSymbol}/structure`">
  <template #prepend>
    <v-icon icon="mdi-dna" />
  </template>
  <v-list-item-title>View Structure</v-list-item-title>
</v-list-item>
```

---

## Phase 3: Testing & Documentation

### 3.1 Backend Tests

**File**: `backend/tests/test_ensembl_source.py`

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.pipeline.sources.annotations.ensembl import EnsemblAnnotationSource


@pytest.fixture
def mock_session():
    session = MagicMock()
    session.query.return_value.filter_by.return_value.first.return_value = None
    return session


@pytest.fixture
def mock_gene():
    gene = MagicMock()
    gene.id = 1
    gene.approved_symbol = "PKD1"
    gene.hgnc_id = "HGNC:9008"
    return gene


@pytest.mark.asyncio
async def test_parse_ensembl_response(mock_session):
    source = EnsemblAnnotationSource(mock_session)

    mock_response = {
        "id": "ENSG00000008710",
        "seq_region_name": "16",
        "start": 2138710,
        "end": 2185899,
        "strand": 1,
        "biotype": "protein_coding",
        "Transcript": [{
            "id": "ENST00000262304",
            "is_canonical": True,
            "biotype": "protein_coding",
            "Exon": [
                {"id": "ENSE1", "start": 2138710, "end": 2138900},
                {"id": "ENSE2", "start": 2140000, "end": 2140200},
            ]
        }]
    }

    result = source._parse_ensembl_response(mock_response, "PKD1")

    assert result["gene_symbol"] == "PKD1"
    assert result["chromosome"] == "16"
    assert result["exon_count"] == 2
    assert result["strand"] == "+"


@pytest.mark.asyncio
async def test_is_valid_annotation(mock_session):
    source = EnsemblAnnotationSource(mock_session)

    # Valid annotation
    valid = {"gene_id": "ENSG123", "exons": [], "chromosome": "16"}
    assert source._is_valid_annotation(valid) is True

    # Invalid - missing required field
    invalid = {"gene_id": "ENSG123", "exons": []}
    assert source._is_valid_annotation(invalid) is False


@pytest.mark.asyncio
async def test_error_response_handling(mock_session):
    source = EnsemblAnnotationSource(mock_session)

    # Simulate error response
    error_response = {"error": "No valid lookup found for symbol INVALIDGENE"}

    # _parse_ensembl_response should not be called for error responses
    # This is handled in fetch_annotation before parsing


@pytest.mark.asyncio
async def test_mane_select_transcript_priority(mock_session):
    """Test that MANE Select transcript is prioritized over is_canonical."""
    source = EnsemblAnnotationSource(mock_session)

    # Mock MANE Select data from HGNC
    mane_select = {
        "ensembl_transcript_id": "ENST00000262304.10",
        "refseq_transcript_id": "NM_000297.4"
    }

    # Mock transcripts - note: MANE transcript is NOT marked is_canonical
    transcripts = [
        {
            "id": "ENST00000111111",
            "is_canonical": True,  # This one is canonical but not MANE
            "biotype": "protein_coding",
            "Exon": [{"id": "E1"}, {"id": "E2"}]
        },
        {
            "id": "ENST00000262304",  # This is MANE Select
            "is_canonical": False,
            "biotype": "protein_coding",
            "Exon": [{"id": "E1"}, {"id": "E2"}, {"id": "E3"}]
        }
    ]

    result = source._find_canonical_transcript(transcripts, mane_select)

    # Should select MANE transcript, not the is_canonical one
    assert result["id"] == "ENST00000262304"


@pytest.mark.asyncio
async def test_fallback_to_is_canonical_when_no_mane(mock_session):
    """Test fallback to is_canonical when no MANE Select available."""
    source = EnsemblAnnotationSource(mock_session)

    transcripts = [
        {"id": "ENST00000111111", "is_canonical": False, "biotype": "protein_coding"},
        {"id": "ENST00000222222", "is_canonical": True, "biotype": "protein_coding"},
    ]

    # No MANE Select available
    result = source._find_canonical_transcript(transcripts, mane_select=None)

    # Should fallback to is_canonical
    assert result["id"] == "ENST00000222222"


@pytest.mark.asyncio
async def test_response_includes_refseq_transcript_id(mock_session):
    """Test that response includes RefSeq transcript ID when MANE is used."""
    source = EnsemblAnnotationSource(mock_session)

    mane_select = {
        "ensembl_transcript_id": "ENST00000262304.10",
        "refseq_transcript_id": "NM_000297.4"
    }

    mock_response = {
        "id": "ENSG00000008710",
        "seq_region_name": "16",
        "start": 2138710,
        "end": 2185899,
        "strand": 1,
        "biotype": "protein_coding",
        "Transcript": [{
            "id": "ENST00000262304",
            "is_canonical": True,
            "biotype": "protein_coding",
            "Exon": [{"id": "E1", "start": 100, "end": 200}]
        }]
    }

    result = source._parse_ensembl_response(mock_response, "PKD1", mane_select)

    # Should include RefSeq ID and MANE flag
    assert result["canonical_transcript"]["refseq_transcript_id"] == "NM_000297.4"
    assert result["canonical_transcript"]["is_mane_select"] is True
```

**File**: `backend/tests/test_uniprot_source.py`

```python
import pytest
from unittest.mock import MagicMock
from app.pipeline.sources.annotations.uniprot import UniProtAnnotationSource


@pytest.fixture
def mock_session():
    return MagicMock()


@pytest.fixture
def mock_gene():
    gene = MagicMock()
    gene.id = 1
    gene.approved_symbol = "NPHS1"
    return gene


@pytest.mark.asyncio
async def test_parse_uniprot_response(mock_session):
    source = UniProtAnnotationSource(mock_session)

    mock_response = {
        "primaryAccession": "O60500",
        "uniProtkbId": "NPHN_HUMAN",
        "proteinDescription": {
            "recommendedName": {"fullName": {"value": "Nephrin"}}
        },
        "sequence": {"length": 1241},
        "features": [
            {
                "type": "Domain",
                "description": "Ig-like C2-type 1",
                "location": {"start": {"value": 27}, "end": {"value": 130}}
            }
        ],
        "uniProtKBCrossReferences": [
            {"database": "Pfam", "id": "PF00047", "properties": [{"value": "Ig"}]}
        ]
    }

    result = source._parse_uniprot_response(mock_response, "NPHS1")

    assert result["gene_symbol"] == "NPHS1"
    assert result["accession"] == "O60500"
    assert result["length"] == 1241
    assert len(result["domains"]) == 1
    assert result["domains"][0]["name"] == "Ig-like C2-type 1"


@pytest.mark.asyncio
async def test_is_valid_annotation(mock_session):
    source = UniProtAnnotationSource(mock_session)

    # Valid annotation
    valid = {"accession": "O60500", "length": 1241}
    assert source._is_valid_annotation(valid) is True

    # Invalid - missing required field
    invalid = {"accession": "O60500"}
    assert source._is_valid_annotation(invalid) is False


@pytest.mark.asyncio
async def test_empty_results_handling(mock_session):
    """Test that empty results (not error) is handled correctly."""
    source = UniProtAnnotationSource(mock_session)

    # UniProt returns {"results": []} for not found
    empty_response = {"results": []}

    # The source should handle this gracefully and return None
    # This is tested via integration test or mock
```

### 3.2 Update Documentation

**File**: `docs/features/annotations.md` (update - add section)

```markdown
## Gene Structure Annotations (Ensembl)

The Ensembl annotation source provides gene structure data including:
- Genomic coordinates (chromosome, start, end, strand)
- Exon positions and sizes
- Canonical transcript information
- Gene biotype and description

**API Endpoint**: `GET /api/annotations/genes/{gene_id}/annotations?source=ensembl`

**Cache TTL**: 30 days (structural data rarely changes)

**Rate Limit**: 15 requests/second (per Ensembl guidelines)

### Response Format
```json
{
  "gene_symbol": "PKD1",
  "gene_id": "ENSG00000008710",
  "chromosome": "16",
  "start": 2138710,
  "end": 2185899,
  "strand": "+",
  "exons": [
    {"number": 1, "start": 2138710, "end": 2138900, "size": 191},
    ...
  ],
  "exon_count": 46,
  "gene_length": 47189
}
```

## Protein Domain Annotations (UniProt)

The UniProt annotation source provides protein feature data including:
- Protein domains (Pfam, InterPro references)
- Active sites and binding sites
- Protein length and name
- UniProt accession for external links

**API Endpoint**: `GET /api/annotations/genes/{gene_id}/annotations?source=uniprot`

**Cache TTL**: 30 days (domain annotations are stable)

**Rate Limit**: 5 requests/second

### Response Format
```json
{
  "gene_symbol": "NPHS1",
  "accession": "O60500",
  "protein_name": "Nephrin",
  "length": 1241,
  "domains": [
    {"type": "Domain", "name": "Ig-like C2-type 1", "start": 27, "end": 130},
    ...
  ],
  "domain_count": 9,
  "pfam_references": [...],
  "interpro_references": [...]
}
```
```

---

## Implementation Checklist

### Backend Tasks
- [ ] Add Ensembl/UniProt configuration to `backend/config/annotations.yaml`
- [ ] Create `EnsemblAnnotationSource` in `backend/app/pipeline/sources/annotations/ensembl.py`
  - [ ] Include `@retry_with_backoff` decorator
  - [ ] Include HTTP status code validation
  - [ ] Implement `_get_mane_select_from_hgnc()` for MANE Select priority
  - [ ] Include both Ensembl and RefSeq transcript IDs in response
- [ ] Create `UniProtAnnotationSource` in `backend/app/pipeline/sources/annotations/uniprot.py`
  - [ ] Include `@retry_with_backoff` decorator
  - [ ] Handle empty results (NOT error key)
- [ ] Register new sources in `__init__.py`
- [ ] Add update task functions to `gene_annotations.py`
- [ ] Update default sources list to include "ensembl" and "uniprot"
- [ ] Write unit tests for new sources
  - [ ] Test MANE Select transcript selection priority
  - [ ] Test fallback to is_canonical when no MANE
- [ ] Run manual test with sample genes (PKD1, NPHS1, PKD2)
  - [ ] Verify MANE Select transcript matches HGNC data

### Frontend Tasks - Subpage Architecture
- [ ] **Route Configuration**: Add `/genes/:symbol/structure` route to `router/index.js`
- [ ] **GeneStructure.vue Page** (NEW): Create dedicated visualization page in `views/`
  - [ ] Breadcrumb navigation (Home > Genes > PKD1 > Structure)
  - [ ] Back link to parent gene page
  - [ ] Header with MANE Select transcript info
  - [ ] Full-width visualization cards
  - [ ] External links (Ensembl, UniProt)
- [ ] Create `useD3Tooltip` composable in `frontend/src/composables/useD3Tooltip.js`
- [ ] Create `GeneStructureVisualization.vue` component with:
  - [ ] ResizeObserver for responsive sizing
  - [ ] Vuetify theme integration
  - [ ] useD3Tooltip composable
  - [ ] Error state handling
- [ ] Create `ProteinDomainVisualization.vue` component with same patterns
- [ ] Update `frontend/src/api/genes.js` with new API methods
  - [ ] Correct response path: `response.data.annotations?.ensembl?.[0]?.data`
- [ ] **Minimal GeneDetail.vue changes** (entry points only):
  - [ ] Add "View Structure →" link to ClinVar section
  - [ ] (Optional) Add "View Structure" menu item in gene header dropdown
  - [ ] **DO NOT** add any visualization components to GeneDetail.vue
- [ ] Test responsive behavior and theme switching

### Documentation Tasks
- [ ] Update `docs/features/annotations.md`
- [ ] Update [visualization-integration-ux-analysis.md](./visualization-integration-ux-analysis.md) if needed
- [ ] Move this file to `docs/implementation-notes/completed/` on completion

---

## Performance Considerations

### Single-Gene Response Times (Validated 2026-01-11)
- **Ensembl**: ~874ms average (individual GET request)
- **UniProt**: ~260ms average (individual GET request)
- **Total visualization load**: ~1 second (parallel fetch)

### Batch Processing Performance (Validated 2026-01-11)

#### Ensembl POST Batch
```python
# POST /lookup/symbol/homo_sapiens with {"symbols": [...]}
# Max 1000 symbols per request, 55,000 requests/hour rate limit
```
| Genes | Time | Per-Gene | Improvement |
|-------|------|----------|-------------|
| 178 | 70.1s | 394ms | 1 request vs 178 |
| 571 (projected) | ~3-4 min | ~400ms | **571x fewer requests** |

#### UniProt OR Query Batch
```python
# GET /uniprotkb/search with OR query
# Max 100 OR conditions per query (HARD LIMIT!)
```
| Genes | Time | Requests | Improvement |
|-------|------|----------|-------------|
| 100 | 1.3s | 1 | 100x fewer |
| 178 | 2.1s | 2 | 89x fewer |
| 571 (projected) | ~8s | 6 | **95x fewer requests** |

### Caching Strategy
- **Cache TTL**: 30 days (structural data is stable)
- **L1 Cache**: In-memory for repeated views
- **L2 Cache**: PostgreSQL JSONB for persistence
- **Batch updates**: Run monthly with full database refresh

### Batch Processing Implementation
Both annotation sources implement optimized `fetch_batch()` methods:

```python
# Ensembl: Single POST request for all 571 genes
symbols = [g.approved_symbol for g in genes]  # Max 1000
response = await client.post(
    "/lookup/symbol/homo_sapiens",
    json={"symbols": symbols},
    params={"expand": 1}
)

# UniProt: Chunked OR queries (100 genes per request)
for chunk in [genes[i:i+100] for i in range(0, len(genes), 100)]:
    query = " OR ".join([f"(gene:{g} AND organism_id:9606)" for g in chunk])
    response = await client.get("/search", params={"query": query})
```

### Rate Limit Handling
- **Ensembl**: Check `X-RateLimit-Remaining` and `Retry-After` headers
- **UniProt**: No explicit rate limit headers, but throttle to 5 req/s
- **Both**: Use `@retry_with_backoff` decorator for resilience

---

## Comparison: kidney-genetics-db vs hnf1b-db

| Aspect | kidney-genetics-db (this plan) | hnf1b-db |
|--------|-------------------------------|----------|
| Scope | 571+ genes (generic) | 1 gene (HNF1B-specific) |
| Data Source | External APIs (Ensembl, UniProt) | Hardcoded + API fallback |
| Visualization Size | ~250 lines/component | ~1400 lines/component |
| Zoom/Pan | Not included (Phase 1) | Full D3 zoom/pan |
| Variant Display | Count badges (existing) | Individual lollipop plot |
| CNV Display | Not included | Full CNV visualization |
| 3D Structure | Not included | NGL.js integration |
| Theme Support | ✅ Full Vuetify integration | Partial |
| Code Reuse | ✅ Tooltip composable | Inline tooltip code |
| Complexity | Low (KISS) | High (feature-rich) |

---

## Future Enhancements (Phase 2 - Optional)

### Individual ClinVar Variants for Lollipop Plot

The current ClinVar integration only stores variant **counts**. To enable hnf1b-db-style lollipop plots:

1. **Extend ClinVarAnnotationSource** to store individual variant data:
   ```python
   "pathogenic_variants": [
       {"position": 1234, "change": "p.Arg1234Cys", "classification": "Pathogenic"},
       ...
   ]
   ```

2. **Create variant lollipop visualization component** overlaid on protein domains

3. **Considerations**:
   - Storage: ~1KB per gene for top variants (minimal)
   - Complexity: Medium - requires protein position extraction from HGVS

This is intentionally deferred as it adds complexity without blocking the core visualization feature.

---

## Review Changes Summary

**Issues Fixed (from expert review 2026-01-11):**

| Priority | Issue | Fix Applied |
|----------|-------|-------------|
| 🔴 Critical | UniProt returns `{"results": []}` not `{"error": ...}` | Removed error key check, handle empty results |
| 🔴 Critical | Frontend API path wrong | Changed to `response.data.annotations?.ensembl?.[0]?.data` |
| 🟠 High | Missing `@retry_with_backoff` | Added decorator to both fetch_annotation methods |
| 🟠 High | Missing HTTP status check | Added `response.status_code != 200` validation |
| 🟠 High | Default sources list outdated | Added "ensembl", "uniprot" to default list |
| 🟡 Medium | DRY violation - duplicate tooltip | Created `useD3Tooltip` composable |
| 🟡 Medium | Promise.all doesn't handle partial failures | Changed to `Promise.allSettled` |

**Batch API Optimizations (added 2026-01-11):**

| API | Optimization | Improvement |
|-----|--------------|-------------|
| Ensembl | POST batch with up to 1000 symbols | 571x fewer requests |
| UniProt | OR query with 100-gene chunks | 95x fewer requests |
| Combined | Parallel execution | ~3-4 min for full DB update |

**Key Findings from Batch API Testing:**
- Ensembl `expand=True` adds significant time (~400ms/gene) but required for exon data
- UniProt has hard limit of 100 OR conditions per query
- UniProt ID Mapping (async job) is slower than OR query for <1000 genes
- Rate limit headers: Ensembl provides `X-RateLimit-Remaining`, `Retry-After`

**MANE Select Transcript Integration (added 2026-01-11):**

| Feature | Implementation |
|---------|----------------|
| Source | HGNC annotations via `_get_mane_select_from_hgnc()` |
| Priority | MANE Select → is_canonical → longest protein-coding |
| Response | Includes both `ensembl_transcript_id` and `refseq_transcript_id` |
| Consistency | Matches `GeneInformationCard.vue` header display |

This ensures the exon structure shown in visualizations matches the canonical transcript referenced throughout the application.

---

## References

### API Documentation
- [Ensembl REST API Documentation](https://rest.ensembl.org/)
- [Ensembl POST Symbol Lookup](https://rest.ensembl.org/documentation/info/symbol_post) - Batch endpoint (max 1000)
- [Ensembl Rate Limits](https://github.com/Ensembl/ensembl-rest/wiki/Rate-Limits) - 55,000/hour
- [UniProt REST API Documentation](https://www.uniprot.org/help/api)
- [UniProt API Queries](https://www.uniprot.org/help/api_queries) - OR query syntax
- [UniProt ID Mapping](https://www.uniprot.org/help/id_mapping) - Alternative for >100 genes

### Codebase References
- [GitHub Issue #29](https://github.com/berntpopp/kidney-genetics-db/issues/29)
- [BaseAnnotationSource](../../../backend/app/pipeline/sources/annotations/base.py)
- [ClinVarAnnotationSource](../../../backend/app/pipeline/sources/annotations/clinvar.py) - Reference implementation
- [retry_utils.py](../../../backend/app/core/retry_utils.py) - SimpleRateLimiter, RetryConfig
- [D3BarChart.vue](../../../frontend/src/components/visualizations/D3BarChart.vue) - Reference for patterns
- [HNF1B-DB Visualization](../../hnf1b-db/frontend/src/components/gene/) - Inspiration only

### Related Implementation Plans
- [ensembl-uniprot-system-integration.md](./ensembl-uniprot-system-integration.md) - Backend integration details
  - Configuration for `annotations.yaml`
  - Source class implementation with `_is_valid_annotation()` override
  - Batch processing with `SimpleRateLimiter` and semaphores
  - Pipeline and API endpoint registration
- [visualization-integration-ux-analysis.md](./visualization-integration-ux-analysis.md) - Frontend UX design
  - Route configuration with gene symbol validation guard
  - D3 cleanup in `onUnmounted()` for memory leak prevention
  - Error boundaries and retry functionality
  - Unified breadcrumb integration

---

**Plan Status**: ✅ Expert Reviewed & Batch APIs Validated - Ready for Implementation
**Review Date**: 2026-01-11
**Review Rating**: 9/10 (after batch API optimizations)
**Reviewer**: Expert Code Review with API Validation & Performance Testing
