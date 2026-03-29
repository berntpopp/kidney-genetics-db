<template>
  <div class="container mx-auto px-4 py-8 max-w-3xl">
    <!-- Breadcrumb -->
    <nav aria-label="breadcrumb" class="mb-4">
      <ol class="flex items-center gap-1.5 text-sm text-muted-foreground">
        <li><RouterLink to="/" class="hover:text-foreground">Home</RouterLink></li>
        <li class="text-muted-foreground/60">/</li>
        <li class="text-foreground font-medium">FAQ</li>
      </ol>
    </nav>

    <h1 class="text-2xl font-bold mb-2">Frequently Asked Questions</h1>
    <p class="text-muted-foreground mb-8">
      Common questions about the Kidney Genetics Database and how to use it.
    </p>

    <div class="space-y-4">
      <div v-for="(faq, index) in faqs" :key="index" class="rounded-lg border border-border">
        <button
          class="flex w-full items-center justify-between p-4 text-left font-medium hover:bg-muted/50 transition-colors"
          :aria-expanded="openIndex === index"
          @click="openIndex = openIndex === index ? null : index"
        >
          <span>{{ faq.question }}</span>
          <ChevronDown
            class="size-4 text-muted-foreground transition-transform duration-200"
            :class="{ 'rotate-180': openIndex === index }"
          />
        </button>
        <div
          v-if="openIndex === index"
          class="px-4 pb-4 text-sm text-muted-foreground leading-relaxed"
        >
          <p v-for="(para, i) in faq.answer" :key="i" class="mb-2 last:mb-0">
            {{ para }}
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { RouterLink } from 'vue-router'
import { ChevronDown } from 'lucide-vue-next'
import { useSeoMeta } from '@/composables/useSeoMeta'
import { useJsonLd, getBreadcrumbSchema } from '@/composables/useJsonLd'

const openIndex = ref<number | null>(null)

useSeoMeta({
  title: 'FAQ — Kidney Genetics Database',
  description:
    'Frequently asked questions about the Kidney Genetics Database (KGDB). Learn about gene evidence scoring, data sources, kidney gene curation methodology, and how to use the API.',
  canonicalPath: '/faq'
})

const breadcrumbs = [
  { title: 'Home', to: '/' },
  { title: 'FAQ', to: null }
]
useJsonLd(computed(() => getBreadcrumbSchema(breadcrumbs)))

const faqs = [
  {
    question: 'What genes are included in the Kidney Genetics Database?',
    answer: [
      'KGDB contains over 5,000 genes associated with kidney diseases, curated from 7 authoritative sources: PanelApp (UK and Australia), ClinGen, GenCC, HPO, PubTator, curated literature, and commercial diagnostic panels.',
      'Genes are included if they have at least one kidney disease association reported by any of these sources. Each gene receives an evidence score from 0 to 100 based on the strength and breadth of supporting evidence.'
    ]
  },
  {
    question: 'How is the evidence score calculated?',
    answer: [
      'The evidence score is a weighted composite score (0-100) that aggregates data from all available sources. Each source contributes a sub-score based on the strength of its evidence. For example, a gene classified as "Definitive" by ClinGen receives a higher sub-score than one classified as "Limited".',
      'Genes scoring 95-100 are classified as "Definitive", 80-94 as "Strong", 50-79 as "Moderate/Limited". The scoring methodology ensures that genes supported by multiple independent sources rank higher than those from a single source.'
    ]
  },
  {
    question: 'How often is the database updated?',
    answer: [
      'The database is updated continuously through an automated pipeline that synchronizes with upstream data sources. Each source is checked for new data regularly, and gene evidence scores are recalculated whenever new evidence becomes available.',
      'You can see the last update date on the homepage and the detailed status of each data source on the Data Sources page.'
    ]
  },
  {
    question: 'Can I access the data programmatically?',
    answer: [
      'Yes. KGDB provides a JSON:API compliant REST API for programmatic access. You can query genes, filter by evidence score, and retrieve detailed annotations. The API documentation is available at /api/docs (Swagger UI).',
      'All public data is freely accessible without authentication under the CC BY 4.0 license.'
    ]
  },
  {
    question: 'How should I cite the Kidney Genetics Database?',
    answer: [
      'Please cite: Popp B, Rank N, Wolff A, Halbritter J. Kidney-Genetics: An evidence-based database for kidney disease associated genes. Nephrol Dial Transplant. 2024;39(Supplement_1):gfae069-0787-2170.',
      'You can also use: Kidney Genetics Database. https://kidney-genetics.org. Accessed [date].'
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
      text: faq.answer.join(' ')
    }
  }))
})
</script>
