# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- **Clinical geneticists and nephrologists** checking how strong the kidney-disease evidence for a gene is while interpreting a patient case or assembling a gene panel.
- **Researchers and bioinformaticians** browsing, filtering and exporting gene lists, networks and statistics.
- **Curators and admins** curating gene-disease associations, reviewing staging and running data pipelines in `/admin`.

## Product Purpose

The Kidney-Genetics Database aggregates kidney-disease gene evidence from many authoritative sources (ClinGen, GenCC, PanelApp, HPO, curated literature, diagnostic panels, PubTator and annotation sources) into one transparent, reproducible evidence score and tier per gene. Success means a user can see quickly how well supported a gene is, why, and from which sources, and can cite it.

## Positioning

A reproducible, provenance-aware evidence score for kidney genes. Every number traces back to named sources, versioned releases and documented scoring (the successor of the published kidney-genetics R pipeline), with expert-reviewed associations on top.

## Operating Context

- Public read-only site plus read-only API and MCP server; authenticated admin area for curation and pipelines.
- Code releases are SemVer with a Zenodo software DOI; data releases are CalVer with dataset DOIs. A manuscript describes the scoring.

## Capabilities and Constraints

- Frontend: Vue 3, TypeScript, Vite SSG with build-time prerendering, Tailwind CSS v4, shadcn-vue primitives in `frontend/src/components/ui/`, Pinia.
- Light and dark themes.
- Evidence tier vocabulary is fixed: comprehensive support, multi-source support, established support, preliminary evidence, minimal evidence (plus no evidence). Names and meanings follow the scoring and the manuscript.

## Brand Commitments

- Keep the existing KGDB logo and the name "Kidney-Genetics Database".
- Keep the tier names and their meaning unchanged.
- Visual direction (confirmed 2026-10-27): systematize the incumbent shadcn-vue look into one enforced design and color language; not a new visual world.

## Evidence on Hand

- Real gene, evidence, score and release data from the production API; source provenance on every evidence item.
- UI/UX audit baseline and tooling: `.planning/audits/ui-ux/` (rubric, scores, runs).
- Do not fabricate counts, sources, citations or claims.

## Product Principles

1. Evidence first: the score, its tier and its sources are always visible and traceable.
2. One language for evidence: the same source, tier or identifier looks and behaves the same on every view.
3. Identifiers are never bare: every ontology ID (HPO, MONDO, OMIM, HGNC) shows its human-readable name and a link.
4. Research density without noise: scannable tables and cards for expert users.
5. Reproducible and citable: versions, releases and provenance stay visible.

## Accessibility & Inclusion

WCAG 2.2 AA in both light and dark themes is required: contrast, keyboard paths with visible focus, named controls, no colour-only meaning. Public pages must keep build-time prerendering and SEO behaviour.
