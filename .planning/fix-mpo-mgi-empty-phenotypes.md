# Fix MPO/MGI Empty Phenotypes

**Status**: RESOLVED (2026-03-02) — Commits `618fd14`, `1aa5f21`

## Problem

All 5,080 genes showed `phenotype_count: 0` and empty `phenotypes: []` for Mouse Phenotypes (MGI/MPO).

## Root Causes (two bugs)

### Bug 1: `fetch_batch()` bypassed file cache → hit reCAPTCHA-blocked JAX API

The JAX API (`www.informatics.jax.org`) is now behind Google reCAPTCHA. Server-side requests get a captcha challenge page instead of JSON.

- `fetch_annotation()` (single-gene path) correctly loads MPO terms from the file cache at `app/data/mpo_kidney_terms.json` before falling back to the JAX API
- `fetch_batch()` (batch path used by the pipeline) called `fetch_kidney_mpo_terms()` directly → JAX API → reCAPTCHA → silent failure → only root term `MP:0005367` (1 term instead of 661)
- MouseMine queries worked fine, but filtering against 1 root term matched almost nothing

### Bug 2: InterMine `size=0` returns 0 rows (not unlimited)

Both `_bulk_query_phenotypes()` and `_bulk_query_zygosity()` passed `size=0` to the InterMine API, intending "unlimited results". InterMine interprets `size=0` as "return 0 rows". The queries returned empty result sets for every gene.

## Fix

### Code changes (`backend/app/pipeline/sources/annotations/mpo_mgi.py`)

1. **Extracted `_load_mpo_terms()` method** — shared file-cache-first logic used by both `fetch_annotation()` and `fetch_batch()`. Loads from `app/data/mpo_kidney_terms.json` (661 kidney-related MPO terms), falls back to JAX API only if file doesn't exist.

2. **Removed `size=0`** from bulk InterMine query params — omitting the `size` parameter lets InterMine return all results (default behavior).

### Test updates (`backend/tests/test_mpo_mgi_bulk.py`)

- Updated `test_fetch_batch_loads_mpo_terms_once` to mock `_load_mpo_terms` instead of `fetch_kidney_mpo_terms`
- Added `test_load_mpo_terms_uses_file_cache` — verifies file cache is used and API is NOT called
- Added `test_load_mpo_terms_falls_back_to_api` — verifies API fallback when file doesn't exist

## Results After Pipeline Re-run

```
total_genes | with_phenotypes | has_kidney | avg_pheno_count | max_pheno_count
-----------+-----------------+------------+-----------------+----------------
      5080 |            1110 |       1110 |             5.1 |              57
```

PKD1 example: 41 kidney phenotypes, first = "kidney cortex cyst", 1 mouse ortholog (Pkd1).

## Verification

- 515 tests pass (14 MPO/MGI-specific)
- Lint + typecheck + format clean
- Frontend confirmed via Playwright: PKD1 gene detail page shows "Mouse Phenotypes (MGI/MPO): 41 phenotypes"

## Key Learnings

- **InterMine API**: `size=0` means "return 0 rows", NOT unlimited. Omit the param entirely for unlimited results.
- **Pipeline endpoint**: `/pipeline/update` uses FastAPI `BackgroundTasks` (in-process), not ARQ. No worker needed.
- **MPO term cache**: `backend/app/data/mpo_kidney_terms.json` contains 661 terms. The JAX API can no longer be used programmatically to refresh them.

## Future Consideration

The JAX API reCAPTCHA block means we can no longer programmatically refresh MPO terms. Options:
1. **Use the existing cache file** (sufficient for now — MPO ontology is stable)
2. **Download MPO OBO file** from https://github.com/obophenotype/mammalian-phenotype-ontology and parse locally
3. **Use OLS4 API** (https://www.ebi.ac.uk/ols4/api) as alternative source for MPO term hierarchy
