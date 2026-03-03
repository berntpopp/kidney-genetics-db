# Fix GTEx Tissue Key Format Mismatch

**Status**: RESOLVED (2026-03-02) — Commit `8482b69`

## Problem

After migrating GTEx from API-only to bulk GCT file download, the tissue keys in the database changed format:

- **GCT file**: `"Kidney - Cortex"`, `"Adipose - Visceral (Omentum)"` (human-readable)
- **GTEx API**: `"Kidney_Cortex"`, `"Adipose_Visceral_Omentum"` (underscore IDs)
- **Frontend expects**: underscore format (matches API)

The frontend checks `gtexData.tissues?.Kidney_Cortex` — with dashes in the DB, this was always `undefined`, so GTEx showed "No data" for all genes.

## Root Cause

`backend/app/pipeline/sources/annotations/gtex.py` `parse_bulk_file()` used GCT column headers as-is for tissue keys. The GCT file uses human-readable names, but the frontend was built against the API-style `tissueSiteDetailId` format.

## Fix

Added `_normalise_tissue_id()` function in `gtex.py` that converts GCT names to API-style IDs:

```
"Kidney - Cortex"                          → "Kidney_Cortex"
"Adipose - Visceral (Omentum)"             → "Adipose_Visceral_Omentum"
"Brain - Anterior cingulate cortex (BA24)" → "Brain_Anterior_cingulate_cortex_BA24"
"Brain - Spinal cord (cervical c-1)"       → "Brain_Spinal_cord_cervical_c-1"
```

Rules: replace ` - ` and spaces with `_`, strip parentheses (keep content), collapse double underscores.

Also removed the API fallback code path (no longer needed with bulk file approach).

## Results

- 5,080 genes annotated with normalized tissue keys in ~6 seconds
- Frontend correctly displays Cortex/Medulla TPM values

## Verification

- All tests pass
- Lint clean
- 10/10 tissue name normalization test cases pass
