# Pipeline Optimization Design

**Date**: 2026-03-01
**Status**: Approved
**Based on**: `.planning/annotation-pipeline-assessment.md`

## Goal

Optimize the annotation pipeline by migrating data sources from per-gene API calls to bulk file downloads (~4x speedup), applying architecture fixes, and ensuring complete data parity via golden file validation. Per-source research determines whether API fallback code is kept or removed.

## Constraints

- **Data parity**: Core scientific values (IDs, scores, classifications, phenotypes) must match exactly before/after. Metadata differences acceptable.
- **API fallback**: Research per-source. Keep if bulk file has coverage gaps that matter. Drop if 100% covered to avoid repo bloat.
- **Version alignment**: Investigate API-vs-bulk-file version differences per source. Flag for manual decision if they diverge.
- **Incremental delivery**: Each source migration is independently deployable and validated.

## Architecture

### BulkDataSourceMixin

New mixin added to source classes alongside existing `UnifiedDataSource` base:

```python
class BulkDataSourceMixin:
    """Mixin for sources that can fetch all data in a single bulk download."""

    bulk_file_url: str = ""
    bulk_cache_ttl_hours: int = 168  # 7 days
    bulk_file_format: str = "tsv"    # tsv, json, gct, txt

    async def download_bulk_file(self) -> Path:
        """Download and cache the bulk file locally."""

    async def parse_bulk_file(self, path: Path) -> dict[str, dict]:
        """Parse bulk file into {gene_key: annotation_data}. Source-specific."""

    async def lookup_gene(self, gene_key: str) -> dict | None:
        """Look up a single gene from parsed bulk data."""
```

Each migrated source gains the mixin:

```python
class GnomADUnifiedSource(BulkDataSourceMixin, UnifiedDataSource):
    bulk_file_url = "https://storage.googleapis.com/.../gnomad.v4.1.constraint_metrics.tsv"
    api_fallback_enabled = True  # Researched: needed for X-linked genes

    async def fetch_annotation(self, gene):
        result = await self.lookup_gene(gene.approved_symbol)
        if result is None and self.api_fallback_enabled:
            result = await self._fetch_via_api(gene)
        return result
```

### Golden File Validation

`backend/app/pipeline/golden_file.py`:

- `export_golden_snapshot(db, output_path)` — Exports `gene_annotations` table as JSON grouped by (gene_symbol, source), separating core values from metadata.
- `compare_snapshots(before, after)` — Diffs core values per gene per source. Float tolerance for scores.
- `generate_parity_report(diff)` — Human-readable report of matches, mismatches, missing genes, new genes.

Core value keys per source:

| Source | Core Values |
|--------|------------|
| gnomAD | pLI, LOEUF, lof_z, mis_z, syn_z, oe_lof |
| HGNC | hgnc_id, entrez_id, ensembl_gene_id, locus_type, gene_family |
| GTEx | tissue expression TPM values |
| HPO | phenotype IDs, names, disease associations |
| ClinVar | pathogenic/likely_pathogenic counts, total alleles |
| Ensembl | transcript IDs, RefSeq NM IDs |
| UniProt | accession, protein domains |
| PubTator | publication count, top PMIDs |

## Implementation Phases

### Phase 0: Foundation

1. Golden file validation framework (`golden_file.py`)
2. Export baseline golden snapshot (run current pipeline)
3. N+1 subquery fix in `genes.py` — replace 3 correlated subqueries with CTE/JOIN
4. Thread safety — `threading.Lock` on ARQ pool, thread-safe L1 cache wrapper
5. Pool alignment — ThreadPoolExecutor → 10-15 workers, connection pool → 10+15
6. `BulkDataSourceMixin` base class
7. Replace `inspect.stack()` with `asyncio.get_running_loop()` in `base.py`

### Phase 1: P0 Sources (biggest speedup)

8. **gnomAD → bulk TSV** (285s → 5s)
   - File: `gnomad.v4.1.constraint_metrics.tsv` (91 MB)
   - Research: count X-linked genes missing from bulk among our 571
   - Decision: keep API fallback if >5 genes missing
   - Golden file comparison

9. **HGNC → bulk JSON** (571 API calls → 1 download)
   - File: `hgnc_complete_set.json` (~30 MB)
   - 100% coverage — drop API code
   - Golden file comparison

### Phase 2: P1 Sources

10. **GTEx → bulk GCT** (1,142 API calls → 1 download)
    - File: `gene_median_tpm.gct.gz` (~7-9 MB)
    - Research: v8 vs v10 alignment
    - Golden file comparison

11. **HPO → genes_to_phenotype.txt** (1,142 API calls → 1 download)
    - File: `genes_to_phenotype.txt` (19.6 MB)
    - Research: does file include frequency and disease fields?
    - Golden file comparison

12. **ClinVar → hybrid bulk + API key**
    - Add NCBI API key support (3.4x speedup, near-zero code change)
    - File: `gene_specific_summary.txt` (3.5 MB) for aggregate counts
    - Research: do we use molecular consequence data?
    - Stream variants for memory fix
    - Golden file comparison

### Phase 3: P2 Sources

13. **Ensembl → MANE file** (571 xref GETs → 1 file)
    - File: `MANE.GRCh38.v1.5.summary.txt.gz` (1.1 MB)
    - Keep existing batch POST for core data
    - Golden file comparison

14. **UniProt → ID Mapping API** (6 batches → 1 job)
    - Fixes PKD1/PRKD1 ambiguity bug
    - Research: domain data availability
    - Golden file comparison

15. **PubTator → FTP or gene-centric** (hundreds of pages → 1 download or 571 targeted queries)
    - Research: 713MB file parse time vs API
    - Golden file comparison

### Phase 4: P3 Sources + Polish

16. MPO/MGI → MouseMine Lists API (571 → ~3 requests)
17. ClinGen → CSV bulk download (5 → 1)
18. Bulk upserts — `insert().on_conflict_do_update()` in base.py
19. Progress tracker interval → 5-10 seconds
20. Cache stats admin endpoint
21. Parallelize statistics summary queries

### Phase 5: Final Validation

22. Full pipeline run with all optimizations
23. Compare against original golden snapshot — full parity report
24. Performance benchmarks — before/after timing

## Per-Source API Fallback Research Questions

| Source | Question | Decision Criteria |
|--------|----------|------------------|
| gnomAD | How many of 571 genes are X-linked and missing from bulk TSV? | Keep API if >5 genes missing |
| GTEx | Does v8 GCT match current API data? Should we upgrade to v10? | Version must match current data |
| HPO | Does `genes_to_phenotype.txt` include frequency and disease_id? | Drop API if fields present |
| ClinVar | Do we use molecular consequence data from variant-level API? | Drop variant API if unused |
| UniProt | Does ID Mapping return domain annotations? | Keep search API if domains missing |
| PubTator | Is 713MB file download+parse faster than streaming API? | Use whichever is faster and simpler |
| MPO/MGI | Is MouseMine Lists API reliable as primary (no bulk file available)? | Must work consistently |

## Expected Outcomes

- **Pipeline runtime**: 13-15 min → 3-4 min (~4x speedup)
- **API calls**: ~5,000+ → ~20 (for sources with fallback)
- **Rate limit risk**: Eliminated for bulk-migrated sources
- **Network error surface**: Reduced by ~95%
- **Data parity**: Core values identical, validated per source

## Files Changed (estimated)

| Category | Files |
|----------|-------|
| New | `golden_file.py`, `BulkDataSourceMixin` in base or new file |
| Modified (sources) | gnomad, hgnc, gtex, hpo, clinvar, ensembl, uniprot, pubtator, mpo |
| Modified (architecture) | `genes.py`, `arq_client.py`, `cache_service.py`, `base.py`, `database.py`, `statistics.py`, `progress_tracker.py` |
| New (admin) | Cache stats endpoint in `admin.py` |
| Migration | Functional index on `UPPER(approved_symbol)` |
