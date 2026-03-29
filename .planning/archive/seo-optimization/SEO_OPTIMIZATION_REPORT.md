# KGDB SEO & Performance Optimization Report

> Generated: 2026-03-15
> Scope: Research & analysis — no code changes made
> Lighthouse audits: Run against local dev server (localhost:5173) — performance scores reflect dev mode (unminified, unbundled ESM). Production scores will differ.

## Executive Summary

**KGDB has zero Google-indexed pages.** A `site:kidney-genetics.org` search returns nothing. The root cause is that KGDB is a pure Vue.js SPA rendering into an empty `<div id="app"></div>` — search engines, social media crawlers, and AI crawlers see no content, no per-page meta tags, and no structured data. All 9 competitors use server-side rendering.

The biggest opportunity is that KGDB's published abstract already ranks on page 1 for key queries like "kidney disease gene database" and "kidney gene evidence scores" — but the website itself doesn't appear. With proper indexing, KGDB could realistically rank for 7+ keyword clusters. The niche is not dominated by any single database; academic papers and commercial labs fill the results, leaving room for a dedicated kidney genetics resource.

The recommended approach is a **build-time hybrid strategy**: use `vite-ssg` for ~8 static pages (full SSG with hydration) plus a lightweight build script that generates meta-only HTML shells for 5,000+ gene pages (correct `<title>`, `<meta>`, JSON-LD baked into the SPA shell). Total build time: **under 30 seconds**. No dynamic rendering, no SSR, no Nuxt rewrite — fits the existing Vue 3 + Vite + FastAPI stack.

## 1. Competitive Landscape

### 1.1 Competitor Profiles

| Competitor | Rendering | JSON-LD | Domain Authority | Content Depth | Kidney Focus |
|------------|-----------|---------|-----------------|---------------|-------------|
| OMIM | SSR | No | Very High (~80+) | Very Deep | General |
| GeneCards | SSR | Unknown (403) | Very High (~75+) | Very Deep | General |
| ClinGen | SSR | No | High (~65+) | Deep (curated) | 4 kidney panels |
| HGNC | SSR | No | High (~70+) | Moderate | General |
| Orphanet | SSR | **Yes (gold standard)** | Very High (~75+) | Deep | Rare diseases |
| PanelApp | SSR | No | High (~60+) | Moderate | Partial (panels) |
| GenCC | SSR (Livewire) | No | Moderate (~40-50) | Moderate | General |
| Nephromine/NephQTL | N/A | No | Low | Deep (expression) | Yes |
| **KGDB** | **CSR (SPA)** | **No** | **Very Low** | **Moderate** | **Yes (primary)** |

**Key insight**: ALL major competitors use SSR. KGDB is the only resource relying on client-side rendering. However, most competitors (except Orphanet) have **no JSON-LD structured data** — they rank on domain authority and content depth alone. Orphanet's `MedicalCondition` JSON-LD with cross-reference `MedicalCode` arrays is the gold standard to emulate.

**KGDB's unique advantage**: It is the only dedicated kidney disease gene database with multi-source evidence scoring. OMIM, GeneCards, ClinGen are pan-disease. Nephromine/NephQTL are kidney-focused but limited to expression data.

### 1.2 Keyword Gap Analysis

**Primary target keywords** (user-identified high priority):

| Keyword | Current Top Ranker | Difficulty | KGDB Opportunity |
|---------|-------------------|------------|-----------------|
| kidney disease gene database | PubMed/PMC papers, KGDB abstract at #9 | Low-Medium | **HIGH** — abstract already on p1, website should dominate |
| renal genetics database | Mayo Clinic Labs, academic papers | Medium | **HIGH** — no dedicated database ranks here |
| nephrology gene panel | Commercial labs (Mayo, Blueprint, Invitae) | High | **HIGH** — differentiate with curated evidence vs commercial panels |
| kidney gene curation | ClinGen (4 panels), KGDB abstract at #5 | Medium | **HIGH** — create dedicated methodology page |
| nephropathy gene list | Academic papers, OMIM | Low-Medium | **HIGH** — curated gene lists per nephropathy type |
| kidney genomics resource | NIDDK, academic papers | Medium | **HIGH** — position as the definitive resource |
| hereditary kidney disease genes | Patient orgs, hospitals, academic papers | Medium | **MEDIUM** — informational content page needed |
| kidney gene evidence scores | Academic papers, KGDB abstract at #5 | Low | **HIGH** — unique KGDB feature, should own this |
| polycystic kidney disease genes | UpToDate, GeneReviews, OMIM | High | **LOW** — dominated by clinical authorities |
| renal disease genetic testing genes | Commercial labs, patient orgs | High | **LOW** — commercial/transactional intent |

### 1.3 Content Gaps

Content competitors have that KGDB lacks:

| Content Type | Who Has It | Recommendation |
|-------------|-----------|----------------|
| Disease-centric gene pages | OMIM, Orphanet | Create `/diseases/adpkd`, `/diseases/alport-syndrome`, etc. listing all associated genes with evidence |
| Evidence methodology page | ClinGen (detailed SOP) | Create dedicated `/methodology` page explaining scoring system |
| Downloadable gene lists | OMIM, PanelApp, GenCC | Offer CSV/JSON gene lists per disease category |
| Human-readable API docs | PanelApp, GenCC | Create public API docs page beyond Swagger |
| Cross-coding mappings | Orphanet (ICD-10, ICD-11, MeSH, SNOMED CT) | Add disease code cross-references |
| Gene panel comparison | None | Compare KGDB against commercial testing panels — unique differentiator |
| Changelog/news | ClinGen, Orphanet | Database update log for freshness signals |

### 1.4 Backlink Opportunities

**Database registries** (submit KGDB for listing):
- re3data.org — Registry of Research Data Repositories
- FAIRsharing.org — Standards, databases, and policies
- bio.tools — ELIXIR tools registry
- dkNET — NIDDK Information Network
- Bioschemas.org — get listed as adopter after implementing BioSchemas

**Academic citation links**:
- NIDDK Kidney Genetics & Genomics program page — submit as community resource
- NAR Database Issue — publish a full database paper (highest-value backlink in bioinformatics)
- KDIGO guidelines — submit for inclusion in future guideline updates

**Institutional cross-links**:
- ClinGen Kidney Clinical Domain Working Groups (KGDB integrates ClinGen data)
- Genomics England PanelApp (KGDB integrates PanelApp data)
- GenCC (KGDB integrates GenCC data)
- HPO (KGDB uses HPO terms)

## 2. Current State Audit

### 2.0 Lighthouse Audit Results (Dev Server, 2026-03-15)

> **Note**: Performance scores are from the Vite dev server (unbundled ESM, no minification, no compression). Production scores will be significantly higher. Accessibility, Best Practices, and SEO scores are representative of production.

| Page | Performance | Accessibility | Best Practices | SEO |
|------|-------------|--------------|----------------|-----|
| Home (`/`) | 55 | 90 | 100 | 100 |
| Gene Browser (`/genes`) | 53 | 92 | 100 | 100 |
| Gene Detail (`/genes/PKD1`) | 54 | 83 | 100 | 100 |
| Gene Structure (`/genes/PKD1/structure`) | 55 | 88 | 100 | 100 |
| Dashboard (`/dashboard`) | 54 | 87 | 100 | 100 |
| Network Analysis (`/network-analysis`) | 54 | 82 | 100 | 100 |
| Data Sources (`/data-sources`) | 54 | 86 | 100 | 100 |
| About (`/about`) | 54 | 84 | 100 | 100 |

**Best Practices: 100 across all pages** — no console errors, HTTPS, no deprecated APIs.
**SEO: 100 across all pages** — but this only checks basic meta tag presence, NOT crawlability or structured data quality.

#### Key Performance Metrics (Dev Mode — will improve in production)

| Metric | Home | Genes | Gene Detail | Dashboard |
|--------|------|-------|-------------|-----------|
| FCP | 17.6s | 17.7s | 18.0s | 17.8s |
| LCP | 34.2s | 39.8s | 41.5s | 38.9s |
| TBT | 90ms | 170ms | 110ms | 100ms |
| CLS | 0 | 0.008 | 0.006 | 0.049 |

- **TBT is excellent** (< 200ms) across all pages — no main-thread blocking issues
- **CLS is excellent** (< 0.1) across all pages — no layout shift problems
- FCP/LCP are dev-mode artifacts (unbundled ESM modules, ~5.6-6.3 MB total transfer)

#### Dev Mode Bundle Breakdown (largest modules)

| Module | Size | Note |
|--------|------|------|
| `reka-ui.js` | 1,468 KB | UI primitives for shadcn-vue — tree-shakes in production |
| `lucide-vue-next.js` | 906 KB | Icon library — should tree-shake to only used icons |
| `@radix-icons/vue.js` | 437 KB | Additional icon library — may be redundant with Lucide |
| `chunk-NEQT7IUZ.js` | 380 KB | Vendor chunk |
| `chunk-HSMVNQEZ.js` | 296 KB | Vendor chunk |
| `vue-router.js` | 201 KB | Router |

#### Accessibility Failures (consistent across pages)

| Issue | Pages Affected | Elements | Severity |
|-------|---------------|----------|----------|
| **Buttons without accessible name** | ALL 8 pages | Footer icon buttons (tooltip triggers) | High |
| **Links without discernible name** | ALL 8 pages | Footer icon links (GitHub, docs, license, issues) | High |
| **Insufficient color contrast** | 6/8 pages | `muted-foreground` text, colored badges on gene detail | High |
| **Heading order not sequential** | Dashboard, Data Sources | Skips heading levels | Medium |
| **Touch targets too small** | Gene Detail | Back-to-browser arrow link | Medium |
| **Form elements without labels** | Network Analysis | Input fields (Min Score, Max Genes, STRING) | High |
| **Links rely on color** | About | Inline links not distinguishable without color | Medium |

#### 404 Behavior

Navigating to `/nonexistent-page` shows an **empty page** with:
- Generic title "KGDB - Kidney Genetics Database" (no "404" or "Not Found")
- Empty `<main>` element — no content, no helpful navigation
- Vue Router console warning: "No match found for location"
- No `noindex` directive — Google would index this empty page

### 2.0.1 Visual Observations from Page Screenshots

**Home page**:
- Hero shows "Kidney-Genetics database" as a logo/image — NOT an `<h1>` heading (confirmed in accessibility tree: no heading element in hero)
- Dynamic gene count "3,245 Genes with Evidence" is rendered — but meta descriptions still say "571+"
- Large empty space below the "Why Use This Database?" section — wasted content area that could hold keyword-rich text
- Footer shows v0.1.0 (version badge)

**Gene Browser**:
- Good: Has `<h1>` "Gene Browser" with descriptive subtitle
- Shows 10/3,245 genes with pagination (Page 1 of 325)
- Filter controls have no visible labels (just icons/placeholders)

**Gene Detail (PKD1)**:
- Rich data: Evidence Score 95.2/Definitive, 7 data source cards, constraint scores, phenotypes, expression, interactions
- "PKD1" heading exists but no full gene name visible in the heading area (just "Gene information" subtitle)
- "Top: PKD2, PKHD1, NPHP1" — internal links to related genes exist in the interactions section (good for SEO)
- Many colored badges with potential contrast issues

**Gene Structure (PKD1)**:
- D3 visualization renders well with ClinVar variant lollipops
- Tabs: Gene Structure / Protein Domains
- No `useSeoMeta` or `useJsonLd` — confirmed zero SEO management

**Dashboard**:
- UpSet plot renders with full source overlap data
- 3,245/5,183 genes stat visible — shows different total from gene browser

**Network Analysis**:
- Empty state: "No network loaded" — thin content for crawlers
- Form inputs lack associated labels (Lighthouse confirmed)

**Data Sources**:
- 7 source cards with stats — good content depth
- Database Summary section at bottom with aggregate stats

**About**:
- Rich content: How to Use, Core Concepts, Open Source sections
- Multiple heading levels — good structure
- Inline links may have color-only differentiation issue

### 2.1 Performance Assessment

**Font Loading**: No web fonts loaded — relies on system fonts via Tailwind defaults. This is good for performance (zero font-related render blocking).

**Resource Hints**: Zero `<link rel="preconnect">`, `<link rel="dns-prefetch">`, or `<link rel="preload">` tags in `index.html`. Not critical since backend is proxied same-origin, but preloading the entry JS chunk would help.

**Bundle Size / Code Splitting** (`vite.config.ts`):
- Manual chunks for `vendor-vue`, `vendor-tanstack`, `vendor-d3`, `vendor-cytoscape` — good separation
- **Issue**: D3 imported as `import * as d3 from 'd3'` in 5 files (D3BarChart, D3DonutChart, GeneStructureVisualization, ProteinDomainVisualization, useD3Tooltip) — pulls the entire D3 library (~300KB minified). Should use named submodule imports (`import { select, scaleLinear } from 'd3-selection'`)
- Heavy components (Cytoscape network graph, UpSet.js, D3 charts) are properly lazy-loaded via `defineAsyncComponent` in Dashboard.vue and GeneDetail.vue

**Compression**: nginx enables gzip (level 6) but **no Brotli compression** (15-20% better than gzip). No pre-compressed build assets via Vite plugin.

**Static Asset Caching** (nginx.prod.conf):
- **Issue**: All files cached for only 1 hour, including hashed Vite build assets that are safe for immutable 1-year caching. Missing:
  ```nginx
  location /assets/ {
      expires 1y;
      add_header Cache-Control "public, immutable";
  }
  ```

**Critical CSS**: No critical CSS inlining (no `critters` plugin). Entire CSS bundle must download before first paint.

**Image Optimization**: Only PNG icons (favicon, PWA). Logo components (`KGDBLogo.vue`) lack explicit `width`/`height` attributes — CSS-only sizing risks CLS.

**Estimated Lighthouse Score**: Cannot determine without running, but expect ~60-70 Performance (large JS bundles, no prerendering), ~80-85 Accessibility (missing ARIA), ~90 Best Practices, ~70-80 SEO (no crawlable content).

### 2.2 Structured Data Assessment

**Organization** (`useJsonLd.ts:42-46`):
```javascript
{ '@type': 'Organization', name, url, logo: `${SITE_URL}/icon-512.png` }
```
**Missing**: `logo` as `ImageObject` with dimensions, `sameAs` (GitHub, social), `description`, `contactPoint`

**WebSite with SearchAction** (`useJsonLd.ts:48-63`): Present and correct. `urlTemplate` points to `/genes?search={search_term_string}`.

**Dataset** (`useJsonLd.ts:68-89`):
```javascript
{ '@type': 'Dataset', name, description, url, license, creator, keywords, variableMeasured, dateModified }
```
**Missing**: `variableMeasured` is a plain string (should be `PropertyValue`), `distribution` (API endpoint/download), `identifier` (DOI), `isAccessibleForFree: true`, `version`

**Gene** (`useJsonLd.ts:92-112`) — **CRITICAL gaps**:
```javascript
{ '@type': 'Gene', name, identifier, url, alternateName, sameAs: [genenames.org only], isPartOf }
```
**Missing vs BioSchemas Gene 1.0-RELEASE**:
- `description` (gene full name / function)
- `taxonomicRange` (`{ '@type': 'Taxon', name: 'Homo sapiens' }`)
- `associatedDisease` — **this is KGDB's core data and it's not in the schema**
- `sameAs` should include Ensembl, NCBI Gene, UniProt (currently only genenames.org)
- `encodesBioChemEntity` (protein link)
- `isPartOfBioChemEntity` (chromosome)
- `subjectOf` (publications/evidence)
- `dct:conformsTo` BioSchemas profile URI

**BreadcrumbList** (`useJsonLd.ts:115-128`): Present and correct on all public pages.

**Missing schema types that would add value**:
- `MedicalWebPage` — for gene detail pages
- `CollectionPage` — for Gene Browser (`/genes`)
- `ItemList` — on Gene Browser listing top genes (can generate rich results)
- `DataCatalog` — for Data Sources page
- `FAQPage` — if About page is restructured

### 2.3 Technical SEO Assessment

**SPA Crawlability** — **CRITICAL**:
- Pure client-side SPA with no SSR, no prerendering
- `index.html` contains only `<div id="app"></div>` with static meta tags
- Per-page `useHead()` calls only execute client-side
- Social media crawlers (Facebook, Twitter/X, LinkedIn) see only static `index.html` meta tags
- AI crawlers (GPTBot, ClaudeBot, PerplexityBot) do not execute JavaScript at all
- Google renders JS but with a delayed second-pass queue

**Sitemap** (`backend/app/api/endpoints/seo.py`):
- Contains static pages and all gene detail pages with `priority` and `changefreq`
- Properly proxied via nginx at `/sitemap.xml`
- **Missing**: `<lastmod>` timestamps on all URLs (important for crawl efficiency)
- **Missing**: Sitemap index (5,000+ URLs should be split into chunks)
- **Missing**: Gene structure pages (`/genes/{symbol}/structure`)
- **Missing**: `Cache-Control` response header

**Canonical URLs**: `useSeoMeta` supports `canonicalPath` and is used on all major public pages.
- **Issue**: `GeneStructure` view (`/genes/{symbol}/structure`) has NO `useSeoMeta` or `useJsonLd` call — zero SEO management
- **Issue**: Reactivity bug in `useSeoMeta.ts` line 52 — `og:url` conditional spread evaluates `.value` at setup time, not reactively
- **Issue**: No trailing slash normalization (both `/genes` and `/genes/` resolve)

**404 Handling**: No catch-all route (`/:pathMatch(.*)*`) in router. Unknown URLs fall through to `index.html` with no 404 content and no `noindex` directive.

**Security Headers** (nginx.prod.conf): Well-configured — HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy all present. CSP has `unsafe-inline` for scripts/styles (comment references removed Vuetify — may no longer be needed).

**Internal Linking**: Gene detail pages do not link to related genes (same disease pathway, PPI interactions). This limits PageRank distribution and crawl discovery.

### 2.4 Accessibility Assessment

**ARIA Labels**: Only 3 `aria-label` attributes found across all views (all in GeneDetail.vue). No other views have ARIA attributes.

**`aria-live` Regions**: Zero `aria-live` attributes anywhere. Dynamic content (loading states, search results, pipeline status) not announced to screen readers.

**Color Contrast**: `muted-foreground` color (`oklch(0.552 0.016 285.938)` ≈ `#7c7c89`) may be borderline for WCAG AA (4.5:1) against white background. Needs verification with rendering.

**Keyboard Navigation**: shadcn-vue components (built on Radix Vue) handle keyboard navigation for interactive primitives. Custom interactive elements (charts, network graph) likely lack keyboard support.

### 2.5 Content & On-Page SEO Assessment

**Title Tags**:

| Page | Current Title | Issue |
|------|--------------|-------|
| Home | `Home \| KGDB` | **Should be keyword-rich**: "Kidney Genetics Database — Renal & Nephrology Gene Evidence Scores" |
| Genes | `Gene Browser \| KGDB` | Acceptable but could include "Kidney Disease" |
| GeneDetail | `{SYMBOL} - Gene Detail \| KGDB` | Should include full gene name: "PKD1 (Polycystin 1) — Kidney Gene Evidence \| KGDB" |
| Dashboard | `Dashboard \| KGDB` | Acceptable |
| About | `About \| KGDB` | Could be "About the Kidney Genetics Database \| KGDB" |
| DataSources | `Data Sources \| KGDB` | Acceptable |
| NetworkAnalysis | `Network Analysis \| KGDB` | Acceptable |
| GeneStructure | **NO title set** | Missing `useSeoMeta` entirely |

**Meta Descriptions**:
- **Stale data**: Home page, `index.html`, and router meta all reference "571+ genes" — the database now has 5,080+ genes
- GeneDetail has generic fallback description (not gene-specific)
- GeneStructure has no description

**H1 Tags**:
- **Home page has NO `<h1>` tag** — hero section uses `KGDBLogo` component and `<p>` tags only. This is the most important page for SEO.
- All other public pages have exactly one `<h1>` — good.

**Open Graph Image**:
- All pages use `/icon-512.png` (a small square icon)
- **No dedicated OG image (1200×630px)** — social sharing previews look unprofessional
- `og:type` is always `website` for every page (hardcoded in `useSeoMeta.ts`)

## 3. Best Practices & Industry Standards

### 3.1 SPA SEO — Current Google Guidance

Google uses a **two-phase rendering process**: first fetches HTML and extracts links, then queues the page for full JavaScript rendering in headless Chromium. Rendering typically completes within minutes but can be delayed.

**Google deprecated "dynamic rendering"** (serving pre-rendered HTML to bots while serving JS to users) in 2024 — it's prone to cloaking penalties and adds maintenance complexity.

**Critical reality**: Google is the ONLY search engine that renders JavaScript well:

| Crawler | Executes JS? | Notes |
|---------|-------------|-------|
| Googlebot | Yes (Chromium) | Delayed second-pass rendering |
| Bingbot | Limited | Struggles with complex SPAs |
| DuckDuckGo | No | Uses Bing's index |
| GPTBot (OpenAI) | No | Zero JS execution |
| ClaudeBot (Anthropic) | No | No JS execution |
| PerplexityBot | No | No JS execution |
| Twitterbot | No | Raw HTML only |
| facebookexternalhit | No | No JS execution |
| LinkedInBot | No | No JS execution |
| Google Scholar | Unknown/Unlikely | Requires `citation_*` meta tags in initial HTML |

**Recommendation**: Build-time prerendering is the correct approach. It produces real HTML that all crawlers can read, without runtime complexity.

### 3.2 Scientific Database SEO Patterns

- **UniProt**: Uses RDF/linked data for semantic representation; cross-references 100+ databases via `sameAs`-style links
- **Ensembl/NCBI**: NCBI uses Highwire Press meta tags (`citation_title`, `citation_author`) for Google Scholar indexing
- **Bgee**: Deployed BioSchemas Gene profile on 750,000+ pages — the largest known BioSchemas deployment

**Google Scholar requirements** (relevant for KGDB):
- Highwire Press meta tags (`citation_title`, `citation_database_title`, etc.) in initial HTML
- Permanent URLs per resource
- Content accessible without paywalls
- Indexing takes 6-9 months after implementation

**Google Dataset Search**:
- Requires `Dataset` JSON-LD with mandatory: `name`, `description`, `creator`, `distribution`
- `DataCatalog` links the overall collection
- Submit via sitemap + Google Search Console

### 3.3 BioSchemas Compliance

**Gene Profile 1.0-RELEASE** — property mapping for KGDB:

| Marginality | Property | KGDB Data Source |
|------------|----------|-----------------|
| **Minimum** | `identifier` | HGNC ID (available) |
| **Minimum** | `name` | `approved_symbol` (available) |
| **Recommended** | `description` | Gene full name / function (available via HGNC/UniProt) |
| **Recommended** | `encodesBioChemEntity` | UniProt protein ID (available) |
| **Recommended** | `isPartOfBioChemEntity` | Chromosome (available via Ensembl) |
| **Recommended** | `url` | Gene detail URL (available) |
| **Optional** | `alternateName` | Previous symbols, aliases (available) |
| **Optional** | `associatedDisease` | ClinGen/GenCC disease associations (available) |
| **Optional** | `expressedIn` | GTEx kidney tissue expression (available) |
| **Optional** | `sameAs` | NCBI Gene, Ensembl, UniProt, OMIM links (available) |
| **Optional** | `taxonomicRange` | Homo sapiens (constant) |

KGDB has data for ALL minimum, recommended, and most optional properties. Implementation is primarily a frontend schema generation task.

**Validation**: Google's Rich Results Test does NOT understand BioSchemas types (will show warnings). Use the Heriot-Watt BioSchemas scraper or Schema.org Markup Validator separately.

### 3.4 Lighthouse Perfect Score Strategies

**Scoring reality**: 100 is extremely hard; 90-100 is "excellent." Google does NOT use Lighthouse scores as a direct ranking factor — but Core Web Vitals (LCP < 2.5s, INP < 200ms, CLS < 0.1) ARE ranking signals.

**SPA-specific blockers**:
- Large initial JS bundle (mitigate with code splitting — already partially done)
- No server-rendered content for LCP measurement (mitigate with prerendering)
- Client-side routing can confuse canonical URL detection

**Data-heavy site strategies**:
- Use TanStack Virtual for row virtualization on gene tables
- Skeleton placeholders with fixed dimensions to prevent CLS
- Lazy-load D3/Cytoscape via `defineAsyncComponent` (already done)
- Debounce search/filter inputs for INP
- Web Workers for heavy client-side computation (sorting 5,000+ genes)

## 4. Implementation Plan

### Priority Matrix

| Task | Impact | Effort | Priority |
|------|--------|--------|----------|
| Build-time prerendering (hybrid) | **Critical** | High (3-4d) | 1 |
| Google Search Console setup | **Critical** | Low (1h) | 2 |
| Sitemap `lastmod` + sitemap index | High | Low (2h) | 3 |
| Home page `<h1>` + keyword-rich title | High | Low (1h) | 4 |
| Fix stale "571+ genes" references | High | Low (30m) | 5 |
| GeneStructure view SEO (missing entirely) | High | Low (1h) | 6 |
| Gene JSON-LD BioSchemas enrichment | High | Medium (1d) | 7 |
| Dataset JSON-LD enhancement | High | Low (2h) | 8 |
| Organization JSON-LD enhancement | Medium | Low (1h) | 9 |
| Dedicated OG image (1200×630) | Medium | Low (1h) | 10 |
| nginx immutable caching for `/assets/` | Medium | Low (30m) | 11 |
| 404 catch-all route | Medium | Low (1h) | 12 |
| D3 tree-shaking (submodule imports) | Medium | Medium (2h) | 13 |
| Brotli compression | Medium | Low (1h) | 14 |
| `useSeoMeta.ts` reactivity bug fix | Medium | Low (30m) | 15 |
| Gene title enrichment (include full name) | Medium | Low (1h) | 16 |
| Internal linking (related genes) | Medium | Medium (1d) | 17 |
| Highwire Press meta tags for Scholar | Medium | Low (2h) | 18 |
| `aria-live` regions | Medium | Medium (3h) | 19 |
| ARIA labels on interactive elements | Medium | Medium (3h) | 20 |
| `llms.txt` for AI discoverability | Low | Low (30m) | 21 |
| Database registry submissions | Low | Low (2h) | 22 |

### Phase 1: Quick Wins (1-2 days)

High impact, low effort items that can be done immediately without architectural changes.

- [ ] **1.1 Add `<h1>` to Home page with primary keywords** — `frontend/src/views/Home.vue`
  - Add: `<h1 class="sr-only">Kidney Genetics Database — Renal & Nephrology Gene Evidence Curation</h1>` (visually hidden if logo is the primary visual element, or replace the hero text)
  - This is the #1 on-page SEO signal

- [ ] **1.2 Fix Home page title tag** — `frontend/src/views/Home.vue` (useSeoMeta call)
  - Change from: `Home | KGDB`
  - Change to: `Kidney Genetics Database — Renal Gene Evidence Scores & Nephrology Gene Panel | KGDB`
  - Target keywords: kidney genetics database, renal gene, nephrology gene panel, evidence scores

- [ ] **1.3 Fix stale "571+ genes" → "5,000+ genes"** — Three locations:
  - `frontend/index.html` line 29
  - `frontend/src/router/index.ts` line 29
  - `frontend/src/views/Home.vue` (useSeoMeta description)
  - Consider making gene count dynamic from API rather than hardcoded

- [ ] **1.4 Add `useSeoMeta` + `useJsonLd` to GeneStructure view** — `frontend/src/views/GeneStructure.vue`
  - Add title: `{SYMBOL} Gene Structure | KGDB`
  - Add description: `Protein domain and gene structure visualization for {SYMBOL}`
  - Add canonical: `/genes/{symbol}/structure`
  - Add breadcrumb JSON-LD

- [ ] **1.5 Add 404 catch-all route** — `frontend/src/router/index.ts`
  - Add: `{ path: '/:pathMatch(.*)*', name: 'NotFound', component: NotFound, meta: { noindex: true, title: 'Page Not Found' } }`
  - Create minimal `NotFound.vue` view with helpful navigation

- [ ] **1.6 Enhance gene detail title tags** — `frontend/src/views/GeneDetail.vue`
  - Change from: `{SYMBOL} - Gene Detail | KGDB`
  - Change to: `{SYMBOL} ({full_name}) — Kidney Disease Gene Evidence | KGDB`
  - Include full gene name for long-tail keyword matching

- [ ] **1.7 Fix `useSeoMeta.ts` reactivity bug** — `frontend/src/composables/useSeoMeta.ts` lines 52, 61
  - The `og:url` and `canonical` link spread operators evaluate `.value` at setup time rather than reactively inside the computed
  - Move the conditional inside the reactive computation

- [ ] **1.8 Create dedicated OG image (1200×630px)** — `frontend/public/og-image.png`
  - Design a proper social sharing image with KGDB branding, tagline, and kidney/gene visual
  - Update `useSeoMeta.ts` default `ogImage` from `/icon-512.png` to `/og-image.png`
  - Update `index.html` static OG image reference

- [ ] **1.9 Set immutable caching for hashed Vite assets** — `frontend/nginx.prod.conf`
  - Add before the general `location /` block:
    ```nginx
    location /assets/ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    ```

- [ ] **1.10 Add `llms.txt`** — `frontend/public/llms.txt`
  - Create a Markdown file describing KGDB for AI crawlers (project name, summary, key URLs)
  - Add reference in `robots.txt`

### Phase 2: Structured Data Enhancement (2-3 days)

JSON-LD enrichment and BioSchemas compliance.

- [ ] **2.1 Enrich Gene JSON-LD to full BioSchemas Gene 1.0-RELEASE** — `frontend/src/composables/useJsonLd.ts` (`getGeneSchema`)
  - Add `dct:conformsTo`: `https://bioschemas.org/profiles/Gene/1.0-RELEASE`
  - Add `description`: gene full name / function summary from gene data
  - Add `taxonomicRange`: `{ '@type': 'Taxon', name: 'Homo sapiens', '@id': 'https://www.ncbi.nlm.nih.gov/Taxonomy/Browser/wwwtax.cgi?id=9606' }`
  - Add `associatedDisease`: array of `MedicalCondition` from ClinGen/GenCC disease associations
  - Expand `sameAs` to array: HGNC, Ensembl, NCBI Gene, UniProt links (data already available in gene annotations)
  - Add `encodesBioChemEntity`: UniProt protein reference
  - Add `isPartOfBioChemEntity`: chromosome from Ensembl data
  - Add `expressedIn`: kidney tissue expression from GTEx data (if available)

- [ ] **2.2 Enrich Dataset JSON-LD** — `frontend/src/composables/useJsonLd.ts` (`getDatasetSchema`)
  - Change `variableMeasured` from string to `PropertyValue` object
  - Add `distribution`: `{ '@type': 'DataDownload', encodingFormat: 'application/json', contentUrl: 'https://kidney-genetics.org/api/genes' }`
  - Add `isAccessibleForFree: true`
  - Add `version` (from app version)
  - Add `measurementTechnique`: "computational curation from multiple genomic databases"

- [ ] **2.3 Enrich Organization JSON-LD** — `frontend/src/composables/useJsonLd.ts` (`getOrganizationSchema`)
  - Change `logo` to `ImageObject` with `width`/`height`
  - Add `sameAs`: GitHub repo URL, institutional website
  - Add `description`: "Research group developing the Kidney Genetics Database..."

- [ ] **2.4 Add CollectionPage + ItemList to Gene Browser** — `frontend/src/views/Genes.vue`
  - Add `CollectionPage` schema wrapping the gene list
  - Add `ItemList` with top genes as `ListItem` entries (can generate rich search results)

- [ ] **2.5 Add DataCatalog to Data Sources page** — `frontend/src/views/DataSources.vue`
  - Add `DataCatalog` JSON-LD listing all annotation sources

- [ ] **2.6 Add Highwire Press meta tags for Google Scholar** — `frontend/src/composables/useSeoMeta.ts` or per-view
  - Gene detail pages: `citation_title`, `citation_database_title`, `citation_public_url`
  - These must be in initial HTML (requires Phase 4 prerendering to be effective)

### Phase 3: Performance Optimization (2-3 days)

Bundle optimization, compression, and resource hints.

- [ ] **3.1 Tree-shake D3 imports** — 5 files:
  - `frontend/src/components/visualizations/D3BarChart.vue`
  - `frontend/src/components/visualizations/D3DonutChart.vue`
  - `frontend/src/components/gene/GeneStructureVisualization.vue`
  - `frontend/src/components/gene/ProteinDomainVisualization.vue`
  - `frontend/src/composables/useD3Tooltip.ts`
  - Change `import * as d3 from 'd3'` to named submodule imports (e.g., `import { select, scaleLinear, arc } from 'd3'` or from specific packages like `d3-selection`)
  - Expected savings: ~150-200KB from the vendor-d3 chunk

- [ ] **3.2 Add Brotli compression** — Two options:
  - Option A: Add `vite-plugin-compression` to generate `.br` files at build time, configure nginx to serve them
  - Option B: Add `brotli` module to nginx (requires nginx rebuild or `ngx_brotli` module)
  - Expected: 15-20% better compression than gzip

- [ ] **3.3 Add explicit dimensions to images** — `frontend/src/components/KGDBLogo.vue`
  - Add `width` and `height` attributes to `<img>` tags to prevent CLS
  - Use the intrinsic image dimensions, let CSS override for display size

- [ ] **3.4 Add resource hint for entry chunk** — `frontend/index.html`
  - Add `<link rel="modulepreload" href="/src/main.ts">` (Vite transforms this at build time)
  - Consider `<link rel="preconnect" href="https://kidney-genetics.org">` for same-origin API calls (useful if API is on a different subdomain in production)

- [ ] **3.5 Add `critters` for critical CSS inlining** — `frontend/vite.config.ts`
  - Install `critters` package
  - vite-ssg (Phase 4) integrates `critters` automatically when installed
  - Inlines above-the-fold CSS into `<style>` tags in the HTML `<head>`

- [ ] **3.6 Add sitemap Cache-Control header** — `backend/app/api/endpoints/seo.py`
  - Add `Cache-Control: public, max-age=3600` response header to sitemap endpoint

### Phase 4: Build-Time Prerendering (3-4 days)

**Recommended approach: Hybrid vite-ssg + meta-only gene pages**

This is the highest-impact change. Two sub-phases:

#### Phase 4A: vite-ssg for static pages

- [ ] **4A.1 Install vite-ssg** — `frontend/package.json`
  - `npm install vite-ssg`
  - Optionally install `critters` for critical CSS inlining during SSG

- [ ] **4A.2 Refactor main.ts to ViteSSG factory** — `frontend/src/main.ts`
  - Change from `createApp()` + `app.mount()` to `ViteSSG()` export pattern
  - Guard all browser-only code (`window.logService`, `navigator.userAgent`, etc.) with `isClient` checks
  - Example structure:
    ```typescript
    import { ViteSSG } from 'vite-ssg'
    import App from './App.vue'
    import { routes } from './router'

    export const createApp = ViteSSG(App, { routes }, ({ app, isClient }) => {
      // Register plugins
      if (isClient) {
        // Browser-only: logService, snackbar, WebSocket, etc.
      }
    })
    ```

- [ ] **4A.3 Add ssgOptions to vite.config.ts** — `frontend/vite.config.ts`
  - Configure `includedRoutes` to prerender only static public pages:
    ```typescript
    ssgOptions: {
      script: 'async',
      formatting: 'minify',
      includedRoutes(paths) {
        return ['/', '/genes', '/dashboard', '/data-sources', '/network-analysis', '/about']
      }
    }
    ```

- [ ] **4A.4 Ensure SSR-safety in static page components** — Views: Home, Genes, Dashboard, DataSources, NetworkAnalysis, About
  - Wrap any `window`/`document`/`navigator` access in `onMounted()` or `import.meta.env.SSR` guards
  - Lazy-loaded components (charts, network graph) should work automatically since they won't render during SSG

- [ ] **4A.5 Update build script** — `frontend/package.json`
  - Change `"build"` script from `vite build` to `vite-ssg build` (or however vite-ssg hooks in)

#### Phase 4B: Meta-only HTML shells for 5,000+ gene pages

- [ ] **4B.1 Create build script for gene page HTML shells** — `frontend/scripts/generate-gene-pages.ts`
  - Reads the built `dist/index.html` as template
  - Fetches all gene symbols + metadata from the API at build time
  - For each gene, generates `dist/genes/{SYMBOL}/index.html` with:
    - Correct `<title>`: `{SYMBOL} ({full_name}) — Kidney Disease Gene Evidence | KGDB`
    - Correct `<meta name="description">`: Gene-specific description with evidence score
    - Correct `<meta property="og:*">` tags
    - `<script type="application/ld+json">` with BioSchemas Gene schema
    - Same SPA `<script>` and `<link>` tags as the template (Vue app still mounts normally)
  - **Build time: ~5-15 seconds** for 5,000 files (just string replacement + file writes)

- [ ] **4B.2 Update nginx try_files** — `frontend/nginx.prod.conf`
  - Change: `try_files $uri $uri/ /index.html;`
  - To: `try_files $uri $uri/index.html /index.html;`
  - This serves prerendered `dist/genes/PKD1/index.html` for `/genes/PKD1` before falling back to the SPA shell

- [ ] **4B.3 Add build step to CI/CD** — `Makefile` or CI workflow
  - After `vite build` (or `vite-ssg build`), run the gene page generation script
  - Ensure the API is accessible during build (either from the hybrid setup or a build-time API endpoint)

- [ ] **4B.4 Add sitemap `lastmod` timestamps** — `backend/app/api/endpoints/seo.py`
  - Query `updated_at` from gene records
  - Add `<lastmod>` tag to each `<url>` entry

- [ ] **4B.5 Implement sitemap index** — `backend/app/api/endpoints/seo.py`
  - Split 5,000+ URLs into multiple sitemap files (max 10,000 each)
  - Serve a `<sitemapindex>` at `/sitemap.xml` pointing to `/sitemap-static.xml`, `/sitemap-genes-1.xml`, etc.

- [ ] **4B.6 Add gene structure pages to sitemap** — `backend/app/api/endpoints/seo.py`
  - Include `/genes/{symbol}/structure` URLs for all genes

### Phase 5: Content & Accessibility (3-5 days)

Content enrichment, internal linking, and accessibility improvements.

- [ ] **5.1 Add internal linking — related genes** — `frontend/src/views/GeneDetail.vue`
  - Add a "Related Genes" section linking to genes in the same disease pathway or PPI network
  - Use existing network analysis data (STRING PPI interactions)
  - This distributes PageRank and improves crawl discovery

- [ ] **5.2 Keyword-optimized meta descriptions** — Multiple view files
  - Home: "Kidney Genetics Database (KGDB) — the definitive nephrology gene panel and renal genetics resource. Evidence-based curation of 5,000+ kidney disease genes from ClinGen, PanelApp, GenCC, and 6 more sources."
  - Genes: "Browse 5,000+ kidney and renal disease genes with evidence scores. Filter by gene symbol, disease association, or annotation source. Comprehensive nephropathy gene list."
  - GeneDetail: Dynamic — "{SYMBOL} ({full_name}): kidney disease evidence score {score}. Disease associations, expression data, and annotations from {N} genomic sources."
  - Include target keywords naturally: nephrology gene panel, renal genetics, kidney gene curation, nephropathy gene list, kidney genomics resource

- [ ] **5.3 Add `aria-live` regions** — Multiple components
  - Gene Browser search results: `aria-live="polite"` on results count
  - Loading/error state transitions: `aria-live="assertive"` on error containers
  - Toast notifications: verify Sonner handles this (likely does)
  - Pipeline progress: `aria-live="polite"` on progress indicators

- [ ] **5.4 Add ARIA labels to interactive elements** — Multiple components
  - Navigation menus: `aria-label="Main navigation"`, `role="navigation"`
  - Search inputs: `aria-label="Search genes"`
  - Filter controls: proper labels
  - Chart components: `aria-label` descriptions of what the chart shows
  - Network graph: `aria-label="Gene interaction network"`

- [ ] **5.5 Audit and fix color contrast** — `frontend/src/assets/main.css`
  - Test `muted-foreground` against white background for WCAG AA (4.5:1)
  - Darken if needed (change `oklch(0.552 ...)` to `oklch(0.45 ...)` or similar)

- [ ] **5.6 Update robots.txt with AI crawler controls** — `frontend/public/robots.txt`
  - Add rules for AI training crawlers (block training, allow search):
    ```
    User-agent: GPTBot
    Disallow: /admin
    Allow: /

    User-agent: ClaudeBot
    Disallow: /

    User-agent: Claude-SearchBot
    Allow: /
    ```
  - Add `Sitemap: https://kidney-genetics.org/sitemap.xml` (already present)

### Phase 6: Monitoring & CI (1 day)

- [ ] **6.1 Set up Google Search Console** — External
  - Verify domain ownership (DNS TXT record or HTML file)
  - Submit sitemap
  - Monitor indexing status
  - Request indexing of key pages
  - Check for crawl errors

- [ ] **6.2 Add Lighthouse CI to GitHub Actions** — `.github/workflows/lighthouse.yml`
  - Run Lighthouse on key pages after deployment
  - Set minimum thresholds: Performance 80, Accessibility 90, Best Practices 90, SEO 90
  - Fail CI if scores drop below thresholds

- [ ] **6.3 Add structured data validation test** — `frontend/tests/` or CI script
  - Validate JSON-LD output against BioSchemas Gene profile
  - Ensure all required properties are present
  - Use Schema.org Markup Validator API or custom test

- [ ] **6.4 Submit to Google Dataset Search** — External
  - Verify `Dataset` JSON-LD appears in initial HTML (requires Phase 4)
  - Validate with Google's Rich Results Test
  - Monitor Dataset Search appearance

- [ ] **6.5 Submit to database registries** — External
  - re3data.org, FAIRsharing.org, bio.tools, dkNET, BioSchemas.org live deploys

### Dependencies & Risks

**Critical path**: Phase 4 (prerendering) → Phase 6.1 (Search Console) → indexing
- Without prerendering, all other SEO improvements are invisible to crawlers
- Search Console submission should happen immediately after prerendering is deployed

**Phase dependencies**:
- Phase 1 has no dependencies — do first
- Phase 2 (structured data) can run parallel with Phase 3 (performance)
- Phase 4 (prerendering) depends on Phase 1 completing (to prerender correct content)
- Phase 5 can run parallel with Phase 4
- Phase 6 depends on Phase 4 deploying to production

**Risks**:
- **vite-ssg SSR-safety**: Components using `window`/`document` during setup will break SSG. Mitigation: audit all components, add `isClient` guards. The lazy-loaded components (charts, network graph) are naturally safe since they won't render during SSG.
- **API availability during build**: The gene page generation script needs the API running. Mitigation: use the hybrid setup (`make hybrid-up`) during CI/CD builds, or cache API responses.
- **Build-time API rate limiting**: vite-ssg may hit rate limits if making 5,000+ API calls. Mitigation: bulk-fetch all gene data once, inject per-route.
- **Hydration mismatches**: If the prerendered HTML doesn't match what Vue renders client-side, Vue will warn and re-render. Mitigation: ensure data used during SSG matches what the client fetches.
- **Meta-only gene pages vs full prerender**: Crawlers that don't execute JS will see meta tags and JSON-LD but not the full page content. This is sufficient for indexing (Google renders JS; other crawlers get enough structured data).

## 5. Recommended New Dependencies

| Package | Purpose | Size Impact | Alternative Considered |
|---------|---------|-------------|----------------------|
| `vite-ssg` | Static site generation for Vue 3 + Vite | Build-time only (~50KB) | Vike (heavier, more features than needed) |
| `critters` | Critical CSS inlining during SSG | Build-time only (~100KB) | Manual critical CSS extraction (fragile) |
| `vite-plugin-compression` | Pre-compress assets as `.br`/`.gz` | Build-time only (~20KB) | nginx-only compression (works but no pre-compression) |
| `@unhead/schema-org` | Typed Schema.org helpers | ~15KB | Raw JSON-LD objects (current approach, more verbose) |

All are build-time dependencies with zero runtime size impact.

## 6. Metrics & Success Criteria

### Target Scores (3 months post-implementation)

| Metric | Current (estimated) | Target | Tool |
|--------|-------------------|--------|------|
| Google indexed pages | 0 | 5,000+ | Google Search Console |
| Lighthouse Performance | ~60-70 | 85+ | Lighthouse CI |
| Lighthouse Accessibility | ~80-85 | 90+ | Lighthouse CI |
| Lighthouse Best Practices | ~90 | 95+ | Lighthouse CI |
| Lighthouse SEO | ~70-80 | 95+ | Lighthouse CI |
| LCP | Unknown | < 2.5s | CrUX / PageSpeed Insights |
| INP | Unknown | < 200ms | CrUX / PageSpeed Insights |
| CLS | Unknown | < 0.1 | CrUX / PageSpeed Insights |

### Ranking Goals (6-12 months post-implementation)

| Keyword | Target Position | Currently |
|---------|----------------|-----------|
| kidney disease gene database | Top 3 | Abstract at #9, website not indexed |
| kidney gene evidence scores | #1 | Abstract at #5, website not indexed |
| kidney gene curation | Top 5 | Abstract at #5, website not indexed |
| nephropathy gene list | Top 5 | Not ranked |
| renal genetics database | Top 5 | Not ranked |
| nephrology gene panel | Top 10 | Not ranked |
| kidney genomics resource | Top 5 | Not ranked |
| hereditary kidney disease genes | Top 10 | Not ranked |

### Other Success Criteria

- Google Dataset Search: KGDB appears for "kidney genetics dataset" queries
- Social sharing: Correct per-page OG previews on Twitter/X, LinkedIn, Facebook
- BioSchemas validation: All gene pages pass BioSchemas Gene 1.0-RELEASE validation
- Google Scholar: Gene pages indexed (6-9 month timeline after `citation_*` tags)
- Backlinks: Listed on 3+ database registries (re3data, FAIRsharing, bio.tools)
- AI discoverability: KGDB content surfaced by AI search engines (Perplexity, ChatGPT Search)
