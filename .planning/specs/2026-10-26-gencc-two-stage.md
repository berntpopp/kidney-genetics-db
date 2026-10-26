# Scoring: two-stage GenCC sub-score

- **Date:** 2026-10-26
- **Status:** Decided (formula fixed by the maintainer before evaluation; α and
  the penalty were not tuned on the results)
- **Issue:** #330
- **Migration:** Alembic `0006` (`evidence_classification_weights`, GenCC branch only);
  conflict rule replaced in `0008` (DiStefano Level 3; see v2)

## Problem

The GenCC sub-score (`evidence_classification_weights.classification_weight`
for `source_name = 'GenCC'`) is the `MAX` of fixed classification weights. One
strong submission scores the same as several agreeing ones, and submitter
disagreement (DiStefano et al. 2022) is not reflected.

## Input

One `gene_evidence` row per gene with `source_name = 'GenCC'`. Its
`evidence_data -> 'submissions'` array holds one object per kidney-related GenCC
submission, written by `backend/app/pipeline/sources/unified/gencc.py`
(`_extract_gene_info`); the formula reads only its `classification` and
`submitter` keys (e.g. `"Definitive"`, `"Labcorp Genetics (formerly Invitae)"`).
Classifications are compared case-insensitively after trimming.

## Formula

Class weights (unchanged) and ordinal ranks:

| classification (lower-cased) | weight | rank |
|---|---:|---:|
| definitive | 1.0 | 6 |
| strong | 0.8 | 5 |
| moderate | 0.6 | 4 |
| supportive | 0.5 | none (unranked; see Post-evaluation correction) |
| limited | 0.4 | 2 |
| disputed evidence | 0.2 | 1 |
| no known disease relationship | 0.0 | 0 |
| refuted evidence | 0.0 | 0 |
| anything else (unknown, empty, NULL) | 0.0 | none (ignored for agreement and conflict) |

1. **Quality (stage 1).** `Q` = maximum weight over all submissions, ClinGen's
   included. This is exactly today's `MAX`. The gene's *top class* is the
   highest rank among its submissions (the class giving `Q`; ranks and positive
   weights are in the same order, so it is unique whenever `Q > 0`).
2. **Counted submitters.** Distinct non-empty `submitter` strings, excluding
   ClinGen, which is already a separate source (148 of the 349 GenCC genes on
   the 2026-10-26 development snapshot carry a ClinGen GenCC submission; #282).
   Excluded strings, matched exactly: **`ClinGen`** (the only ClinGen spelling
   among the 13 distinct submitter strings on that snapshot). Each counted
   submitter contributes its *strongest ranked* classification for this gene
   (a submitter may submit several kidney diseases for one gene; those are
   different assertions, not disagreement). Submitters with only unranked
   classifications are ignored.
3. **Agreement count.** `n` = number of counted submitters whose strongest
   ranked class equals the top class. If none does (for example the top class
   comes only from ClinGen), `n = 1`, so the score keeps `Q`.
4. **Consensus (stage 2).** `C = min(1, Q × (1 + α · ln n))`, `α = 0.1`.
   One submitter: `ln 1 = 0`, so `C = Q`.
5. **Conflict.** DiStefano et al. 2022 (*Genet Med*, PMC7613247), Level 3:
   "a conflict was defined as a Limited/Disputed/Refuted assertion versus a
   Moderate/Strong/Definitive assertion", between submissions with the same
   gene, disease term and mode of inheritance. Group the gene's submissions by
   (`disease_curie`, `moi_curie`); submissions missing either key are left
   out. If, in any group, the counted submitters' strongest ranked classes in
   that group include at least one Definitive, Strong or Moderate **and** at
   least one Limited, Disputed Evidence, Refuted Evidence or No Known Disease
   Relationship, subtract `P = 0.1` (once per gene). Supportive is in neither
   set. Zero or one counted submitter in a group never conflicts. (Since v2;
   see below.)
6. **Final.** `max(0, C − P)` (with `P = 0` when there is no conflict), as
   `numeric` (the existing column type).
7. **Fallback.** A row whose `submissions` is missing, not an array, or empty
   uses today's `MAX` over `classifications`, unchanged.

Worked examples (same disease and MOI unless stated): single Definitive →
1.0. Two non-ClinGen Strong submitters →
`0.8 × (1 + 0.1 ln 2) = 0.85545`. Strong and Limited from two submitters →
`0.8 − 0.1 = 0.7`. Moderate and Limited → `0.6 − 0.1 = 0.5`. Strong and
Moderate → `0.8`. Definitive and Moderate from two labs → `1.0` (no
conflict). Limited and No Known Disease Relationship → `0.4` (no conflict).
Strong (lab) and Supportive (Orphanet) → `0.8`. ClinGen Limited and lab
Definitive → `1.0` (ClinGen is not counted). Strong and Disputed Evidence →
`0.7`. Three labs Definitive AR and one Limited AD → `1.0` (different MOI).
Lab A Strong AR and Limited AD, lab B Moderate AD → `0.8 − 0.1 = 0.7` (A's
Strong AR does not hide its Limited AD). Strong and Limited for different
diseases → `0.8`. Missing `disease_curie` → no conflict. Four Definitive
submitters → `min(1, 1.1386) = 1.0`.

## Post-evaluation correction (2026-10-26)

Made **after** seeing the first before/after results (kept in the audit as
"v1 (Supportive ranked)"). It is a definitional correction, not tuning: α,
`P` and the `≥ 2`-rank rule are unchanged.

- **Change:** `supportive` has no conflict rank (it is treated like an
  unknown class for conflict). It still sets `Q` through its weight (0.5) and
  still counts for agreement when it is the top class, by class equality.
- **Why:** Supportive is not an ordinal grade between Moderate and Limited.
  DiStefano et al. 2022, *Genet Med* (PMC7613247): "The exception is for
  Orphanet and OMIM, two well-established public resources, which are mapping
  to the less granular term supportive, given that these resources do not
  distinguish between Limited, Moderate, Strong and Definitive." On the
  snapshot all 181 Supportive submissions come from Orphanet; in v1, 94 of the
  147 penalized genes were penalized only because of a Supportive class.
- **Stricter than DiStefano's conflict definition.** DiStefano et al. define a
  conflict as "a Limited/Disputed/Refuted assertion versus a
  Moderate/Strong/Definitive assertion". The maintainer's `≥ 2`-rank rule also
  penalizes Definitive vs Moderate (ranks 6 and 4), which that definition does
  not. After the correction 53 genes are penalized on the snapshot: 45 meet
  DiStefano's definition and 8 are penalized only for Definitive vs Moderate
  (all their counted classes are Moderate or stronger; Strong vs Moderate is
  one rank and never penalized). Source: `v010_conflict_breakdown.sql` in the audit
  directory. This stricter rule was kept in v0.10.0; v2 replaces it.

## v2: published conflict definition, Level 3 (2026-10-26, migration `0008`)

Decided **after** the v0.10.0 evaluation above. The home-made `≥ 2`-rank
conflict rule, and the post-hoc patch that left Supportive unranked to repair
it, are replaced by the definition of the paper the issue cites (DiStefano et
al. 2022, *Genet Med*, PMC7613247), verbatim: "a conflict was defined as a
Limited/Disputed/Refuted assertion versus a Moderate/Strong/Definitive
assertion". The paper computes it at three levels, verbatim:

- "“Level 1 conflicts” were those conflicting entries where the gene matched,
  without regard to the mode of inheritance or disease term, but gene-disease
  validity terms conflicted"
- "“Level 2 conflicts” were those conflicting entries where gene and mode of
  inheritance matched but gene-disease validity terms conflicted. These were
  agnostic of submitted disease terms."
- "“Level 3 conflicts” were those where gene, disease term, and mode of
  inheritance all matched but gene-disease validity terms conflicted"

We use **Level 3**: different diseases or modes of inheritance of one gene
are different claims that may both be valid, not disagreement.

- **Group:** submissions of one GenCC evidence row (one gene) with the same
  `raw_data.disease_curie` (MONDO) and `raw_data.moi_curie` (HPO), compared
  exactly after trimming. A submission whose `disease_curie` or `moi_curie`
  is missing or empty never forms a conflict (conservative: a missing key
  must not merge unrelated records). On the snapshot all 967 submissions have
  both keys. "Unknown" MOI (`HP:0000005`) is its own value.
- **Conflict:** within a group, each counted (non-ClinGen) submitter
  contributes its strongest ranked class in that group; the gene is
  penalized once (`P = 0.1`) if any group has one Definitive/Strong/Moderate
  and one Limited/Disputed Evidence/Refuted Evidence/No Known Disease
  Relationship. Supportive is in neither set because, per the same paper, it
  does not grade.
- **No Known Disease Relationship:** NKDR is not named in the definition; we
  place it with Refuted following the paper's "Limited or below (including
  121 No Known Disease Relationship)" grouping; affects C4B only on the
  snapshot.
- Ranks are still used for the top class and agreement; `n` is still
  agreement on the top class across the gene. Nothing else changes (Q, n, α,
  `P`, cap before penalty, floor, fallback, `numeric`).

An unreleased first version of `0008` (commit `ac4c83a`, amended) applied
the definition to each submitter's strongest class across the whole gene,
which matches none of the paper's levels: it penalized 9 genes with no Level 3
conflict (8 differ only by mode of inheritance, e.g. NPHS2: three labs
Definitive AR vs Ambry Limited AD; TBC1D1 by disease term) and missed SLC2A9
(Labcorp Limited AD vs Ambry Moderate AD, hidden by Labcorp's Strong AR).

Effect on the snapshot (`conflict_breakdown.sql` in the audit): 37 genes are
penalized (45 gene-level, 53 under v0.10.0). Versus v0.10.0, 17 genes lose
the penalty and SLC2A9 gains it; no tier changes. `0006` is not edited because
v0.10.0 shipped it; `0008` replaces the view and its downgrade restores the
`0006` definition exactly.

## Deliberately omitted

- **Percentile spread.** The issue mentions "plus a percentile spread"; it is
  not part of the decided formula. GenCC stays a classification-weighted
  source and is not mixed with the count percentiles used by other sources.
- Submitter-specific reliability weights and disease-level (MONDO) grouping:
  not requested; every non-ClinGen submitter counts equally and the gene-level
  record is scored as a whole.

## Scope and invariants

- Only the GenCC branch of `evidence_classification_weights` changes; ClinGen,
  output columns and types are unchanged, so `CREATE OR REPLACE VIEW` keeps
  dependent views. `gene_scores` (and `gene_distribution_analysis`) are
  refreshed only where they are materialized views. Stored evidence rows are
  not modified. The `0006` downgrade restores the `MAX` view exactly; the
  `0008` downgrade restores the `0006` view exactly.
- `percentage_score` divisor and tier thresholds are unchanged (#333).
- Before/after numbers: `.planning/audits/gencc-two-stage-2026-10/`.
