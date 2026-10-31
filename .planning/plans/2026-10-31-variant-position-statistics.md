# Variant Position Statistics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Domain enrichment, linear hotspot scan, 3D clustering and 3D hotspots for ClinVar P/LP missense vs gnomAD missense, shown as clear charts on the Protein Domains and 3D tabs.

**Architecture:** The ClinVar pipeline stores an uncapped per-residue missense table. The browser fetches gnomAD missense (controls) and the UniProt sequence per gene, runs pure, seeded, R-validated statistics in a same-origin module Web Worker, and renders results with D3 and shadcn-vue in the existing design language.

**Tech Stack:** Python 3.13 / pytest (backend pipeline), Vue 3 + TypeScript + Vitest + D3 v7 (frontend), NGL (Cα coordinates), R 4.5 for reference values.

**Spec:** `.planning/specs/2026-10-31-variant-position-statistics-design.md` (read it first; this plan does not repeat its rationale).

## Global Constraints

- Worktree only: `/home/bernt-popp/development/kidney-genetics-db/.claude/worktrees/perf-gene-page-3d-structure`. **Do not commit**; the lead reviews each task's diff. Never use `git stash`.
- No new npm or Python dependencies.
- Cases = ClinVar `pathogenic` + `likely_pathogenic` missense with stars ≥ 1 (toggle to include 0). B/LB = `benign` + `likely_benign`, same star rule. Controls = gnomAD v4.1 missense, PASS, ac > 0.
- Missense HGVS = single substitution `^p\.\(?([A-Z][a-z]{2})(\d+)([A-Z][a-z]{2})\)?$`, ref ≠ alt, alt not `Ter`; reuse the regex already in `frontend/src/utils/alphafold.ts` (export it), do not write a second one.
- Reference-AA check against the UniProt canonical sequence for both sources; > 10% failures in either source ⇒ withhold statistics with the reason.
- Linear scan window `w = 15`, step 1, `B = 10 000`; 3D clustering `B = 10 000`; 3D hotspots radius `10 Å`, `B = 2 000`; pLDDT ≥ 70; seed `20261031`; min-p FWER `(k+1)/(B+1)`; ≥ 3 cases or "too few" message.
- Colour: only `significanceColor('pathogenic')` for significant/observed marks; neutral `var(--muted-foreground)` otherwise; text in text tokens; solid labelled hairlines; table twin per chart.
- Copy: never "PM1 met"; caveat text from the spec verbatim: "Statistical support for an ACMG/AMP PM1 assessment, not a classification. Population variants are not benign variants. Research use."
- Gates per AGENTS.md: backend `ruff check --no-fix app/`, `ruff format --check app/`, focused pytest; frontend `npm run lint:check`, `npm run format:check`, `npx vitest run <files>`, `npm run build`.

## Review Focus

1. gnomAD API down / HTTP 429 / timeout → the statistics sections show a retryable error; plots and variant lists keep working. (Task 4 test.)
2. Gene with 0–2 P/LP missense after filtering → "too few P/LP missense variants for a meaningful test", no p-values shown. (Task 5 test.)
3. Annotation without `missense_residues` (data older than this change) → "Statistics need a ClinVar data refresh", nothing computed from the capped list. (Task 4 test.)
4. Very long protein (PKD1, 4303 aa, no AlphaFold model) → linear statistics complete within budget, 3D section shows the no-model message. (Task 5 perf test, Task 8 test.)
5. Leaving the tab or page mid-computation → the worker is terminated and no state is written after unmount. (Task 6 test.)

---

### Task 1: ClinVar `missense_residues` (uncapped) in the pipeline

**Files:**
- Modify: `backend/app/pipeline/sources/annotations/clinvar_utils.py` (`GeneAccumulator`: slots, `__init__`, `add_variant`, `finalize`)
- Modify: `backend/app/pipeline/sources/annotations/clinvar.py` (`_aggregate_variants` delegates to `GeneAccumulator`; `_build_annotation` and `_empty_annotation` carry the field)
- Test: `backend/tests/pipeline/test_clinvar_utils.py`, `backend/tests/test_w2_clinvar_fallback.py` (existing, must stay green)

**Interfaces:**
- Produces: annotation field `missense_residues: list[{"residue": int, "ref": str, "counts": dict[category, dict[str(star), int]]}]`, sorted by residue then ref; only non-zero keys. Star = existing `confidence` (0–4).
- Produces (maintainer request 2026-10-31: "fix api ... improve and stabilize"): the capped detail lists `protein_variants` and `genomic_variants` keep their `max_detail` bound but are no longer "first N in file order". Each list keeps the N highest-priority variants, deterministically: priority key `(category_rank, -confidence, position, accession)` ascending, with `category_rank` = pathogenic 0, likely_pathogenic 1, conflicting 2, vus 3, likely_benign 4, benign 5, other 6; implemented with a bounded heap so memory stays O(N); `finalize()` returns them sorted by position (then accession) as today's consumers expect. New fields `protein_variants_total: int` and `genomic_variants_total: int` (counts before capping) so the UI can say "N of M".

- [ ] **Step 1: Write failing tests** in `test_clinvar_utils.py`:
  - `test_missense_residues_counts_all_variants_beyond_detail_cap`: `GeneAccumulator(levels, max_detail=2)`; add 5 missense variants (`p.Arg177Trp` P 2-star ×2, `p.Arg177Gln` LP 1-star, `p.Ser148Trp` VUS 0-star, `p.Gly20Arg` B 1-star) plus `p.Arg177Ter` (nonsense) and `p.Val5del`; `finalize()["missense_residues"] == [{"residue": 20, "ref": "Gly", "counts": {"benign": {"1": 1}}}, {"residue": 148, "ref": "Ser", "counts": {"vus": {"0": 1}}}, {"residue": 177, "ref": "Arg", "counts": {"pathogenic": {"2": 2}, "likely_pathogenic": {"1": 1}}}]` and `len(protein_variants) == 2`.
  - `test_missense_residues_requires_missense_consequence`: `p.Arg177Trp` whose `molecular_consequences` lacks "missense variant" is not counted.
  - `test_detail_cap_keeps_highest_priority_deterministically`: `max_detail=3`; add 6 variants in file order VUS(pos 10), B(pos 5), P 1-star(pos 300), LP 2-star(pos 50), P 2-star(pos 200), conflicting(pos 1) → kept protein accessions are exactly the P 2-star, P 1-star and LP ones, returned sorted by position (50, 200, 300); feeding the same 6 in reversed order gives the identical list; `protein_variants_total == 6`.
  - `test_aggregate_variants_matches_accumulator`: for the same variant list, `ClinVarAnnotationSource._aggregate_variants(list)` == `GeneAccumulator(...)` + `finalize()` (construct the source with a mocked session as the existing fallback test does).
- [ ] **Step 2: Run** `cd backend && uv run pytest tests/pipeline/test_clinvar_utils.py -q` → the new tests FAIL (KeyError / mismatch).
- [ ] **Step 3: Implement.** In `add_variant`, after `effect_category`: when any consequence lower-cases to "missense variant" and the protein change matches the missense regex (Python twin of the frontend regex, defined once in `clinvar_utils.py`), increment `self.missense_residues[(position, ref)][category][str(confidence)]`. `finalize()` emits the sorted list. Replace the body of `_aggregate_variants` with accumulator delegation using `_MAX_DETAIL_VARIANTS` and the source's confidence levels; add `"missense_residues": stats.get("missense_residues", [])` in `_build_annotation` and `[]` in `_empty_annotation`.
- [ ] **Step 4: Run** `uv run pytest tests/pipeline/test_clinvar_utils.py tests/test_w2_clinvar_fallback.py tests/ -q -k clinvar` (with `TEST_DATABASE_URL` set to the throwaway `kgdb_gates` DB, see `/tmp/.../scratchpad/gates.sh`) → PASS; `uv run ruff check --no-fix app/ && uv run ruff format --check app/` clean.
- [ ] **Step 5: Hand the diff to review** (no commit).

### Task 2: Statistics primitives, validated against R

**Files:**
- Create: `frontend/src/utils/stats/core.ts`
- Test: `frontend/src/utils/stats/__tests__/core.spec.ts`

**Interfaces:**
- Produces: `fisherExact(a, b, c, d): { p: number; or: number; lo: number; hi: number }` (2×2 `[[a,b],[c,d]]`, R `fisher.test` semantics incl. conditional MLE OR and exact 95% CI, `Infinity`/`0` bounds); `hyperUpper(k, K, N, n): number` = P(X ≥ k), X ~ Hypergeometric(population N, K successes, n draws); `bhAdjust(p: number[]): number[]` (R `p.adjust(,"BH")`, original order); `mulberry32(seed: number): () => number`; `shuffleInPlace<T>(a: T[], rand: () => number): T[]` (Fisher–Yates).

- [ ] **Step 1: Write failing tests** with these R 4.5 reference values (comment the R call above them): `fisher.test(matrix(c(...),2,byrow=TRUE))`:
  `[8,2,1,5] p 0.03496503497 or 15.46968746 ci 1.00884938–1049.791446`; `[3,1,1,3] p 0.4857142857 or 6.408308867 ci 0.2117329153–621.9337505`; `[0,10,5,5] p 0.03250773994 or 0 ci 0–0.8365428425`; `[10,0,2,8] p 0.0007144558228 or Inf ci 3.817010258–Inf`; `[27,84,58,794] p 1.064301661e-07 or 4.389990715 ci 2.530858761–7.486828435`; `[1,9,11,3] p 0.002759456185 or 0.03723311725 ci 0.0006438283884–0.4258840381`; `[12,5,30,40] p 0.0577727087 or 3.157421529 ci 0.9133653002–12.71750941`; `[0,0,3,4] p 1 or 0 ci 0–Inf`. Tolerance: relative 1e-6 on p and OR, 1e-4 on CI bounds.
  BH: input `[0.01,0.04,0.03,0.005,0.5,0.2,0.04]` → `[0.035,0.056,0.056,0.035,0.5,0.2333333333,0.056]`.
  `hyperUpper(5, 20, 100, 7)` = `0.003259144891` (R `phyper(4,20,80,7,lower.tail=FALSE)`).
  `mulberry32(20261031)` gives the same first 3 numbers twice; values in [0,1).
- [ ] **Step 2: Run** `cd frontend && npx vitest run src/utils/stats/__tests__/core.spec.ts` → FAIL (module missing).
- [ ] **Step 3: Implement** with log-space hypergeometric pmf via a `lgamma`/log-factorial table. Two-sided p: sum of pmf ≤ observed pmf × (1 + 1e-7). Conditional MLE: solve E[X; ψ] = observed on the noncentral hypergeometric by bisection on log ψ; CI: solve the two one-sided tail equations at α/2 = 0.025 by bisection on log ψ (R's method); support-boundary observed values give 0/∞ exactly as R.
- [ ] **Step 4: Run** the spec → PASS.
- [ ] **Step 5: Hand the diff to review.**

### Task 3: Variant set assembly (data → positions)

**Files:**
- Modify: `frontend/src/utils/alphafold.ts` (export `MISSENSE_HGVS` and the 3-letter→1-letter `AA` map; no behaviour change)
- Create: `frontend/src/utils/stats/variantSet.ts`
- Test: `frontend/src/utils/stats/__tests__/variantSet.spec.ts`

**Interfaces:**
- Consumes: `MISSENSE_HGVS`, `AA` from `alphafold.ts`.
- Produces:
  - `type ClinvarResidueRow = { residue: number; ref: string; counts: Record<string, Record<string, number>> }`
  - `type GnomadVariant = { variant_id: string; consequence: string; hgvsp: string | null; exome: { ac: number; filters: string[] } | null; genome: { ac: number; filters: string[] } | null }`
  - `type VariantSet = { length: number; cases: number[]; controls: number[]; benign: number[]; dropped: { clinvar: number; gnomad: number }; checked: { clinvar: number; gnomad: number }; withheld: string | null }` (arrays = residue per variant, one entry per variant)
  - `buildVariantSet(input: { sequence: string; clinvar: ClinvarResidueRow[] | undefined; gnomad: GnomadVariant[]; minStars: number }): VariantSet`

- [ ] **Step 1: Write failing tests:** counts expand to one residue entry per variant; `minStars: 1` drops the `"0"` bucket; gnomAD keeps only `missense_variant` with a PASS call (`filters` empty) and `ac > 0` in exome or genome; ref mismatch against `sequence` is dropped and counted per source; > 10% mismatches in either source sets `withheld` to a sentence naming the source and the percentage; `clinvar: undefined` sets `withheld` to "Statistics need a ClinVar data refresh."
- [ ] **Step 2: Run** `npx vitest run src/utils/stats/__tests__/variantSet.spec.ts` → FAIL.
- [ ] **Step 3: Implement** `buildVariantSet` (pure).
- [ ] **Step 4: Run** → PASS; `npx vitest run src/utils/__tests__/alphafold.spec.ts` still PASS.
- [ ] **Step 5: Hand the diff to review.**

### Task 4: Fetchers (UniProt sequence, gnomAD missense), session-cached

**Files:**
- Create: `frontend/src/api/variantStatsSources.ts`
- Test: `frontend/src/api/__tests__/variantStatsSources.spec.ts`

**Interfaces:**
- Produces: `fetchUniprotSequence(accession: string): Promise<string>` (parses FASTA from `https://rest.uniprot.org/uniprotkb/{acc}.fasta`); `fetchGnomadMissense(symbol: string): Promise<GnomadVariant[]>` (POST `https://gnomad.broadinstitute.org/api` with the spec's GraphQL query, `dataset: gnomad_r4`, filtered to `consequence === 'missense_variant'`). Both cached per session in a module `Map` of promises, evicting on rejection (same pattern as `fetchModel` in `alphafold.ts`). Errors throw `Error` with a user-facing message naming the source and HTTP status ("gnomAD responded 429").
  These are third-party public APIs called from the browser by design (spec), like `alphafold.ts`; they do not belong in the backend `apiClient`.

- [ ] **Step 1: Write failing tests** with `vi.stubGlobal('fetch', ...)`: FASTA header stripped and lines joined; second call hits cache (fetch called once); HTTP 429 rejects with message containing "gnomAD" and "429" and a retry fetches again; GraphQL `errors` array rejects; non-missense rows filtered.
- [ ] **Step 2: Run** `npx vitest run src/api/__tests__/variantStatsSources.spec.ts` → FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Hand the diff to review.**

### Task 5: Analyses (domain enrichment, linear scan, 3D clustering, 3D hotspots)

**Files:**
- Create: `frontend/src/utils/stats/analyses.ts`
- Test: `frontend/src/utils/stats/__tests__/analyses.spec.ts`

**Interfaces:**
- Consumes: Task 2 primitives, `VariantSet`, `ProteinRegion` from `alphafold.ts` (`proteinRegions`).
- Produces:
  - `domainEnrichment(set: VariantSet, regions: ProteinRegion[]): DomainResult[]` with `DomainResult = ProteinRegion & { caseIn: number; ctrlIn: number; caseOut: number; ctrlOut: number; p: number; or: number; lo: number; hi: number; q: number }`
  - `linearScan(set: VariantSet, opts?: { w?: number; B?: number; seed?: number }): ScanResult` with `ScanResult = { windows: { start: number; end: number; centre: number; cases: number; ctrls: number; p: number; adjP: number }[]; regions: { start: number; end: number; cases: number; ctrls: number; benign: number; adjP: number }[]; B: number; seed: number; w: number }`
  - `type Residue3D = { resno: number; x: number; y: number; z: number; plddt: number }`
  - `cluster3D(set: VariantSet, residues: Residue3D[], opts?: { B?: number; seed?: number }): ClusterResult | null` with `{ observed: number; nullMean: number; nullLo: number; nullHi: number; p: number; histogram: { x0: number; x1: number; n: number }[]; nCaseResidues: number; B: number; seed: number }` (null when < 3 eligible case residues)
  - `hotspots3D(set: VariantSet, residues: Residue3D[], opts?: { radius?: number; B?: number; seed?: number }): { clusters: { residues: number[]; cases: number; ctrls: number; adjP: number }[]; B: number; seed: number; radius: number }`
  - `TOO_FEW = 3` exported; analyses return an `{ tooFew: true }`-free API: callers check `set.cases.length < TOO_FEW` first.
- [ ] **Step 1: Write failing tests:**
  - `domainEnrichment` on a fixture equals `fisherExact` on hand-computed 2×2 per region and `q` equals `bhAdjust` of the region p-values.
  - Determinism: two `linearScan` runs with the same seed give identical `adjP`.
  - **Calibration**: 200 null datasets (300 residues; 20 cases and 200 controls at uniform random positions via `mulberry32(i)`), `B = 999`; count datasets with any region (adjP < 0.05); assert count within the binomial 99% interval for n=200, p=0.05: **[3, 19]**.
  - **Power**: planted hotspot (15 of 20 cases in residues 100–114, controls uniform) → a region overlapping 100–114 with adjP < 0.05.
  - **3D**: synthetic residues on a 60-residue line spaced 3.8 Å; cases planted at residues 10–14 → `cluster3D.p < 0.01`; 100 random-label datasets → mean p in [0.4, 0.6].
  - `hotspots3D` on the planted set returns a cluster containing residues 10–14 with adjP < 0.05.
  - **Perf** (Review Focus 4): 4303-residue protein, 60 cases, 3 000 controls, `linearScan` with `B = 10 000` completes in < 4 000 ms in Vitest (generous CI bound; measure and report actual).
  - Too few (Review Focus 2): `set.cases.length = 2` is handled by the caller contract; add a test that `cluster3D` returns `null` with < 3 eligible case residues.
- [ ] **Step 2: Run** `npx vitest run src/utils/stats/__tests__/analyses.spec.ts` → FAIL.
- [ ] **Step 3: Implement.** Linear scan: prefix sums of per-residue case/control counts; window p = `hyperUpper(casesInWin, totalCases, totalVariants, variantsInWin)`; per permutation shuffle labels over the fixed variant positions (`Int32Array` of positions, `Uint8Array` labels), recompute window case counts with prefix sums, record min window p; adjP(window) = (#perms with minP ≤ p_obs + 1)/(B + 1). Precompute a `hyperUpper` lookup per (variantsInWin, casesInWin) since totals are fixed. Regions = merged consecutive windows with adjP < 0.05, `adjP` = min over merged windows, `benign` counted from `set.benign` inside. 3D: eligible = plddt ≥ 70; distances from Cα; clustering statistic = mean pairwise distance among distinct case residues (variants mapped to residues; permute variant labels, then take distinct residues); one-sided p `(k+1)/(B+1)` where k counts permuted ≤ observed; histogram 30 bins over the null; nullLo/Hi = 2.5/97.5 percentiles. Hotspots: neighbour lists within radius (inclusive of self), per-residue hyper p, min-p permutation, clusters = connected components of significant residues under the radius.
- [ ] **Step 4: Run** → PASS; record the perf time in the task report.
- [ ] **Step 5: Hand the diff to review.**

### Task 6: Worker + composable

**Files:**
- Create: `frontend/src/workers/positionStats.worker.ts`
- Create: `frontend/src/composables/usePositionStats.ts`
- Test: `frontend/src/composables/__tests__/usePositionStats.spec.ts`

**Interfaces:**
- Consumes: Tasks 3–5.
- Produces:
  - Worker protocol: request `{ id: number; kind: 'linear'; set: VariantSet; regions: ProteinRegion[] } | { id: number; kind: '3d'; set: VariantSet; residues: Residue3D[] }`; response `{ id; ok: true; result } | { id; ok: false; error: string }`. Export the pure `handle(request)` from the worker file for tests; the `self.onmessage` wrapper only calls it.
  - `usePositionStats(input: { symbol: Ref<string>; accession: Ref<string | undefined>; clinvar: Ref<{ missense_residues?: ClinvarResidueRow[] } | null>; regions: Ref<ProteinRegion[]> })` → `{ status: Ref<'idle'|'loading'|'ready'|'error'|'withheld'|'too-few'>; message: Ref<string>; set: Ref<VariantSet|null>; linear: Ref<{ domains: DomainResult[]; scan: ScanResult } | null>; run3D(residues: Residue3D[]): Promise<void>; spatial: Ref<{ cluster: ClusterResult | null; hotspots: ReturnType<typeof hotspots3D> } | null>; minStars: Ref<number>; retry(): void }`. Worker created with `new Worker(new URL('../workers/positionStats.worker.ts', import.meta.url), { type: 'module' })` only in the browser; terminated in `onScopeDispose`. When `typeof Worker === 'undefined'` (Vitest/SSR) it calls `handle` directly.
- [ ] **Step 1: Write failing tests** (Worker undefined in jsdom, fetchers mocked): happy path reaches `ready` with domains; gnomAD rejection → `error` with the message and `retry()` refetches (Review Focus 1); missing `missense_residues` → `withheld` "Statistics need a ClinVar data refresh." (Review Focus 3); 2 cases → `too-few`; changing `minStars` recomputes; unmount (effectScope stop) during a pending fetch → no state change after stop (Review Focus 5).
- [ ] **Step 2: Run** `npx vitest run src/composables/__tests__/usePositionStats.spec.ts` → FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** → PASS. `npm run build` emits a separate `positionStats.worker-*.js` asset (check `dist/assets`).
- [ ] **Step 5: Hand the diff to review.**

### Task 7: Linear UI — forest table, scan track, Methods

**Files:**
- Create: `frontend/src/components/visualizations/stats/PositionStatistics.vue` (section: sentence, forest table, hotspot-region table, Methods disclosure, states)
- Create: `frontend/src/components/visualizations/stats/ForestCell.vue` (inline SVG: point, CI line, OR=1 hairline, arrows for 0/∞; shared domain via props `min`, `max`)
- Create: `frontend/src/components/visualizations/stats/StatsMethods.vue` (shared Methods disclosure used by Tasks 7 and 8; props: `kind: 'linear' | '3d'`, `B`, `seed`, `versions`, `minStars` v-model)
- Create: `frontend/src/utils/stats/sentences.ts` (+ spec) — `domainSentence(results: DomainResult[]): string`, `scanSentence(scan: ScanResult): string`, `clusterSentence(c: ClusterResult): string`, `formatP(p: number, B?: number): string` (permutation p printed as "< 1/(B+1)" floor when k = 0)
- Modify: `frontend/src/components/visualizations/ProteinDomainVisualization.vue` (new optional prop `scan: ScanResult | null`; draws the scan track under the domain track using the same zoomed x scale; region bands through lollipop + track; crosshair tooltip; height grows by the track's fixed height only when `scan` is non-null — reserve it while loading via a `scanPending: boolean` prop to avoid layout shift)
- Modify: `frontend/src/views/GeneStructure.vue` (protein tab: call `usePositionStats`, pass `scan`, render `PositionStatistics` under the plot)
- Test: `frontend/src/components/visualizations/stats/__tests__/PositionStatistics.spec.ts`, `frontend/src/utils/stats/__tests__/sentences.spec.ts`

**Interfaces:**
- Consumes: `usePositionStats` (Task 6), result types (Task 5).
- Produces: `PositionStatistics` props `{ state: ReturnType<typeof usePositionStats> }`; `StatsMethods` (used by Task 8).
- [ ] **Step 1: Write failing tests:** sentences: significant top domain → "Pathogenic missense variants are 4.4× more likely than population variants to fall in the POU-specific atypical domain (95% CI 2.5–7.5; q < 0.001)."; nothing significant → contains "No domain is significantly enriched"; `formatP(0.0000999, 10000)` → "< 0.0001". Component: rows sorted by q; significant rows carry `data-significant="true"`; each row exposes 2×2 counts on focus (tooltip text in DOM); `withheld`/`too-few`/`error` states render their messages and no table; caveat text present verbatim.
- [ ] **Step 2: Run** the two specs → FAIL.
- [ ] **Step 3: Implement** using shadcn primitives (`Table`, `Button`, `Collapsible`) and the colour rules in Global Constraints; numbers `tabular-nums`; table twin always rendered.
- [ ] **Step 4: Run** specs PASS; then visual check at 360/768/1440 light + dark on the dev server (`http://localhost:5181/genes/HNF1B/structure?view=protein`) via Playwright with `CHROME_PATH`-style executablePath `/usr/bin/google-chrome`; validate the meaning hue vs both card surfaces with `node /tmp/claude-1000/bundled-skills/2.1.316/050d946d2caab694f6eb368ebaef352a/dataviz/scripts/validate_palette.js "<hex>,<hex>" --mode light` and `--mode dark` (report output).
- [ ] **Step 5: Hand the diff + screenshots to review.**

### Task 8: 3D UI — spatial statistics, histogram, Hotspots colour mode

**Files:**
- Create: `frontend/src/components/visualizations/stats/SpatialStatistics.vue` (sentence, null histogram SVG with observed line and 95% null span, table twin, hotspot cluster list emitting `select-cluster(residues: number[])`, Methods via `StatsMethods`)
- Modify: `frontend/src/components/visualizations/ProteinStructure3D.vue` (after load: collect `Residue3D[]` from `.CA` atoms only when the model is full length; call `run3D`; add colour mode `'hotspots'` to `COLOR_MODES`; on `select-cluster`: zoom to `caSelection(residues)` and set the query/region filter to those residues; render `SpatialStatistics` below the legend; fragment/no-model message per spec)
- Test: `frontend/src/components/visualizations/stats/__tests__/SpatialStatistics.spec.ts`

**Interfaces:**
- Consumes: `usePositionStats().run3D`, `spatial`, `StatsMethods`, `clusterSentence`.
- [ ] **Step 1: Write failing tests:** renders sentence with observed and null numbers; histogram has one `rect` per non-empty bin and one observed `line` with `aria-label` containing the observed value; clicking a cluster emits its residues; partial model (`uniprotStart > 1` or `uniprotEnd < length`) renders "No full-length AlphaFold model for this protein, so no 3D statistics." (Review Focus 4).
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** → PASS; visual check of `?view=3d` at 360/768/1440 light + dark; Hotspots colour mode screenshot.
- [ ] **Step 5: Hand the diff + screenshots to review.**

### Task 9: Real data, evaluation, design review

**Files:**
- Modify: `.planning/specs/2026-10-31-variant-position-statistics-design.md` (Results section)

- [ ] **Step 1:** Re-run ClinVar on the local backend (:8010) through the pipeline API (admin token): `POST /api/annotations/pipeline/update` with sources `["clinvar"]`, `strategy=full`, `force=true`; poll `/api/annotations/pipeline/status` until done; confirm `missense_residues` present for HNF1B (gene 6517).
- [ ] **Step 2:** Results for HNF1B and UMOD (full-length AlphaFold model) and PKD1 (no model): domain table top rows, scan regions, 3D p and clusters, timings; compare with MetaDome intolerant region 123–171 for HNF1B. Write into the spec Results section (report, don't assert).
- [ ] **Step 3:** impeccable `critique` and `audit` on both sections (360/768/1440, light/dark); fix findings or list deferrals in the Results section.
- [ ] **Step 4:** Stability harness on `/genes/HNF1B/structure?view=protein` and `?view=3d` (production image): CLS 0 target; report.
- [ ] **Step 5:** Full gates (`/tmp/.../scratchpad/gates.sh`) → `GATES EXIT=0`.
