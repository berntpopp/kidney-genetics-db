<template>
  <div :class="PAGE_CONTAINER">
    <PageHeader
      title="Data Visualization Dashboard"
      description="How the kidney-disease gene evidence is spread across sources, tiers and classifications."
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

    <!-- Global filters: they apply to every chart -->
    <TooltipProvider>
      <div class="mb-4 flex flex-wrap items-center gap-2" role="group" aria-label="Chart filters">
        <span class="text-sm font-medium text-muted-foreground">Tiers:</span>
        <Chip
          v-for="tier in tierOptions"
          :key="tier.value"
          :tier="tier.value"
          :aria-pressed="selectedTiers.includes(tier.value)"
          class="min-h-6"
          :class="
            selectedTiers.includes(tier.value)
              ? 'ring-2 ring-foreground/70 ring-offset-1 ring-offset-background'
              : ''
          "
          @click="toggleTier(tier.value)"
        >
          {{ tier.title }}
          <Check v-if="selectedTiers.includes(tier.value)" aria-hidden="true" />
        </Chip>
        <Button
          v-if="selectedTiers.length > 0"
          variant="ghost"
          size="sm"
          class="h-7 px-2 text-xs"
          @click="selectedTiers = []"
        >
          Clear
        </Button>
        <div class="flex w-full items-center gap-2 sm:ml-auto sm:w-auto">
          <Label
            for="show-insufficient-global"
            class="min-h-6 cursor-pointer text-sm whitespace-nowrap text-muted-foreground"
          >
            Include zero-score genes
          </Label>
          <Switch id="show-insufficient-global" v-model="showInsufficientEvidence" />
        </div>
      </div>
    </TooltipProvider>

    <Tabs v-model="activeTab" class="w-full">
      <TabsList class="mb-4 grid h-auto w-full grid-cols-3">
        <TabsTrigger value="overlaps" class="min-h-8">
          <ChartScatter class="hidden sm:block" aria-hidden="true" />
          Overlaps
        </TabsTrigger>
        <TabsTrigger value="distributions" class="min-h-8">
          <ChartBar class="hidden sm:block" aria-hidden="true" />
          Distributions
        </TabsTrigger>
        <TabsTrigger value="composition" class="min-h-8">
          <Circle class="hidden sm:block" aria-hidden="true" />
          Composition
        </TabsTrigger>
      </TabsList>
      <TabsContent value="overlaps">
        <ErrorBoundary fallback-message="Chart failed to render.">
          <UpSetChart
            :selected-tiers="selectedTiers"
            :show-insufficient-evidence="showInsufficientEvidence"
          />
        </ErrorBoundary>
      </TabsContent>
      <TabsContent value="distributions">
        <ErrorBoundary fallback-message="Chart failed to render.">
          <SourceDistributionsChart
            v-if="activeTab === 'distributions'"
            :selected-tiers="selectedTiers"
            :show-insufficient-evidence="showInsufficientEvidence"
          />
        </ErrorBoundary>
      </TabsContent>
      <TabsContent value="composition">
        <ErrorBoundary fallback-message="Chart failed to render.">
          <EvidenceCompositionChart
            v-if="activeTab === 'composition'"
            :selected-tiers="selectedTiers"
            :show-insufficient-evidence="showInsufficientEvidence"
          />
        </ErrorBoundary>
      </TabsContent>
    </Tabs>
  </div>
</template>

<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { ChartScatter, ChartBar, Check, Circle } from 'lucide-vue-next'
import ErrorBoundary from '@/components/ui/error-boundary/ErrorBoundary.vue'
import { ref, watch, onMounted, computed, defineAsyncComponent } from 'vue'
import ComponentSkeleton from '@/components/ui/ComponentSkeleton.vue'
import ComponentError from '@/components/ui/ComponentError.vue'
import { useRoute, useRouter } from 'vue-router'
const UpSetChart = defineAsyncComponent({
  loader: () => import('@/components/visualizations/UpSetChart.vue'),
  loadingComponent: ComponentSkeleton,
  errorComponent: ComponentError,
  delay: 200,
  timeout: 10000
})

const SourceDistributionsChart = defineAsyncComponent({
  loader: () => import('@/components/visualizations/SourceDistributionsChart.vue'),
  loadingComponent: ComponentSkeleton,
  errorComponent: ComponentError,
  delay: 200,
  timeout: 10000
})

const EvidenceCompositionChart = defineAsyncComponent({
  loader: () => import('@/components/visualizations/EvidenceCompositionChart.vue'),
  loadingComponent: ComponentSkeleton,
  errorComponent: ComponentError,
  delay: 200,
  timeout: 10000
})
import { TIER_CONFIG } from '@/utils/evidenceTiers'
import { Chip, PageHeader, PAGE_CONTAINER } from '@/components/shared'
import { PUBLIC_BREADCRUMBS } from '@/utils/publicBreadcrumbs'
import { useSeoMeta } from '@/composables/useSeoMeta'
import { useJsonLd, getBreadcrumbSchema } from '@/composables/useJsonLd'
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator
} from '@/components/ui/breadcrumb'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'
import { TooltipProvider } from '@/components/ui/tooltip'

defineOptions({
  name: 'Dashboard'
})

const route = useRoute()
const router = useRouter()

const breadcrumbs = PUBLIC_BREADCRUMBS.dashboard

useJsonLd(getBreadcrumbSchema(breadcrumbs))

useSeoMeta({
  title: 'Data Overview — Gene Evidence Dashboard',
  description:
    'Visualization dashboard for kidney disease gene-disease associations. Source overlap analysis, evidence distribution, and composition across ClinGen, PanelApp, GenCC, and more.',
  canonicalPath: '/dashboard'
})

const activeTab = ref('overlaps')
const selectedTiers = ref<string[]>([])
const showInsufficientEvidence = ref(false)

const validTabs = ['overlaps', 'distributions', 'composition']

const tierOptions = computed(() => {
  return Object.entries(TIER_CONFIG).map(([key, config]) => ({
    title: config.label,
    value: key,
    color: config.color,
    description: config.description
  }))
})

const toggleTier = (value: string) => {
  const index = selectedTiers.value.indexOf(value)
  if (index === -1) {
    selectedTiers.value = [...selectedTiers.value, value]
  } else {
    selectedTiers.value = selectedTiers.value.filter(t => t !== value)
  }
}

onMounted(() => {
  const urlTab = route.query.tab as string
  if (urlTab && validTabs.includes(urlTab)) {
    activeTab.value = urlTab
  }
})

watch(activeTab, newTab => {
  if (route.query.tab !== newTab) {
    router.push({
      path: route.path,
      query: { ...route.query, tab: newTab }
    })
  }
})

watch(
  () => route.query.tab,
  newTab => {
    if (newTab && validTabs.includes(newTab as string) && activeTab.value !== newTab) {
      activeTab.value = newTab as string
    }
  }
)
</script>
