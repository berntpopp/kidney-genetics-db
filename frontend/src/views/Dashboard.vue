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

    <!-- Global Filters -->
    <div class="mb-4">
      <Popover>
        <PopoverTrigger as-child>
          <Button variant="outline" class="justify-between">
            {{ selectedTiers.length ? `${selectedTiers.length} tiers selected` : 'All tiers' }}
            <ChevronDown :size="16" class="ml-2" />
          </Button>
        </PopoverTrigger>
        <PopoverContent class="w-72">
          <div class="space-y-1">
            <div
              v-for="tier in tierOptions"
              :key="tier.value"
              class="flex items-center gap-2 rounded-md px-2 py-1.5 cursor-pointer hover:bg-accent"
              @click="toggleTier(tier.value)"
            >
              <div
                class="h-4 w-4 rounded border flex items-center justify-center"
                :class="
                  selectedTiers.includes(tier.value) ? 'bg-primary border-primary' : 'border-input'
                "
              >
                <CheckIcon
                  v-if="selectedTiers.includes(tier.value)"
                  :size="12"
                  class="text-primary-foreground"
                />
              </div>
              <Badge
                variant="secondary"
                :style="{ backgroundColor: tier.color + '20', color: tier.color }"
              >
                {{ tier.title }}
              </Badge>
            </div>
          </div>
          <div v-if="selectedTiers.length" class="mt-2 pt-2 border-t">
            <Button variant="ghost" size="sm" class="w-full text-xs" @click="selectedTiers = []">
              Clear all
            </Button>
          </div>
        </PopoverContent>
      </Popover>
      <p class="text-xs text-muted-foreground mt-1">
        Select one or more evidence tiers to filter visualizations (multi-select with OR logic)
      </p>
    </div>

    <!-- Visualization Tabs -->
    <Card>
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
            <UpSetChart :selected-tiers="selectedTiers" />
          </TabsContent>
          <TabsContent value="distributions">
            <SourceDistributionsChart
              v-if="activeTab === 'distributions'"
              :selected-tiers="selectedTiers"
            />
          </TabsContent>
          <TabsContent value="composition">
            <EvidenceCompositionChart
              v-if="activeTab === 'composition'"
              :selected-tiers="selectedTiers"
            />
          </TabsContent>
        </CardContent>
      </Tabs>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { RouterLink } from 'vue-router'
import {
  ChevronRight,
  LayoutDashboard,
  ChartScatter,
  ChartBar,
  Circle,
  ChevronDown,
  Check as CheckIcon
} from 'lucide-vue-next'
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
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'

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
