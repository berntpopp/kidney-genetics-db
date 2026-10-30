# Tool policy for curation agents (include in every curator/judge prompt)

## Order of preference
1. GeneFoundry MCP tools (provenance, citations, caching, rate limits).
2. A direct public API call only for a capability GeneFoundry lacks, and only from this list:
   - PubMed → ClinVar records citing a paper: NCBI elink/efetch (until clinvar-link#119 ships).
3. Never write your own scrapers or bulk downloads.

## Failure handling (GeneFoundry errors are machine-readable; obey them)
| error_code / signal | do |
|---|---|
| `upstream_unavailable`, `retryable: true` | wait `retry_after_s` (default 10 s), retry **at most 2 times**, then take the fallback below |
| `rate_limited` | wait `retry_after_s`, retry once; reduce parallel calls |
| `invalid_input` | fix the arguments named in `field_errors`; **never resend unchanged** |
| `not_found` | try another identifier form (rsID ↔ coordinates ↔ HGVS; GRCh37 → `dataset: gnomad_r2_1`) |
| "Unknown tool" | re-run `search_tools`, then call again |

## Fallback routes
- **HGVS → genomic coordinates/rsID**: `clinvar_get_variant(identifier="NM_…(GENE):c.…")` (fast, local
  index; the full/standard response holds coordinates and rsID) → else `vep_annotate_variant` (Ensembl,
  may time out ~45 s) → else `litvar_search_genetic_variants`.
- **Allele frequency**: `gnomad_resolve_variant_id(rsID or CHROM-POS-REF-ALT)` →
  `gnomad_get_variant_frequencies`. Use the highest continental population AF and **ignore
  "remaining", "asj", "fin" and "mid"** for the cap (gnomAD's grpmax convention) until gnomad-link exposes
  the filtering AF (faf95).
- **Paywalled paper**: PubMed → ClinVar (OMIM text in `<Description>`, `<Comment>` or
  `<Attribute Type="Description">`; drop any sentence naming a ClinGen/GenCC classification) → later
  case series → mark `variant_source: not_given`.

## When everything fails
Record it, never guess: `"af_checked": false, "af_check_error": "<tool + error_code>"`. An unchecked
frequency is **not** evidence of rarity. A variant that carries points with an unchecked AF gets a
reviewer flag.
