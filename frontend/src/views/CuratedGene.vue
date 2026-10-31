<template>
  <!-- One gene's expert-reviewed associations, without the rest of the gene page -->
  <div :class="PAGE_CONTAINER">
    <PageHeader :title="symbol" description="Expert-reviewed gene–disease associations">
      <template #breadcrumb>
        <Breadcrumb>
          <BreadcrumbList>
            <template v-for="(crumb, index) in breadcrumbs" :key="crumb.title">
              <BreadcrumbItem>
                <BreadcrumbPage v-if="index === breadcrumbs.length - 1">{{
                  crumb.title
                }}</BreadcrumbPage>
                <BreadcrumbLink v-else as-child>
                  <RouterLink :to="crumb.to ?? '/'">{{ crumb.title }}</RouterLink>
                </BreadcrumbLink>
              </BreadcrumbItem>
              <BreadcrumbSeparator v-if="index < breadcrumbs.length - 1" />
            </template>
          </BreadcrumbList>
        </Breadcrumb>
      </template>
      <template #actions>
        <Button variant="outline" size="sm" as-child>
          <RouterLink :to="`/genes/${symbol}`">Evidence and gene page</RouterLink>
        </Button>
      </template>
    </PageHeader>

    <!-- The automated score is a separate layer: curations never feed it -->
    <p
      class="mb-4 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-muted-foreground"
      data-testid="kgdb-score"
    >
      <template v-if="gene?.evidence_score != null">
        <span>KGDB evidence score</span>
        <span class="font-medium text-foreground tabular-nums">{{
          Math.round(gene.evidence_score * 10) / 10
        }}</span>
        <Chip v-if="gene.evidence_tier" :tier="gene.evidence_tier" />
        <span>· not changed by these curations ·</span>
      </template>
      <RouterLink to="/about#scoring" :class="LINK">How the score works</RouterLink>
      <span aria-hidden="true">·</span>
      <RouterLink to="/about#curation" :class="LINK">How expert classifications work</RouterLink>
    </p>

    <DataState
      :loading="loading"
      :error="error"
      error-title="Could not load the associations"
      :empty="!records.length"
      :empty-message="`No published expert-reviewed associations for ${symbol}.`"
      min-height="16rem"
      @retry="load"
    >
      <GeneCuratedAssociations :records="records" standalone />
    </DataState>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { curationApi, type Association } from '@/api/curation'
import { geneApi } from '@/api/genes'
import GeneCuratedAssociations from '@/components/gene/GeneCuratedAssociations.vue'
import { Chip, DataState, PageHeader, PAGE_CONTAINER } from '@/components/shared'
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator
} from '@/components/ui/breadcrumb'
import { Button } from '@/components/ui/button'
import { useSeoMeta } from '@/composables/useSeoMeta'
import { getPublicBreadcrumbsWithParents } from '@/utils/publicBreadcrumbs'

const props = defineProps<{ symbol: string }>()

const LINK = 'text-primary underline-offset-4 hover:underline'
const records = ref<Association[]>([])
// For the score line only; a failed gene lookup just hides it
const gene = ref<{ evidence_score?: number | null; evidence_tier?: string | null } | null>(null)
const loading = ref(true)
const error = ref<Error | null>(null)

const breadcrumbs = computed(() =>
  getPublicBreadcrumbsWithParents([
    { title: 'Curated Associations', to: '/curation/associations' },
    { title: props.symbol, to: `/curation/associations/${props.symbol}` }
  ])
)

useSeoMeta({
  title: computed(() => `${props.symbol} expert-reviewed gene–disease associations`),
  description: computed(
    () =>
      `Expert-reviewed kidney gene–disease associations for ${props.symbol}: classification, inheritance, points, provenance and diagnostics.`
  ),
  canonicalPath: computed(() => `/curation/associations/${props.symbol}`)
})

const load = async () => {
  loading.value = true
  error.value = null
  try {
    const [list, g] = await Promise.all([
      curationApi.listPublished({ gene_symbol: props.symbol }),
      geneApi.getGene(props.symbol).catch(() => null)
    ])
    records.value = list.data
    gene.value = g
  } catch (e) {
    error.value = e instanceof Error ? e : new Error(String(e))
  } finally {
    loading.value = false
  }
}

watch(() => props.symbol, load, { immediate: true })
</script>
