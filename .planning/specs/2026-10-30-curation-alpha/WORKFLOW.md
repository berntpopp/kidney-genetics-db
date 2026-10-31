# Gene Curator → KGDB curation workflow (v1)

One-shot: a curation is made in Gene Curator (GC), imported into KGDB once, and from then on lives
and is edited only in KGDB. GC never updates or retracts it; a new curation is a new import.

1. **Curate in Gene Curator.** An LLM agent uses GC's MCP (`/mcp`) plus GeneFoundry with
   `PROMPT_PRODUCTION.md`: record ClinGen where it exists and curate every entity with explicit per-row
   points and reviewer flags, then submit. A human GC reviewer approves (four-eyes in GC).
2. **Export.** From GC, export the approved `kidney-genetics` curations (`GET /api/v1/export/curations`,
   export v1) with a scope member's token; without one `evidence` is null, so no summary or
   diagnostics arrive (the report says so). Follow `next_cursor` and upload the pages as one JSON list.
3. **Upload to KGDB.** Admin → *Gene Curator import* (`/admin/gene-curator-import`), or
   `POST /api/admin/gene-curator/import` with the file. The file is checked against the pinned
   export schema (`backend/contract/gene_curator_export.snapshot.json`); a mismatch is rejected with
   the failing paths. The report lists created drafts, already-imported, conflicts (an existing KGDB
   record on the same gene/disease/MOI/relationship type), genes not in KGDB, rejected rows and
   dropped fields.
4. **Confirm in KGDB.** Imported drafts are owned by the inactive `gene-curator-import` account.
   A curator may submit and publish an unchanged import alone (GC's review covers it). Editing it
   makes the editor its curator, so a different curator must review before publishing.
   A row only an AI approved in GC (`approval_kind = "ai"`, read in `_approval` in
   `gene_curator_import.py`; field names pending GC #639) is imported **published**, marked
   "AI-reviewed · pending human review", until a KGDB curator marks it human-reviewed
   (`POST /api/curation/associations/{id}/human-review`) or publishes an edited version.

**Rules that matter**
- Only `scope_name = kidney-genetics`; unknown verdict, MOI or relationship values are rejected.
- A curation without a final classification (not yet approved in GC) is rejected.
- Our own curation of a ClinGen-curated entity carries ClinGen's statement in `clingen_reference`
  (same shape as `adoption`). It imports with our methodology, points and PMIDs, and ClinGen's panel,
  class, date and link in `adopted_clingen`, shown as "ClinGen: <class>". A final class that differs
  from ClinGen's needs `curator_classification_rationale` (else the row is rejected).
- The rationale (when the final class differs from the point model or ClinGen) is stored in
  `classification_rationale` and shown as "Why this class"; the synopsis is imported unchanged.
- A legacy adoption (GC `adoption`) imports as methodology "ClinGen gene-disease validity (adopted)"
  with no points and possibly no PMIDs. Only an adoption may have no PMIDs.
- Software agents GC credits (`contributions`, agentType software) are stored in `ai_agents` and
  shown as "AI-assisted (…)" next to the curator. A curator override of the point model keeps its reason in `classification_rationale`.
- Susceptibility association points come from `scores.association_total` (`scores.association`).
- Diagnostics that fail KGDB's schema are dropped and reported; the classification still imports.
- Re-uploading a curation_id is skipped. A GC re-curation (new curation_id) on an entity already in
  KGDB is reported as a conflict for a curator to compare.
- Susceptibility tiers follow #473 (Established / Likely / Uncertain / Refuted association).
- Methodology bundle: `docs/schemas/kidney-genetics/kgdb-methodology.json` in Gene Curator; after a
  change, a GC platform admin re-imports it (Schema Management → Import methodology, dry run first).

**Status (2026-10-31):** KGDB side live in v0.21.0; this branch adds adopted ClinGen
classifications, AI credit (`ai_agents`), the susceptibility `risk_allele` key and the
single-gene view. End-to-end runs on local Gene Curator: first at PR #609 head (NPHS2, CLDN10,
PLA2R1 rs4664308, DNAJB11 adopted), then on master 0fda2285 with methodology version 2
(iteration 8): MAGI2 (Strong, curator call over computed Definitive), PLA2R1 rs17831251 C
(Likely association, polygenic) beside the first PLA2R1 entity, and KCNJ16 adopted from ClinGen
with diagnostics. Agents curated via `/mcp`, a second GC user approved, all imported as drafts
and were published in the KGDB UI. GC gaps found are gene-curator #610–#615 (closed); remaining
GC friction is listed in the #448 PR.
