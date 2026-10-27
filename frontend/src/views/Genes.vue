<template>
  <div :class="PAGE_CONTAINER">
    <PageHeader
      title="Gene Browser"
      description="Search and filter kidney-disease genes by evidence score, tier and source."
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

    <ErrorBoundary fallback-message="Gene table failed to render.">
      <GeneTable />
    </ErrorBoundary>
  </div>
</template>

<script setup lang="ts">
import { RouterLink } from 'vue-router'
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator
} from '@/components/ui/breadcrumb'
import GeneTable from '@/components/GeneTable.vue'
import ErrorBoundary from '@/components/ui/error-boundary/ErrorBoundary.vue'
import { PageHeader, PAGE_CONTAINER } from '@/components/shared'
import { PUBLIC_BREADCRUMBS } from '@/utils/publicBreadcrumbs'
import { useSeoMeta } from '@/composables/useSeoMeta'
import { useJsonLd, getBreadcrumbSchema } from '@/composables/useJsonLd'

const breadcrumbs = PUBLIC_BREADCRUMBS.genes

useJsonLd(getBreadcrumbSchema(breadcrumbs))

useSeoMeta({
  title: 'Gene Browser — Kidney Disease Genes',
  description:
    'Browse and search curated kidney disease genes with evidence scores. Filter by gene symbol, nephropathy type, or annotation source. Comprehensive nephrology gene panel and renal genetics resource.',
  canonicalPath: '/genes'
})
</script>
