# ClinVar Bulk variant_summary.txt.gz Migration

## Context

ClinVar is the slowest annotation source in the pipeline. It makes ~5000+ NCBI eUtils API calls (esearch + esummary per gene), rate-limited at 3 req/s without an API key = ~28 min. With an API key it's ~8 min. The `variant_summary.txt.gz` bulk file (414MB, updated weekly) contains all variant data we need and can be downloaded + parsed in ~1 min total.

Currently, `ClinVarAnnotationSource` already uses `BulkDataSourceMixin` but only for a lightweight pre-filter (`gene_specific_summary.txt`, 3.5MB) that tells us which genes have ClinVar data. All actual variant details still come from the API. This plan replaces the pre-filter with full bulk parsing of `variant_summary.txt.gz`, eliminating nearly all API calls.

**Tested results** (PKD1): bulk file yields 6,910 unique variants vs API's 6,917 (99.9% coverage). All 15 per-variant fields required for the frontend lollipop plots are derivable from the bulk file columns.

---

## Field Mapping: variant_summary.txt columns → annotation schema

### Direct mappings (9 fields)

| TSV Column | Annotation Field | Notes |
|---|---|---|
| `Name` | `title`, `cdna_change` | Full HGVS notation |
| `GeneSymbol` | `gene_symbol` | Grouping key; multi-gene rows use `;` separator |
| `ClinicalSignificance` | `classification` | Raw text (e.g., "Pathogenic") |
| `Type` | `variant_type` | e.g., "single nucleotide variant", "Deletion" |
| `Chromosome` | `chromosome` | e.g., "16" |
| `Start` | `genomic_start` | Integer genomic coordinate |
| `Stop` | `genomic_end` | Integer genomic coordinate |
| `ReviewStatus` | `review_status` | e.g., "criteria provided, single submitter" |
| `PhenotypeList` | traits (split on `\|`) | e.g., "Polycystic kidney disease, adult type" |

### Derived mappings (6 fields)

| Annotation Field | Derivation |
|---|---|
| `accession` | `f"VCV{int(VariationID):09d}"` |
| `protein_change` | Regex `\((p\..*?)\)` from Name column |
| `position` | Regex `[A-Z][a-z]{2}(\d+)` from protein_change |
| `category` | Classification text → `pathogenic\|likely_pathogenic\|vus\|benign\|likely_benign\|conflicting\|not_provided` |
| `confidence` | ReviewStatus → 0-4 stars (existing `_get_review_confidence_levels()` dict) |
| `effect_category` | HGVS inference from Name (see rules below) |

### HGVS → effect_category inference rules

| Pattern in Name | effect_category | molecular_consequences label |
|---|---|---|
| `(p.*Ter*)` (not `ext`) | `truncating` | `["nonsense"]` |
| `(p.*fs*)` | `truncating` | `["frameshift variant"]` |
| `(p.Xxx###Yyy)` where Xxx≠Yyy, Yyy≠Ter | `missense` | `["missense variant"]` |
| `del`/`dup`/`ins` without `fs` | `inframe` | `["inframe_indel"]` |
| `(p.*=)` | `synonymous` | `["synonymous variant"]` |
| `c.NNN+1`, `c.NNN+2`, `c.NNN-1`, `c.NNN-2` | `splice_region` | `["splice donor/acceptor variant"]` |
| `c.NNN+N` or `c.NNN-N` (N>2) | `intronic` | `["intron variant"]` |
| anything else | `other` | `["other"]` |

### Deduplication strategy

Variants appear in both GRCh38 and GRCh37 rows. Deduplicate by `VariationID`: prefer GRCh38 (priority 3) > GRCh37 (priority 2) > "na" (priority 1). This captures 6,910/6,917 variants (99.9%).

### Known fidelity gap

`molecular_consequences` is inferred from HGVS notation instead of curated API labels. Coverage is good for major types (missense, nonsense, frameshift, splice, synonymous, inframe) but may miss edge cases like "non-coding transcript variant" as a secondary label. The `effect_category` field (which drives frontend filtering/coloring) is unaffected.

---

## Tasks

### Task 1: Create HGVS parsing utilities module

**Create**: `backend/app/pipeline/sources/annotations/clinvar_utils.py`

Pure functions, no dependencies on DB/sessions, fully testable in isolation:

- `parse_protein_change(name: str) -> str` — extract `p.Xxx###Yyy` from HGVS Name
- `parse_protein_position(protein_change: str) -> int | None` — extract numeric position (reuse existing regex from `_parse_protein_position`)
- `infer_effect_category(name: str) -> str` — HGVS → effect_category (rules table above)
- `infer_molecular_consequences(name: str, effect_category: str) -> list[str]` — effect_category → SO term labels
- `map_classification(clinical_significance: str) -> str` — ClinicalSignificance → category
- `map_review_confidence(review_status: str, confidence_levels: dict[str, int]) -> int` — ReviewStatus → 0-4 stars
- `format_accession(variation_id: str) -> str` — `"12345"` → `"VCV000012345"`
- `parse_variant_row(row: dict[str, str], confidence_levels: dict[str, int]) -> dict[str, Any]` — parse one TSV row into the normalized variant dict matching `_parse_variant()` output schema

### Task 2: Unit tests for clinvar_utils

**Create**: `backend/tests/pipeline/test_clinvar_utils.py`

All `@pytest.mark.unit`. Test every function from Task 1 with edge cases:
- HGVS names with/without protein changes, complex patterns (extensions, frameshifts with stops)
- All classification categories including "Pathogenic/Likely pathogenic", "Uncertain significance; other"
- All review status levels including edge cases ("-", empty)
- Multi-consequence names, missing fields

### Task 3: Add streaming download to BulkDataSourceMixin

**Edit**: `backend/app/pipeline/sources/unified/bulk_mixin.py`

Add `download_bulk_file_streaming(force: bool = False) -> Path` method. Uses `httpx.AsyncClient.stream()` to write chunks to disk (65KB chunks, 300s timeout). Non-breaking addition — existing sources keep using `download_bulk_file()`.

### Task 4: Rewrite ClinVar bulk parsing

**Edit**: `backend/app/pipeline/sources/annotations/clinvar.py`

Major changes:

**4a.** Change `bulk_file_url` to `variant_summary.txt.gz` URL.

**4b.** Override `ensure_bulk_data_loaded()` to:
1. Call `download_bulk_file_streaming()` (not default `download_bulk_file()`)
2. Load target gene set from DB (`self._target_genes: set[str]`)
3. Call `parse_bulk_file()` on the `.gz` path directly
4. Store result in `self._bulk_data`

**4c.** Rewrite `parse_bulk_file(path: Path) -> dict[str, dict[str, Any]]`:
- Stream-decompress `.gz` with `gzip.open(path, "rt")`
- Phase 1: Collect best row per VariationID per gene (dedup by assembly priority)
- Phase 2: For each gene, build variant list from collected rows using `parse_variant_row()` from clinvar_utils, then call existing `_aggregate_variants()` to produce the final annotation
- Only process genes in `self._target_genes` (~571 genes out of ~19K in file)
- Handle multi-gene variants (GeneSymbol contains `;`)

**4d.** Rename `_aggregate_variants()` output keys for direct schema compatibility:
- `total_count` → `total_variants`
- `variant_type_counts` → `variant_types`
- Add `variant_summary` text and `last_updated` timestamp generation

**4e.** Extract existing API logic from `fetch_annotation()` into `_fetch_via_api(gene: Gene)`.

**4f.** Simplify `fetch_annotation()`: bulk lookup first → API fallback.

**4g.** Simplify `fetch_batch()`: load bulk once → dict lookups → collect API fallback list (matching gnomAD pattern in `backend/app/pipeline/sources/annotations/gnomad.py`).

**4h.** Remove `_gene_has_variants()` method (no longer needed).

### Task 5: Update existing ClinVar tests

**Edit**: `backend/tests/pipeline/test_clinvar_bulk.py`

Update `TestClinVarBulkParsing` to test the new `parse_bulk_file()` with variant_summary.txt format:
- Small TSV fixture (10-20 rows) mimicking variant_summary.txt columns
- GRCh38/GRCh37 deduplication by VariationID
- Multi-gene variants assigned to all matching genes
- Genes not in target set excluded
- Correct aggregation output schema

Add `TestClinVarBulkFetchBatch`:
- Mock bulk data, verify `fetch_batch()` returns bulk results without API calls
- Mock bulk data missing a gene, verify API fallback is called

Keep `TestClinVarNCBIApiKey` tests unchanged (API fallback still needs them).

### Task 6: Lint, typecheck, and run tests

```bash
make lint
cd backend && uv run mypy app/pipeline/sources/annotations/clinvar.py app/pipeline/sources/annotations/clinvar_utils.py app/pipeline/sources/unified/bulk_mixin.py --ignore-missing-imports
make test-unit
```

---

## Key files

| File | Action |
|------|--------|
| `backend/app/pipeline/sources/annotations/clinvar.py` | Major edit — bulk parsing, simplified fetch |
| `backend/app/pipeline/sources/annotations/clinvar_utils.py` | **New** — pure HGVS parsing functions |
| `backend/app/pipeline/sources/unified/bulk_mixin.py` | Edit — add streaming download method |
| `backend/tests/pipeline/test_clinvar_utils.py` | **New** — unit tests for parsing utils |
| `backend/tests/pipeline/test_clinvar_bulk.py` | Edit — update for new bulk format |

## Reference files (read-only, for patterns)

| File | Pattern to follow |
|------|---|
| `backend/app/pipeline/sources/annotations/gnomad.py` | Bulk lookup + API fallback in `fetch_batch()` |
| `backend/app/pipeline/sources/annotations/hpo.py` | Line-by-line TSV parsing with dedup in `parse_bulk_file()` |

---

## Verification

1. **Unit tests pass**: `cd backend && uv run pytest tests/pipeline/test_clinvar_utils.py tests/pipeline/test_clinvar_bulk.py -v`
2. **Lint + typecheck**: `make lint && cd backend && uv run mypy app/pipeline/sources/annotations/clinvar.py app/pipeline/sources/annotations/clinvar_utils.py --ignore-missing-imports`
3. **Full test suite**: `make test`
4. **Manual smoke test** (after pipeline run): Export golden snapshot, compare PKD1 variant counts and field presence against baseline
5. **Performance**: Download + parse should complete in <2 min vs previous ~28 min

## Performance expectations

| Metric | Before (API) | After (Bulk) | Improvement |
|--------|-------------|-------------|-------------|
| Requests | ~5000+ | 1 download | ~5000x fewer |
| Time | ~28 min (no key) / ~8 min (with key) | ~1-2 min | 8-28x faster |
| File size | N/A | 414 MB download | Cached 7 days |
| Memory | Low (per-gene) | ~100-200 MB (all target gene variants) | Acceptable |
