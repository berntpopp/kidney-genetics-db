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

    <!-- Header -->
    <div class="flex items-center gap-3 mb-6">
      <LayoutDashboard class="size-6 text-primary" />
      <div>
        <h1 class="text-2xl font-bold">Data Visualization Dashboard</h1>
        <p class="text-sm text-muted-foreground">
          Comprehensive analysis of gene-disease associations across multiple genomic data sources
        </p>
      </div>
    </div>

    <!-- Visualization Tabs -->
    <Card>
      <!-- Global Filters -->
      <div class="flex flex-wrap items-center gap-2 px-6 pt-6 pb-2">
        <span class="text-sm font-medium text-muted-foreground">Tiers:</span>
        <Badge
          v-for="tier in tierOptions"
          :key="tier.value"
          class="cursor-pointer select-none transition-opacity"
          :class="
            selectedTiers.length === 0 || selectedTiers.includes(tier.value)
              ? 'opacity-100'
              : 'opacity-30'
          "
          :style="{
            backgroundColor: tier.color + '20',
            color: tier.color,
            borderColor: selectedTiers.includes(tier.value) ? tier.color : 'transparent'
          }"
          @click="toggleTier(tier.value)"
        >
          {{ tier.title }}
        </Badge>
        <Button
          v-if="selectedTiers.length > 0"
          variant="ghost"
          size="sm"
          class="text-xs h-6 px-2"
          @click="selectedTiers = []"
        >
          Clear
        </Button>
        <div class="ml-auto flex items-center gap-2">
          <Label
            for="show-insufficient-global"
            class="text-sm text-muted-foreground cursor-pointer"
          >
            Include zero-score genes
          </Label>
          <Switch id="show-insufficient-global" v-model="showInsufficientEvidence" />
        </div>
      </div>
      <Tabs v-model="activeTab" class="w-full">
        <CardHeader class="pb-0">
          <TabsList>
            <TabsTrigger value="overlaps">
              <ChartScatter :size="16" class="mr-2" />
              Gene Source Overlaps
            </TabsTrigger>
            <TabsTrigger value="distributions">
              <ChartBar :size="16" class="mr-2" />
              Source Distributions
            </TabsTrigger>
            <TabsTrigger value="composition">
              <Circle :size="16" class="mr-2" />
              Evidence Composition
            </TabsTrigger>
          </TabsList>
        </CardHeader>
        <CardContent>
          <TabsContent value="overlaps">
            <UpSetChart
              :selected-tiers="selectedTiers"
              :show-insufficient-evidence="showInsufficientEvidence"
            />
          </TabsContent>
          <TabsContent value="distributions">
            <SourceDistributionsChart
              v-if="activeTab === 'distributions'"
              :selected-tiers="selectedTiers"
              :show-insufficient-evidence="showInsufficientEvidence"
            />
          </TabsContent>
          <TabsContent value="composition">
            <EvidenceCompositionChart
              v-if="activeTab === 'composition'"
              :selected-tiers="selectedTiers"
              :show-insufficient-evidence="showInsufficientEvidence"
            />
          </TabsContent>
        </CardContent>
      </Tabs>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { LayoutDashboard, ChartScatter, ChartBar, Circle } from 'lucide-vue-next'
import { ref, watch, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  UpSetChart,
  SourceDistributionsChart,
  EvidenceCompositionChart
} from '@/components/visualizations'
import { TIER_CONFIG } from '@/utils/evidenceTiers'
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
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'

defineOptions({
  name: 'Dashboard'
})

const route = useRoute()
const router = useRouter()

const breadcrumbs = PUBLIC_BREADCRUMBS.dashboard

useJsonLd(getBreadcrumbSchema(breadcrumbs))

useSeoMeta({
  title: 'Dashboard',
  description:
    'Comprehensive analysis of kidney disease gene-disease associations across multiple genomic data sources.',
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
