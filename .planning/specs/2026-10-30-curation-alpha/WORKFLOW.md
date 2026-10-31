# Gene Curator → KGDB curation workflow (alpha)

One-shot: a curation is made in Gene Curator (GC), imported into KGDB once, and from then on lives
and is edited only in KGDB. GC never updates or retracts it; a new curation is a new import.

1. **Curate in Gene Curator.** An LLM agent uses GC's MCP (`/mcp`) plus GeneFoundry with
   `PROMPT_PRODUCTION.md`: adopt ClinGen where it exists, otherwise curate with explicit per-row
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

**Rules that matter**
- Only `scope_name = kidney-genetics`; unknown verdict, MOI or relationship values are rejected.
- A curation without a final classification (not yet approved in GC) is rejected.
- An adopted ClinGen classification (GC `adoption`) imports as methodology "ClinGen gene-disease
  validity (adopted)" with the expert panel, date and CGGV link in `adopted_clingen`, no points and
  possibly no PMIDs.
- Software agents GC credits (`contributions`, agentType software) are stored in `ai_agents` and
  shown as "AI-assisted (…)" next to the curator. A curator override of the point model is appended to the summary with its reason.
- Susceptibility association points come from `scores.association_total` (`scores.association`).
- Diagnostics that fail KGDB's schema are dropped and reported; the classification still imports.
- Re-uploading a curation_id is skipped. A GC re-curation (new curation_id) on an entity already in
  KGDB is reported as a conflict for a curator to compare.
- Susceptibility tiers follow #473 (Established / Likely / Uncertain / Refuted association).
- Methodology bundle: `docs/schemas/kidney-genetics/kgdb-methodology.json` in Gene Curator; after a
  change, a GC platform admin re-imports it (Schema Management → Import methodology, dry run first).

**Status (2026-10-31):** KGDB side live in v0.21.0. First end-to-end local pilot (GC PR #609 head):
agents curated NPHS2 and CLDN10 (full point model), PLA2R1 (susceptibility) and adopted DNAJB11
from ClinGen; a second GC user approved; all four imported and published in KGDB. GC gaps found are
gene-curator #610–#615. Open: the GC bundle is at draft iteration 3 while `PROMPT_PRODUCTION.md`
scores with iteration 8 rules (gene-curator #615), and GC has no field for per-row quotes or
reviewer flags (agents use `context_notes`).
