# Kidney-Genetics Database

## What This Is

A modern web platform for curating and exploring kidney disease-related genes. Python/FastAPI backend with Vue 3/TypeScript frontend, PostgreSQL database. 5,000+ genes with evidence scoring from 7 authoritative sources, admin panel with pipeline management, interactive network analysis, and build-time prerendered pages for SEO. Currently at v0.2.0 with comprehensive SEO optimization.

## Core Value

Researchers, nephrologists, and geneticists can quickly find, explore, and evaluate kidney disease gene evidence with confidence in the data quality and completeness.

## Completed Milestones

### v0.2.0 — Frontend Migration + UI/Pipeline Improvements (2026-03-01)

- Complete TypeScript migration (strict mode) across all 40+ JS files and 73 Vue components
- Replaced Vuetify 3 with shadcn-vue (Reka UI primitives) + Tailwind CSS v4
- TanStack Table, vee-validate + Zod, Lucide icons, Vitest component tests
- Pipeline: session isolation, 10 source bulk optimizations, gene count 571 → 5,080+
- UI: Network Analysis redesign, Gene Structure tabs, fixed footer

### SEO Optimization (2026-03-29, PRs #99 + #115)

- Build-time prerendering via vite-ssg (6 static pages SSG + 5,000+ gene page meta shells)
- BioSchemas Gene 1.0-RELEASE structured data on all gene pages
- Homepage redesign: 6 sections, ~300 words, inline search, citation block, audience cards
- Lighthouse: Accessibility 100, SEO 100, Best Practices 100
- D3 tree-shaking, gzip/brotli pre-compression, immutable asset caching
- FAQ page with FAQPage schema, 404 page, robots.txt with AI crawlers, llms.txt
- Sitemap: lastmod timestamps, structure pages, Cache-Control header
- Lighthouse CI in GitHub Actions (a11y/SEO/best-practices >= 90)
- Primary color darkened for WCAG AA contrast compliance

### v0.1.0 — Production-Ready Alpha (pre-GSD)

- Core platform with gene browsing, evidence scoring, 9 annotation sources
- JWT auth, admin panel, WebSocket pipeline progress, ARQ worker

## Requirements

### Validated

- Gene browsing with server-side pagination, sorting, and filtering
- Gene detail pages with multi-source evidence display
- Evidence scoring and tier system (0-100, Definitive/Strong/Moderate/Minimal)
- 7 annotation source integrations (PanelApp, ClinGen, GenCC, HPO, PubTator, Literature, Diagnostic Panels)
- Additional annotation sources: ClinVar, gnomAD, GTEx, Ensembl, HGNC, UniProt, STRING PPI, MPO/MGI
- JWT authentication with admin/curator/public roles
- Admin panel (user management, cache control, pipeline management, backups, settings)
- Network analysis with Cytoscape visualization and clustering
- Dashboard with D3.js statistical visualizations (UpSet plots, bar/donut charts)
- Gene structure visualization with ClinVar variant overlay
- Dark/light theme support
- TypeScript strict mode, Tailwind CSS v4, shadcn-vue, TanStack Table
- Build-time prerendering (vite-ssg) for SEO
- BioSchemas Gene 1.0-RELEASE structured data
- FAQ page with FAQPage schema
- Lighthouse CI (a11y/SEO/best-practices >= 90)
- WCAG AA contrast compliance

### Active

No active milestone. Next milestone TBD.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| shadcn-vue over PrimeVue | Full component ownership, Reka UI primitives, excellent TS support | Shipped v0.2.0 |
| Tailwind CSS v4 | 10x faster builds, CSS-first config | Shipped v0.2.0 |
| TanStack Table | Composable, headless, TS-first | Shipped v0.2.0 |
| vite-ssg for prerendering | Build-time SSG without Nuxt/SSR rewrite, fits existing Vue+Vite stack | Shipped SEO |
| BioSchemas Gene 1.0-RELEASE | Scientific database standard for gene structured data | Shipped SEO |
| Primary color darkened (sky-500→sky-600/700) | WCAG AA contrast compliance (2.77:1 → 5.93:1) | Shipped SEO |
| Build-time gene page shells | <30s build for 5,000+ pages vs hours for full SSG prerender | Shipped SEO |

---
*Last updated: 2026-03-29 — SEO optimization complete*
