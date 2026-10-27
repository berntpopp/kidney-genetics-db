<template>
  <div :class="PAGE_CONTAINER">
    <PageHeader
      title="Frequently asked questions"
      description="Common questions about the Kidney Genetics Database and how to use it."
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

    <!-- Answers stay in the prerendered HTML -->
    <Accordion
      type="single"
      collapsible
      :unmount-on-hide="false"
      class="max-w-3xl divide-y rounded-lg border bg-card"
    >
      <AccordionItem
        v-for="(faq, index) in faqs"
        :key="index"
        :value="String(index)"
        class="border-b-0"
      >
        <AccordionTrigger
          heading-tag="h2"
          class="rounded-none px-4 py-4 text-base font-semibold hover:bg-muted/50 hover:no-underline"
        >
          {{ faq.question }}
        </AccordionTrigger>
        <AccordionContent class="max-w-[70ch] px-4 text-sm leading-relaxed text-muted-foreground">
          <p v-for="(para, i) in faq.answer" :key="i" class="mb-3 last:mb-0">
            <template v-for="(seg, j) in segments(para)" :key="j">
              <template v-if="typeof seg === 'string'">{{ seg }}</template>
              <RouterLink v-else-if="seg.to" :to="seg.to" :class="LINK">{{ seg.text }}</RouterLink>
              <a v-else :href="seg.href" target="_blank" rel="noopener noreferrer" :class="LINK">{{
                seg.text
              }}</a>
            </template>
          </p>
        </AccordionContent>
      </AccordionItem>
    </Accordion>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { config } from '@/config'
import { PageHeader, PAGE_CONTAINER } from '@/components/shared'
import { getPublicBreadcrumbs } from '@/utils/publicBreadcrumbs'
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger
} from '@/components/ui/accordion'
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator
} from '@/components/ui/breadcrumb'
import { useSeoMeta } from '@/composables/useSeoMeta'
import { useJsonLd, getBreadcrumbSchema } from '@/composables/useJsonLd'
import { TIER_CONFIG } from '@/utils/evidenceTiers'

useSeoMeta({
  title: 'FAQ — Kidney Genetics Database',
  description:
    'Frequently asked questions about the Kidney Genetics Database (KGDB). Learn about gene evidence scoring, data sources, kidney gene curation methodology, and how to use the API.',
  canonicalPath: '/faq'
})

const breadcrumbs = getPublicBreadcrumbs('FAQ', '/faq')

const LINK = 'text-primary underline underline-offset-4 hover:text-primary/80'
// Swagger UI lives at the backend root /docs (same rule as AppFooter)
const apiDocsUrl = `${config.apiBaseUrl}/docs`

/** An answer paragraph: plain text, or text with internal (to) and external (href) links */
type Segment = string | { text: string; to?: string; href?: string }
type Paragraph = string | Segment[]
const segments = (para: Paragraph): Segment[] => (typeof para === 'string' ? [para] : para)
const plainText = (para: Paragraph) =>
  segments(para)
    .map(seg => (typeof seg === 'string' ? seg : seg.text))
    .join('')
useJsonLd(computed(() => getBreadcrumbSchema(breadcrumbs)))

const faqs: { question: string; answer: Paragraph[] }[] = [
  {
    question: 'What genes are included in the Kidney Genetics Database?',
    answer: [
      [
        'KGDB contains genes associated with kidney diseases, curated from these sources: PanelApp (UK and Australia), ClinGen, GenCC, HPO, PubTator, curated literature, and diagnostic panels. The ',
        { text: 'Data Sources', to: '/data-sources' },
        ' page lists each source with its current gene count.'
      ],
      'Genes are included if they have at least one kidney disease association reported by any of these sources. Each gene receives an evidence score from 0 to 100 based on the strength and breadth of supporting evidence.'
    ]
  },
  {
    question: 'How is the evidence score calculated?',
    answer: [
      'The evidence score is a weighted composite score (0-100) that aggregates data from all available sources. Each source contributes a sub-score based on the strength of its evidence. For example, a gene classified as "Definitive" by ClinGen receives a higher sub-score than one classified as "Limited".',
      [
        `Each gene is assigned an evidence tier from its score and the number of sources supporting it: ${Object.values(
          TIER_CONFIG
        )
          .map(t => `"${t.label}"`)
          .join(
            ', '
          )}. The scoring methodology ensures that genes supported by multiple independent sources rank higher than those from a single source. The `,
        { text: 'About page', to: '/about#scoring' },
        ' lists the score and source thresholds of each tier.'
      ],
      'Genes with a score of 0 have no tier and are shown as "No Classification". This includes genes whose only evidence is a "No Known Disease Relationship" or an unknown GenCC classification.'
    ]
  },
  {
    question: 'When is a gene called syndromic?',
    answer: [
      "A gene is called syndromic when its HPO phenotypes clearly reach beyond the kidney. We count the distinct HPO terms that fall under growth, skeletal, nervous-system, or head-and-neck abnormalities (a term in two of these groups counts once) and divide by the gene's total number of HPO terms. If at least 30% of its terms are extra-renal, the gene is labelled syndromic; otherwise it is isolated."
    ]
  },
  {
    question: 'How is the clinical group assigned?',
    answer: [
      "Each clinical group (complement, CAKUT, glomerulopathy, cystic/ciliopathy, tubulopathy, nephrolithiasis, renal neoplasia) is defined by a few HPO root terms; a phenotype counts for a group when it is one of these terms or a more specific term below it. For every disease linked to the gene, each matching phenotype adds its frequency in that disease times its information content (rarer, more specific terms weigh more), counting only the most specific term where a disease lists both a term and a term below it. The group with the most evidence summed over the gene's diseases is the primary group; other groups with at least half of the primary group's evidence are shown as secondary groups. The score shown is the group's share of the gene's kidney-group evidence. Classifications use the pinned HPO release 2026-09-01."
    ]
  },
  {
    question: 'How often is the database updated?',
    answer: [
      'The database is updated continuously through an automated pipeline that synchronizes with upstream data sources. Each source is checked for new data regularly, and gene evidence scores are recalculated whenever new evidence becomes available.',
      [
        'You can see the last update date on the homepage and the detailed status of each data source on the ',
        { text: 'Data Sources', to: '/data-sources' },
        ' page.'
      ]
    ]
  },
  {
    question: 'Can I access the data programmatically?',
    answer: [
      [
        'Yes. KGDB provides a JSON:API compliant REST API for programmatic access. You can query genes, filter by evidence score, and retrieve detailed annotations. See the interactive ',
        { text: 'API documentation', href: apiDocsUrl },
        '. AI agents can connect through the read-only ',
        { text: 'MCP server', to: '/mcp' },
        '.'
      ],
      'All public data is freely accessible without authentication under the CC BY 4.0 license.'
    ]
  },
  {
    question: 'How should I cite the Kidney Genetics Database?',
    answer: [
      'Please cite: Popp B, Rank N, Wolff A, Halbritter J. Kidney-Genetics: An evidence-based database for kidney disease associated genes. Nephrol Dial Transplant. 2024;39(Supplement_1):gfae069-0787-2170.',
      [
        'You can also use: Kidney Genetics Database. ',
        { text: 'https://kidney-genetics.org', href: 'https://kidney-genetics.org' },
        '. Accessed [date]. To cite the software, use its Zenodo DOI ',
        {
          text: '10.5281/zenodo.19316248',
          href: 'https://doi.org/10.5281/zenodo.19316248'
        },
        '.'
      ]
    ]
  },
  {
    question: 'What kidney diseases are covered?',
    answer: [
      'KGDB covers the full spectrum of genetic kidney diseases including polycystic kidney disease (ADPKD/ARPKD), Alport syndrome, nephronophthisis, focal segmental glomerulosclerosis (FSGS), congenital nephrotic syndrome, renal tubular disorders, and CAKUT (congenital anomalies of the kidney and urinary tract).',
      'Disease associations are derived from HPO phenotype terms, ClinGen gene-disease validity classifications, and GenCC submissions.'
    ]
  }
]

// FAQPage JSON-LD schema
useJsonLd({
  '@context': 'https://schema.org',
  '@type': 'FAQPage',
  mainEntity: faqs.map(faq => ({
    '@type': 'Question',
    name: faq.question,
    acceptedAnswer: {
      '@type': 'Answer',
      text: faq.answer.map(plainText).join(' ')
    }
  }))
})
</script>
