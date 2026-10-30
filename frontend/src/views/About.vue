<template>
  <div :class="PAGE_CONTAINER">
    <PageHeader
      title="About the Kidney-Genetics Database"
      description="How genes are scored and tiered, which sources contribute, and how to cite the database."
    >
      <template #breadcrumb>
        <Breadcrumb>
          <BreadcrumbList>
            <BreadcrumbItem v-for="(crumb, index) in breadcrumbs" :key="index">
              <BreadcrumbLink v-if="!crumb.disabled && crumb.to" as-child>
                <RouterLink :to="crumb.to">{{ crumb.title }}</RouterLink>
              </BreadcrumbLink>
              <BreadcrumbPage v-else>{{ crumb.title }}</BreadcrumbPage>
              <BreadcrumbSeparator v-if="index < breadcrumbs.length - 1" />
            </BreadcrumbItem>
          </BreadcrumbList>
        </Breadcrumb>
      </template>
    </PageHeader>

    <div class="lg:grid lg:grid-cols-[minmax(0,1fr)_13rem] lg:gap-12">
      <div class="min-w-0 space-y-12 leading-relaxed [&_h2]:scroll-mt-20 [&_p]:max-w-[90ch]">
        <section aria-labelledby="about-what" class="space-y-3">
          <h2 id="about-what" class="text-xl font-semibold tracking-tight">What it is</h2>
          <!-- Gene and source counts change with every data release; bind live statistics here, never hard-code them -->
          <p>
            The Kidney-Genetics Database brings together evidence that a gene is linked to kidney
            disease from expert curations, diagnostic panels, phenotype annotations and the
            literature. Each gene gets one reproducible evidence score and an evidence tier, and
            every score can be traced back to the sources behind it.
          </p>
          <p>
            It is the successor of the published
            <a :href="R_PIPELINE_URL" target="_blank" rel="noopener noreferrer" :class="LINK"
              >kidney-genetics R pipeline</a
            >. Browse the results in the
            <RouterLink to="/genes" :class="LINK">gene browser</RouterLink>, or see the overall
            picture on the <RouterLink to="/dashboard" :class="LINK">dashboard</RouterLink>.
          </p>
        </section>

        <section id="scoring" aria-labelledby="about-scoring" class="scroll-mt-20 space-y-4">
          <h2 id="about-scoring" class="text-xl font-semibold tracking-tight">
            How the evidence score works
          </h2>
          <ol class="list-decimal space-y-3 pl-5 marker:text-muted-foreground">
            <li>
              <strong class="font-semibold">Each source scores the gene from 0 to 1.</strong>
              ClinGen and GenCC score by their gene-disease validity classification, with Definitive
              highest. The other sources score by how much evidence they hold for the gene (panels,
              phenotype terms and diseases, or publications), as a percentile rank among all genes
              in that source.
            </li>
            <li>
              <strong class="font-semibold">The source scores are combined into 0 to 100.</strong>
              The gene's source scores are added up, divided by the number of scoring sources and
              multiplied by 100. A source that has no evidence for a gene counts as no support, so a
              gene supported by many independent sources ranks above one with strong support from a
              single source.
            </li>
            <li>
              <strong class="font-semibold"
                >The score and the number of sources set the tier.</strong
              >
              A gene gets the highest tier whose score and source count it meets. Established
              Support and above also need at least one curated gene–disease assertion (ClinGen,
              GenCC, PanelApp or Diagnostic Panels); count-only evidence (HPO, PubTator, Literature)
              reaches at most Preliminary Evidence.
            </li>
          </ol>

          <dl class="divide-y rounded-lg border bg-card text-sm">
            <div
              v-for="rule in tierRules"
              :key="rule.tier"
              class="grid gap-1 px-4 py-3 sm:grid-cols-[13rem_1fr] sm:items-center sm:gap-4"
              data-testid="tier-row"
            >
              <dt><Chip :tier="rule.tier" :tooltip="rule.text" /></dt>
              <dd class="text-muted-foreground">{{ rule.text }}</dd>
            </div>
          </dl>
          <p class="text-sm text-muted-foreground">
            A gene with a score of 0 has no tier and is shown as "No Classification". See
            <a href="#faq" :class="LINK">Questions</a> for syndromic genes, clinical groups and
            update frequency.
          </p>
        </section>

        <section aria-labelledby="about-sources" class="space-y-4">
          <h2 id="about-sources" class="text-xl font-semibold tracking-tight">Evidence sources</h2>
          <p>These sources contribute to the evidence score:</p>
          <dl class="grid overflow-hidden rounded-lg border bg-card text-sm sm:grid-cols-2">
            <div
              v-for="name in SOURCE_NAMES"
              :key="name"
              class="border-t px-4 py-3 first:border-t-0 sm:odd:border-r sm:[&:nth-child(2)]:border-t-0"
            >
              <dt class="font-medium">{{ sourceDisplayName(name) }}</dt>
              <dd class="text-muted-foreground">{{ getSourceConfig(name).description }}</dd>
            </div>
          </dl>
          <p>
            Gene pages add annotations that give context but do not change the score: HGNC
            (nomenclature), gnomAD (constraint), ClinVar (variants), GTEx (expression), Descartes
            (single-cell expression), MPO/MGI (mouse models), STRING (interactions), Ensembl and
            UniProt. The <RouterLink to="/data-sources" :class="LINK">Data Sources</RouterLink> page
            shows the status and last update of each source.
          </p>
        </section>

        <section aria-labelledby="about-releases" class="space-y-3">
          <h2 id="about-releases" class="text-xl font-semibold tracking-tight">
            Releases and versions
          </h2>
          <p>The database has two independent version streams:</p>
          <ul class="list-disc space-y-1 pl-5 marker:text-muted-foreground">
            <li>
              <strong class="font-semibold">Data releases</strong> use calendar versions (<span
                class="font-mono text-sm"
                >YYYY.MM</span
              >) and get their own dataset DOI.
            </li>
            <li>
              <strong class="font-semibold">Software releases</strong> use semantic versions and are
              archived on Zenodo with a software DOI. See the
              <a
                :href="`${GITHUB_URL}/releases`"
                target="_blank"
                rel="noopener noreferrer"
                :class="LINK"
                >release notes</a
              >.
            </li>
          </ul>
        </section>

        <section aria-labelledby="about-cite" class="space-y-3">
          <h2 id="about-cite" class="text-xl font-semibold tracking-tight">How to cite</h2>
          <p>Please cite the publication and the software archive:</p>
          <ul class="space-y-3 text-sm">
            <li class="rounded-lg border bg-card p-4">
              Popp B, Rank N, Wolff A, Halbritter J. Kidney-Genetics: An evidence-based database for
              kidney disease associated genes. <i>Nephrol Dial Transplant.</i>
              2024;39(Supplement_1):gfae069-0787-2170.
            </li>
            <li class="rounded-lg border bg-card p-4">
              Popp B. Kidney-Genetics Database. Zenodo.
              <a
                :href="`https://doi.org/${ZENODO_DOI}`"
                target="_blank"
                rel="noopener noreferrer"
                :class="LINK"
                >doi:{{ ZENODO_DOI }}</a
              >
              <span class="mt-1 block text-muted-foreground">
                This DOI always resolves to the latest version; cite the version and data release
                you used.
              </span>
            </li>
          </ul>
        </section>

        <section aria-labelledby="about-access" class="space-y-3">
          <h2 id="about-access" class="text-xl font-semibold tracking-tight">
            Programmatic access and source code
          </h2>
          <p>
            All public data is available through a REST API; the
            <a :href="apiDocsUrl" target="_blank" rel="noopener noreferrer" :class="LINK"
              >API documentation</a
            >
            is interactive. AI agents can use the read-only
            <RouterLink to="/mcp" :class="LINK">MCP server</RouterLink>.
          </p>
          <p>
            The code is open source under the MIT License. Report issues or contribute on GitHub.
          </p>
          <div class="flex flex-wrap gap-2 pt-1">
            <Button as="a" :href="GITHUB_URL" target="_blank" rel="noopener noreferrer" size="sm">
              <Github class="size-4" aria-hidden="true" />
              View on GitHub
            </Button>
            <Button
              as="a"
              :href="`${GITHUB_URL}#readme`"
              target="_blank"
              rel="noopener noreferrer"
              size="sm"
              variant="outline"
            >
              <BookOpen class="size-4" aria-hidden="true" />
              Read the documentation
            </Button>
          </div>
        </section>

        <section id="faq" aria-labelledby="about-faq" class="scroll-mt-20 space-y-6">
          <h2 id="about-faq" class="text-xl font-semibold tracking-tight">Questions</h2>
          <div v-for="item in questions" :key="item.question" class="space-y-2">
            <h3 class="text-base font-semibold">{{ item.question }}</h3>
            <p v-for="(para, i) in item.answer" :key="i">
              <template v-for="(seg, j) in segments(para)" :key="j">
                <template v-if="typeof seg === 'string'">{{ seg }}</template>
                <a v-else-if="seg.href" :href="seg.href" :class="LINK">{{ seg.text }}</a>
                <RouterLink v-else :to="seg.to!" :class="LINK">{{ seg.text }}</RouterLink>
              </template>
            </p>
          </div>
        </section>
      </div>

      <nav aria-label="On this page" class="hidden lg:block">
        <div class="sticky top-20 space-y-3 border-l pl-4 text-sm">
          <p class="font-semibold">On this page</p>
          <ul class="space-y-2">
            <li v-for="item in toc" :key="item.id">
              <a :href="`#${item.id}`" class="text-muted-foreground hover:text-foreground">
                {{ item.label }}
              </a>
            </li>
          </ul>
        </div>
      </nav>
    </div>
  </div>
</template>

<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { BookOpen, Github } from 'lucide-vue-next'
import { config } from '@/config'
import { PUBLIC_BREADCRUMBS } from '@/utils/publicBreadcrumbs'
import type { TierName } from '@/utils/evidenceTiers'
import { SOURCE_NAMES, getSourceConfig, sourceDisplayName } from '@/utils/sources'
import { useSeoMeta } from '@/composables/useSeoMeta'
import { useJsonLd, getBreadcrumbSchema } from '@/composables/useJsonLd'
import { Chip, PageHeader, PAGE_CONTAINER } from '@/components/shared'

const toc = [
  { id: 'about-what', label: 'What it is' },
  { id: 'about-scoring', label: 'How the score works' },
  { id: 'about-sources', label: 'Evidence sources' },
  { id: 'about-releases', label: 'Releases and versions' },
  { id: 'about-cite', label: 'How to cite' },
  { id: 'about-access', label: 'Access and source code' },
  { id: 'faq', label: 'Questions' }
]
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator
} from '@/components/ui/breadcrumb'
import { Button } from '@/components/ui/button'

const breadcrumbs = PUBLIC_BREADCRUMBS.about

useJsonLd(getBreadcrumbSchema(breadcrumbs))

/** An answer paragraph: plain text, or text with in-page (href) and route (to) links */
type Segment = string | { text: string; to?: string; href?: string }
type Paragraph = string | Segment[]
const segments = (para: Paragraph): Segment[] => (typeof para === 'string' ? [para] : para)
const plainText = (para: Paragraph) =>
  segments(para)
    .map(seg => (typeof seg === 'string' ? seg : seg.text))
    .join('')

// Scoring, sources, citation and API access are answered by the sections above, not repeated here
const questions: { question: string; answer: Paragraph[] }[] = [
  {
    question: 'Which kidney diseases are covered?',
    answer: [
      [
        'There is no fixed disease list. A gene is included when at least one ',
        { text: 'evidence source', href: '#about-sources' },
        ' links it to kidney disease, so coverage spans the genetic kidney diseases those sources curate: for example polycystic kidney disease, Alport syndrome, nephronophthisis, focal segmental glomerulosclerosis, congenital nephrotic syndrome, tubulopathies and congenital anomalies of the kidney and urinary tract (CAKUT).'
      ]
    ]
  },
  {
    question: 'Why do some genes have no tier?',
    answer: [
      [
        'A tier requires a score above 0 (see ',
        { text: 'How the evidence score works', href: '#scoring' },
        '). Genes with a score of 0 are shown as "No Classification". This includes genes whose only evidence is a "No Known Disease Relationship" or an unknown GenCC classification.'
      ]
    ]
  },
  {
    question: 'When is a gene called syndromic?',
    answer: [
      "When its HPO phenotypes clearly reach beyond the kidney. We count the distinct HPO terms that fall under growth, skeletal, nervous-system, or head-and-neck abnormalities (a term in two of these groups counts once) and divide by the gene's total number of HPO terms. If at least 30% of its terms are extra-renal, the gene is labelled syndromic; otherwise it is isolated."
    ]
  },
  {
    question: 'How is the clinical group assigned?',
    answer: [
      'Each clinical group (complement, CAKUT, glomerulopathy, cystic/ciliopathy, tubulopathy, nephrolithiasis, renal neoplasia) is defined by a few HPO root terms; a phenotype counts for a group when it is one of these terms or a more specific term below it.',
      "For every disease linked to the gene, each matching phenotype adds its frequency in that disease times its information content (rarer, more specific terms weigh more). Where a disease lists both a term and a term below it, only the more specific term counts. The group with the most evidence summed over the gene's diseases is the primary group; other groups with at least half of the primary group's evidence are shown as secondary groups. The score shown is the group's share of the gene's kidney-group evidence.",
      'Classifications use the pinned HPO release 2026-09-01.'
    ]
  },
  {
    question: 'How often is the data updated?',
    answer: [
      'Updates are scheduled runs, not a continuous feed. Evidence sources are re-imported in update runs started by the database maintainers. Gene annotations, including the HPO phenotypes behind the syndromic and clinical-group labels, are refreshed by an automated pipeline: every night for genes with missing or incomplete annotations, and once a week for all genes.',
      [
        'The ',
        { text: 'Data Sources', to: '/data-sources' },
        ' page shows when each source was last updated. Citable snapshots are published as data releases (see ',
        { text: 'Releases and versions', href: '#about-releases' },
        ').'
      ]
    ]
  }
]

useJsonLd({
  '@context': 'https://schema.org',
  '@type': 'FAQPage',
  mainEntity: questions.map(item => ({
    '@type': 'Question',
    name: item.question,
    acceptedAnswer: { '@type': 'Answer', text: item.answer.map(plainText).join(' ') }
  }))
})

useSeoMeta({
  title: 'About — Kidney Genetics Database Methodology',
  description:
    'How the Kidney Genetics Database scores kidney disease genes: evidence sources, the 0–100 evidence score, evidence tiers, clinical groups, update schedule, releases and how to cite.',
  canonicalPath: '/about'
})

const LINK = 'text-primary underline underline-offset-4 hover:text-primary/80'
const GITHUB_URL = 'https://github.com/berntpopp/kidney-genetics-db'
const R_PIPELINE_URL = 'https://github.com/halbritter-lab/kidney-genetics'
// Zenodo concept DOI (CITATION.cff): resolves to the latest archived version
const ZENODO_DOI = '10.5281/zenodo.19316248'
// Swagger UI lives at the backend root /docs (same rule as AppFooter)
const apiDocsUrl = `${config.apiBaseUrl}/docs`

// Tier rules of the gene_scores view (backend/app/db/views.py), on the 0–100 score scale
const tierRules: { tier: TierName; text: string }[] = [
  { tier: 'comprehensive_support', text: 'Score ≥ 50 with evidence from at least 4 sources' },
  { tier: 'multi_source_support', text: 'Score ≥ 35 with evidence from at least 3 sources' },
  { tier: 'established_support', text: 'Score ≥ 20 with evidence from at least 2 sources' },
  { tier: 'preliminary_evidence', text: 'Score ≥ 10' },
  { tier: 'minimal_evidence', text: 'Score above 0 and below 10' }
]
</script>
