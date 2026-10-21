<template>
  <div class="container mx-auto px-4 py-6">
    <!-- Breadcrumb -->
    <Breadcrumb class="mb-2">
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

    <!-- Page Header -->
    <div class="flex items-center gap-3 mb-6">
      <Info class="size-6 text-primary" />
      <div>
        <h1 class="text-2xl font-bold">About This Database</h1>
        <p class="text-sm text-muted-foreground">
          Learn how to use the database, understand core concepts, and see how evidence is scored
        </p>
      </div>
    </div>

    <!-- How to Use Section -->
    <div class="mb-8">
      <div class="flex items-center gap-2 mb-4">
        <Compass class="size-4 text-primary" />
        <h2 class="text-2xl font-medium">How to Use This Database</h2>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <!-- Gene Search Card -->
        <Card class="h-full">
          <CardHeader class="flex flex-row items-center gap-3 pb-2">
            <div
              class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary"
            >
              <Search class="size-4 text-primary-foreground" />
            </div>
            <CardTitle class="text-base">Search & Browse Genes</CardTitle>
          </CardHeader>
          <CardContent>
            <p class="text-sm text-muted-foreground mb-3">
              Navigate to the
              <RouterLink
                to="/genes"
                class="text-primary underline underline-offset-4 hover:text-primary/80"
                >Gene Browser</RouterLink
              >
              to search curated kidney disease genes by symbol, HGNC ID, or disease association.
            </p>
            <div class="flex flex-wrap gap-2">
              <Badge variant="secondary">
                <Filter class="size-3 mr-1" />
                Filter by evidence score
              </Badge>
              <Badge variant="secondary">
                <ArrowUpDown class="size-3 mr-1" />
                Sort by any column
              </Badge>
            </div>
          </CardContent>
        </Card>

        <!-- Evidence Scores Card -->
        <Card class="h-full">
          <CardHeader class="flex flex-row items-center gap-3 pb-2">
            <div
              class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-green-600"
            >
              <ChartLine class="size-4 text-white" />
            </div>
            <CardTitle class="text-base">Understanding Evidence Scores</CardTitle>
          </CardHeader>
          <CardContent>
            <p class="text-sm text-muted-foreground mb-3">
              Evidence scores reflect confidence in gene-disease associations based on multiple
              authoritative sources. Higher scores indicate stronger evidence from multiple
              independent sources.
            </p>
            <div class="space-y-1 text-sm">
              <div
                v-for="tier in TIER_CONFIG"
                :key="tier.label"
                class="flex items-center gap-2"
                data-testid="tier-row"
              >
                <Badge variant="outline" class="shrink-0" :style="tintedChipStyle(tier.color)">
                  <span>{{ tier.label }}</span>
                </Badge>
                <span class="text-muted-foreground">{{ tier.description }}</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <!-- Annotations Card -->
        <Card class="h-full">
          <CardHeader class="flex flex-row items-center gap-3 pb-2">
            <div
              class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full"
              style="background-color: #8b5cf6"
            >
              <Database class="size-4 text-white" />
            </div>
            <CardTitle class="text-base">Exploring Annotations</CardTitle>
          </CardHeader>
          <CardContent>
            <p class="text-sm text-muted-foreground mb-3">
              Each gene includes rich annotations from multiple sources: HGNC (nomenclature), gnomAD
              (constraint), ClinVar (variants), HPO (phenotypes), GTEx (expression), Descartes
              (single-cell), MPO/MGI (mouse models), STRING (interactions), and PubTator
              (literature).
            </p>
            <Badge variant="secondary">
              <CircleCheck class="size-3 mr-1" />
              Multi-source annotations
            </Badge>
          </CardContent>
        </Card>

        <!-- API Access Card -->
        <Card class="h-full">
          <CardHeader class="flex flex-row items-center gap-3 pb-2">
            <div
              class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-blue-600"
            >
              <Code class="size-4 text-white" />
            </div>
            <CardTitle class="text-base">API Access & Export</CardTitle>
          </CardHeader>
          <CardContent>
            <p class="text-sm text-muted-foreground mb-3">
              Access data programmatically via our JSON:API compliant REST API. Visit
              <a
                href="/docs"
                target="_blank"
                class="text-primary underline underline-offset-4 hover:text-primary/80"
                >/docs</a
              >
              for interactive API documentation.
            </p>
            <div class="flex flex-wrap gap-2">
              <Badge variant="secondary">
                <FileJson class="size-3 mr-1" />
                JSON export
              </Badge>
              <Badge variant="secondary">
                <FileSpreadsheet class="size-3 mr-1" />
                CSV export
              </Badge>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>

    <!-- Core Concepts Section -->
    <div class="mb-8">
      <div class="flex items-center gap-2 mb-4">
        <Lightbulb class="size-4 text-primary" />
        <h2 class="text-2xl font-medium">Core Concepts</h2>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <Card
          v-for="concept in coreConcepts"
          :key="concept.title"
          class="concept-card h-full overflow-hidden"
        >
          <div class="p-4" :style="{ background: concept.gradient }">
            <component :is="concept.icon" class="size-6 text-white mb-2" />
            <h3 class="text-lg font-bold text-white">{{ concept.title }}</h3>
          </div>
          <CardContent class="p-4">
            <p class="text-sm text-muted-foreground mb-3">{{ concept.description }}</p>
            <div class="text-xs space-y-1">
              <div v-for="bullet in concept.bullets" :key="bullet" class="flex items-start gap-1">
                <component
                  :is="concept.bulletIcon"
                  class="size-3 shrink-0 mt-0.5"
                  :class="concept.bulletClass"
                />
                <span>{{ bullet }}</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>

    <!-- Open Source & Documentation -->
    <div class="mb-8">
      <div class="flex items-center gap-2 mb-4">
        <Code class="size-4 text-primary" />
        <h2 class="text-2xl font-medium">Open Source & Documentation</h2>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <!-- GitHub Card -->
        <Card class="h-full">
          <CardHeader class="flex flex-row items-center gap-3 pb-2">
            <div
              class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary"
            >
              <Github class="size-4 text-primary-foreground" />
            </div>
            <CardTitle class="text-base">Source Code & Issues</CardTitle>
          </CardHeader>
          <CardContent>
            <p class="text-sm text-muted-foreground mb-4">
              This project is open source (MIT License). View source code, report issues, or
              contribute on GitHub.
            </p>
            <Button
              as="a"
              href="https://github.com/bernt-popp/kidney-genetics-db"
              target="_blank"
              size="sm"
            >
              <Github class="size-4 mr-2" />
              View on GitHub
            </Button>
          </CardContent>
        </Card>

        <!-- Docs Card -->
        <Card class="h-full">
          <CardHeader class="flex flex-row items-center gap-3 pb-2">
            <div
              class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-blue-600"
            >
              <BookOpen class="size-4 text-white" />
            </div>
            <CardTitle class="text-base">Technical Documentation</CardTitle>
          </CardHeader>
          <CardContent>
            <p class="text-sm text-muted-foreground mb-4">
              Comprehensive technical documentation covering architecture, API reference,
              development guides, and troubleshooting.
            </p>
            <Button
              as="a"
              href="https://github.com/bernt-popp/kidney-genetics-db/tree/main/docs"
              target="_blank"
              size="sm"
              variant="secondary"
            >
              <BookOpen class="size-4 mr-2" />
              View Documentation
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { PUBLIC_BREADCRUMBS } from '@/utils/publicBreadcrumbs'
import { TIER_CONFIG, tintedChipStyle } from '@/utils/evidenceTiers'
import { useSeoMeta } from '@/composables/useSeoMeta'
import { useJsonLd, getBreadcrumbSchema } from '@/composables/useJsonLd'
import {
  ArrowLeftRight,
  ArrowRight,
  ArrowUpDown,
  BookOpen,
  ChartBar,
  Check,
  ChartLine,
  CircleCheck,
  Code,
  Compass,
  Database,
  FileJson,
  FileSpreadsheet,
  Filter,
  Github,
  Info,
  Lightbulb,
  RefreshCw,
  Search
} from 'lucide-vue-next'
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator
} from '@/components/ui/breadcrumb'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'

const breadcrumbs = PUBLIC_BREADCRUMBS.about

useJsonLd(getBreadcrumbSchema(breadcrumbs))

useSeoMeta({
  title: 'About — Kidney Genetics Database Methodology',
  description:
    'Learn how the Kidney Genetics Database curates kidney disease genes. Evidence scoring methodology, multi-source integration, and kidney gene curation workflow.',
  canonicalPath: '/about'
})

const coreConcepts = [
  {
    title: 'Gene Staging System',
    icon: ArrowLeftRight,
    gradient: 'linear-gradient(135deg, #0ea5e9, #0284c7)',
    description:
      'Two-stage data ingestion ensures quality: genes first enter a staging area for normalization and validation, then move to curated status after passing quality checks.',
    bullets: [
      'Staging: Raw data ingestion + HGNC normalization',
      'Curated: Validated genes with complete annotations'
    ],
    bulletIcon: ArrowRight,
    bulletClass: ''
  },
  {
    title: 'Multi-Source Integration',
    icon: RefreshCw,
    gradient: 'linear-gradient(135deg, #10b981, #059669)',
    description:
      'Aggregates evidence from multiple authoritative sources with automatic retry logic and cache validation. Each source contributes unique annotations: nomenclature, constraint scores, variants, phenotypes, expression, interactions, and literature.',
    bullets: [
      'Comprehensive annotation coverage',
      'Exponential backoff retry with circuit breaker'
    ],
    bulletIcon: Check,
    bulletClass: 'text-green-600 dark:text-green-400'
  },
  {
    title: 'Evidence Scoring',
    icon: ChartBar,
    gradient: 'linear-gradient(135deg, #8b5cf6, #7c3aed)',
    description:
      'Weighted scoring algorithm aggregates evidence from multiple sources to produce a confidence score (0-100). Scores are dynamic and update automatically as new evidence becomes available from our data sources.',
    bullets: ['Configurable source weights', 'Transparent calculation methodology'],
    bulletIcon: ArrowRight,
    bulletClass: ''
  }
]
</script>

<style scoped>
.concept-card {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.concept-card:hover {
  transform: translateY(-2px);
}

@media (prefers-reduced-motion: reduce) {
  .concept-card {
    transition-duration: 0.01ms !important;
  }

  .concept-card:hover {
    transform: none;
  }
}
</style>
