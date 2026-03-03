# Data Annotation Pipeline Assessment

**Created**: 2026-02-28
**Last Updated**: 2026-03-03
**Status**: Mostly implemented. 18/20 recommendations done, all 10 source optimizations shipped.

---

## Implementation Status Summary

### Source Optimizations — ALL DONE

| Source | Commit | Change | Status |
|--------|--------|--------|--------|
| gnomAD | `155a07a` | Bulk TSV download + API fallback | DONE |
| HGNC | `b475775` | Bulk JSON download + REST fallback | DONE |
| GTEx | `341fd48` | Bulk GCT download | DONE |
| HPO | `a101b3a` | `genes_to_phenotype.txt` bulk file | DONE |
| ClinVar | `dc34fed` | Bulk summary + API key support | DONE |
| Ensembl | `e71c55c`, `e5f2b0a` | MANE file + GTF bulk parsing | DONE |
| UniProt | `478f59e` | ID Mapping API (single job) | DONE |
| PubTator | `4204afc` | Gene-centric queries | DONE |
| MPO/MGI | `71b5b6f`, `618fd14` | Bulk MouseMine + file cache fix | DONE |
| ClinGen | `7ce0c30` | CSV bulk download | DONE |

### Architecture & Code — 8/10 DONE

| # | Recommendation | Commit | Status |
|---|---------------|--------|--------|
| 1 | N+1 subqueries → CTE/JOIN in gene listing | Pre-assessment | DONE |
| 2 | Functional index on `UPPER(approved_symbol)` | `7c82239` | DONE |
| 3 | Progress tracker interval → 5s | `03f6c60` | DONE |
| 4 | Thread-safe ARQ pool singleton | Pre-assessment | DONE |
| 5 | Replace `inspect.stack()` | Pre-assessment | DONE |
| 6 | Bulk upserts (`ON CONFLICT DO UPDATE`) | `6545139` | DONE |
| 7 | Align thread pool (10) with connection pool (10+15) | Pre-assessment | DONE |
| 8 | Parallelize statistics summary queries | `d428a74` | DONE |
| 9 | ClinVar streaming (fix OOM) | `8e40335` | DONE |
| 10 | Pipeline stability (stale lock, thread-safe cache) | `c0d89fa` | DONE |

### Bug Fixes (discovered during implementation)

| Bug | Commit | Description |
|-----|--------|-------------|
| GTEx tissue keys | `8482b69` | GCT file uses human-readable names; normalized to API-style IDs |
| MPO/MGI empty phenotypes | `618fd14` | `fetch_batch()` bypassed file cache + InterMine `size=0` returns 0 rows |
| ClinVar OOM | `8e40335` | Two-pass streaming parser for 414 MB variant file |

---

## Remaining Work (2 items)

### R1. Replace CROSS JOIN in `source_overlap_statistics`

**Severity**: LOW (was MEDIUM — gene count grew but view refresh is still fast enough)

The materialized view uses self-cross-join. Could be optimized with intersection-based approach:
```sql
SELECT source_a, source_b, COUNT(DISTINCT gene_id) as overlap_count
FROM gene_evidence e1
JOIN gene_evidence e2 ON e1.gene_id = e2.gene_id AND e1.source_name < e2.source_name
GROUP BY source_a, source_b
```

### R2. Expose cache stats via admin API

Cache statistics are tracked (`CacheStats`: hits, misses, evictions, hit rate) but not surfaced in monitoring. Could expose via `/api/admin/cache/stats`.

---

## Current Pipeline Profile

**Gene count**: 5,080+ curated genes (up from 571 at assessment time)
**Sources**: 10 active annotation sources
**Architecture**: All sources now use bulk file downloads or batch APIs

| Source | Annotation Count | Last Update | Approach |
|--------|----------------:|-------------|----------|
| hgnc | 5,080 | 2026-03-01 | Bulk JSON download |
| gnomad | 8,480 | 2026-03-01 | Bulk TSV download |
| ensembl | 6,450 | 2026-03-02 | GTF + MANE bulk files |
| hpo | 5,080 | 2026-03-01 | Bulk `genes_to_phenotype.txt` |
| mpo_mgi | 5,080 | 2026-03-02 | MouseMine bulk + file cache |
| gtex | 4,926 | 2026-03-02 | Bulk GCT file |
| uniprot | 4,911 | 2026-03-01 | ID Mapping API |
| clinvar | 3,934 | 2026-03-01 | Bulk summary file |
| descartes | 4,630 | 2026-03-01 | Bulk CSV |
| string_ppi | 1,941 | 2026-03-01 | Local file processing |

---

## Known External API Constraints

| Service | Constraint | Workaround |
|---------|-----------|------------|
| JAX API (`informatics.jax.org`) | reCAPTCHA blocks server-side requests | Static file cache at `backend/app/data/mpo_kidney_terms.json` (661 terms) |
| InterMine/MouseMine | `size=0` returns 0 rows (not unlimited) | Omit `size` param entirely |
| GTEx GCT file | Tissue names are human-readable (e.g., `"Kidney - Cortex"`) | `_normalise_tissue_id()` converts to API-style IDs |
| gnomAD bulk TSV | Autosomes only — X-linked genes absent | GraphQL API fallback for missing genes |

---

## Architecture Strengths (unchanged)

These patterns remain solid and should be preserved:

1. **Two-phase pipeline**: HGNC first → provides Ensembl IDs → parallel sources
2. **Multi-level error recovery**: per-call → per-gene → per-source → pipeline-wide
3. **L1+L2 cache**: In-memory LRU + PostgreSQL JSONB persistence
4. **Circuit breaker**: Prevents cascade failures on external API outages
5. **Batch mode cache invalidation**: Single namespace clear after bulk updates
6. **Event-driven WebSocket progress**: Event bus for real-time pipeline monitoring
7. **Non-blocking view refresh**: ThreadPoolExecutor with concurrent-first strategy
8. **Bulk file approach**: All major sources now use file downloads over per-gene APIs

---

## Historical Reference

The original assessment (2026-02-28) contained detailed per-source API analysis with live-tested URLs in sections 11.1-11.10. All source optimizations have been implemented. The research URLs and findings remain valid for future reference if any source needs to be re-evaluated.

Key archived commits implementing the full optimization roadmap:
```
155a07a feat: add gnomAD bulk TSV download with GraphQL API fallback
b475775 feat: add HGNC bulk JSON download with REST API fallback
341fd48 feat: add GTEx bulk GCT download with API fallback
a101b3a feat: add HPO bulk file download with API fallback
dc34fed feat: add ClinVar bulk summary + API key support
e71c55c feat: add MANE file for Ensembl RefSeq xrefs (571 GETs -> 1 download)
e5f2b0a perf: replace Ensembl REST API with GTF bulk file parsing
478f59e feat: switch UniProt to ID Mapping API (6 batches -> 1 job)
4204afc feat: switch PubTator to gene-centric queries (500+ pages -> 571 targeted)
71b5b6f feat: switch MPO/MGI to bulk MouseMine queries (1142 -> ~12 requests)
7ce0c30 feat: switch ClinGen to CSV bulk download (5 -> 1 request)
6545139 perf: batch fetch + bulk DB upsert in annotation pipeline
03f6c60 perf: increase progress tracker DB write interval to 5 seconds
d428a74 perf: parallelize statistics summary queries with asyncio.gather
c0d89fa fix: pipeline stability — stale lock recovery, thread-safe cache clear, inter-phase commits
8e40335 fix: ClinVar bulk parse OOM and idle-in-transaction timeout
8482b69 fix: normalize GTEx tissue keys and remove API fallback
618fd14 fix: MPO/MGI empty phenotypes — use file cache and fix InterMine size param
```
