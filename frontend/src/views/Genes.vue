<template>
  <div class="container mx-auto px-4 py-6">
    <div class="mb-6">
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
      <div class="flex items-center gap-2 mt-2">
        <Dna class="size-6 text-primary" />
        <h1 class="text-2xl font-bold">Gene Browser</h1>
      </div>
      <p class="text-sm text-muted-foreground">
        Search and explore curated kidney disease gene-disease associations with evidence scores
      </p>
    </div>

    <GeneTable />
  </div>
</template>

<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { Dna } from 'lucide-vue-next'
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator
} from '@/components/ui/breadcrumb'
import GeneTable from '@/components/GeneTable.vue'
import { PUBLIC_BREADCRUMBS } from '@/utils/publicBreadcrumbs'
import { useSeoMeta } from '@/composables/useSeoMeta'
import { useJsonLd, getBreadcrumbSchema } from '@/composables/useJsonLd'

const breadcrumbs = PUBLIC_BREADCRUMBS.genes

useJsonLd(getBreadcrumbSchema(breadcrumbs))

useSeoMeta({
  title: 'Gene Browser',
  description:
    'Search and explore curated kidney disease gene-disease associations with evidence scores from multiple genomic sources.',
  canonicalPath: '/genes'
})
</script>
