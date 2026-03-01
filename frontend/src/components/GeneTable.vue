<script setup lang="ts">
import { ref, computed, onMounted, watch, h } from 'vue'
import type { ColumnDef, SortingState, PaginationState } from '@tanstack/vue-table'
import { useVueTable, getCoreRowModel } from '@tanstack/vue-table'
import { Info, EyeOff, Search, Download, FilterX, RefreshCw } from 'lucide-vue-next'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { geneApi } from '../api/genes'
import ScoreBreakdown from './ScoreBreakdown.vue'
import EvidenceTierBadge from './EvidenceTierBadge.vue'
import { TIER_CONFIG } from '@/utils/evidenceTiers'
import { DataTable, DataTableColumnHeader, DataTablePagination } from '@/components/ui/data-table'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Label } from '@/components/ui/label'
import { Slider } from '@/components/ui/slider'
import { Switch } from '@/components/ui/switch'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@/components/ui/select'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { Checkbox } from '@/components/ui/checkbox'
import { Separator } from '@/components/ui/separator'
import { Progress } from '@/components/ui/progress'

// Route
const route = useRoute()
const router = useRouter()

// Data
const genes = ref<any[]>([])
const loading = ref(false)
const totalItems = ref(0)
const page = ref(1)
const itemsPerPage = ref(10)
const search = ref('')
const evidenceScoreRange = ref([0, 100])
const selectedSources = ref<string[]>([])
const selectedTiers = ref<string[]>([])
const evidenceCountRange = ref([0, 7])
const sortOption = ref('score_desc')
const filterMeta = ref<any>(null)
const sortBy = ref([{ key: 'evidence_score', order: 'desc' }])
const showZeroScoreGenes = ref(false)

// Track initialization to prevent circular updates
const isInitializing = ref(true)
const isNavigating = ref(false)

// Options
const itemsPerPageOptions = [10, 20, 50, 100]

// Dynamic sources list
const availableSources = ref<{ title: string; value: string }[]>([])

// Available evidence tiers from config
const availableTiers = computed(() => {
  return Object.entries(TIER_CONFIG).map(([key, config]) => ({
    title: config.label,
    value: key,
    color: config.color
  }))
})

const sortOptions = [
  { title: 'Score (High → Low)', value: 'score_desc' },
  { title: 'Score (Low → High)', value: 'score_asc' },
  { title: 'Tier (Best → Weakest)', value: 'tier_asc' },
  { title: 'Tier (Weakest → Best)', value: 'tier_desc' },
  { title: 'Symbol (A → Z)', value: 'symbol_asc' },
  { title: 'Symbol (Z → A)', value: 'symbol_desc' },
  { title: 'Count (High → Low)', value: 'count_desc' },
  { title: 'Count (Low → High)', value: 'count_asc' }
]

// Column definitions
const columns: ColumnDef<any>[] = [
  {
    accessorKey: 'approved_symbol',
    header: ({ column }) => h(DataTableColumnHeader, { column, title: 'Gene' }),
    cell: ({ row }) => {
      const symbol = row.getValue('approved_symbol') as string
      const aliases = row.original.aliases as string[] | undefined
      return h('div', { class: 'flex items-center gap-1' }, [
        h(
          RouterLink,
          {
            to: `/genes/${symbol}`,
            class: 'text-primary hover:underline font-medium font-mono text-sm'
          },
          () => symbol
        ),
        ...(aliases?.length
          ? [
              h(TooltipProvider, null, () =>
                h(Tooltip, null, {
                  default: () => [
                    h(TooltipTrigger, { asChild: true }, () =>
                      h(Info, { class: 'h-3 w-3 text-muted-foreground' })
                    ),
                    h(TooltipContent, null, () =>
                      h('div', null, [h('strong', null, 'Aliases: '), aliases.join(', ')])
                    )
                  ]
                })
              )
            ]
          : [])
      ])
    },
    size: 140
  },
  {
    accessorKey: 'hgnc_id',
    header: ({ column }) => h(DataTableColumnHeader, { column, title: 'HGNC ID' }),
    cell: ({ row }) => {
      const id = row.getValue('hgnc_id') as string | null
      return id
        ? h('code', { class: 'text-xs bg-muted px-1 py-0.5 rounded font-mono' }, id)
        : h(Badge, { variant: 'secondary', class: 'text-[10px]' }, () => 'N/A')
    },
    size: 110
  },
  {
    accessorKey: 'evidence_tier',
    header: ({ column }) => h(DataTableColumnHeader, { column, title: 'Tier' }),
    cell: ({ row }) =>
      h(EvidenceTierBadge, { tier: row.getValue('evidence_tier'), size: 'x-small' }),
    size: 100
  },
  {
    accessorKey: 'evidence_count',
    header: ({ column }) => h(DataTableColumnHeader, { column, title: 'Evidence' }),
    cell: ({ row }) => {
      const count = row.getValue('evidence_count') as number
      return h('div', { class: 'flex items-center gap-2' }, [
        h(
          Badge,
          {
            variant: 'secondary',
            class: 'font-mono text-xs'
          },
          () => count
        ),
        h(Progress, {
          modelValue: getEvidenceStrength(count),
          class: 'h-0.5 w-10'
        })
      ])
    },
    size: 100
  },
  {
    accessorKey: 'evidence_score',
    header: ({ column }) => h(DataTableColumnHeader, { column, title: 'Score' }),
    cell: ({ row }) => {
      const score = row.getValue('evidence_score')
      if (score === null || score === undefined) {
        return h(Badge, { variant: 'secondary', class: 'text-[10px]' }, () => 'N/A')
      }
      return h(ScoreBreakdown, {
        score,
        breakdown: getSourcesAsBreakdown(row.original.sources),
        variant: 'inline',
        size: 'small'
      })
    },
    size: 100
  },
  {
    accessorKey: 'sources',
    header: 'Sources',
    cell: ({ row }) => {
      const sources = (row.getValue('sources') as string[]) || []
      return h('div', { class: 'flex flex-wrap gap-1' }, [
        ...sources.slice(0, 3).map(s =>
          h(
            Badge,
            {
              key: s,
              variant: 'outline',
              class: 'text-[10px] font-medium'
            },
            () => s
          )
        ),
        ...(sources.length > 3
          ? [h('span', { class: 'text-xs text-muted-foreground' }, `+${sources.length - 3}`)]
          : [])
      ])
    },
    enableSorting: false,
    size: 200
  }
]

// Computed
const pageCount = computed(() => Math.ceil(totalItems.value / itemsPerPage.value))

const hiddenGeneCount = computed(() => {
  return filterMeta.value?.hidden_zero_scores || 0
})

const hasActiveFilters = computed(() => {
  return (
    search.value ||
    evidenceScoreRange.value[0] > 0 ||
    evidenceScoreRange.value[1] < 100 ||
    evidenceCountRange.value[0] > 0 ||
    evidenceCountRange.value[1] < (filterMeta.value?.evidence_count?.max || 6) ||
    selectedSources.value.length > 0 ||
    selectedTiers.value.length > 0 ||
    showZeroScoreGenes.value
  )
})

// TanStack Table setup (server-side)
const table = useVueTable({
  get data() {
    return genes.value
  },
  columns,
  getCoreRowModel: getCoreRowModel(),
  manualPagination: true,
  manualSorting: true,
  get pageCount() {
    return pageCount.value
  },
  state: {
    get pagination(): PaginationState {
      return { pageIndex: page.value - 1, pageSize: itemsPerPage.value }
    },
    get sorting(): SortingState {
      return sortBy.value.map(s => ({
        id: s.key,
        desc: s.order === 'desc'
      }))
    }
  },
  onPaginationChange: updater => {
    if (isInitializing.value || isNavigating.value) return
    const current = { pageIndex: page.value - 1, pageSize: itemsPerPage.value }
    const newState = typeof updater === 'function' ? updater(current) : updater
    page.value = newState.pageIndex + 1
    itemsPerPage.value = newState.pageSize
    updateUrl()
    loadGenes()
  },
  onSortingChange: updater => {
    if (isInitializing.value || isNavigating.value) return
    const current = sortBy.value.map(s => ({ id: s.key, desc: s.order === 'desc' }))
    const newState = typeof updater === 'function' ? updater(current) : updater
    sortBy.value = newState.map(s => ({ key: s.id, order: s.desc ? 'desc' : 'asc' }))
    updateUrl()
    loadGenes()
  }
})

// Parse URL parameters and apply to component state
const parseUrlParams = () => {
  const query = route.query

  if (query.page) {
    const parsedPage = parseInt(query.page as string)
    if (!isNaN(parsedPage) && parsedPage > 0) {
      page.value = parsedPage
    }
  }

  if (query.per_page) {
    const parsedPerPage = parseInt(query.per_page as string)
    if (!isNaN(parsedPerPage) && itemsPerPageOptions.includes(parsedPerPage)) {
      itemsPerPage.value = parsedPerPage
    }
  }

  if (query.search) {
    search.value = query.search as string
  }

  if (query.sort_by && query.sort_order) {
    sortBy.value = [{ key: query.sort_by as string, order: query.sort_order as string }]
    const sortMap: Record<string, string> = {
      evidence_score_desc: 'score_desc',
      evidence_score_asc: 'score_asc',
      evidence_tier_asc: 'tier_asc',
      evidence_tier_desc: 'tier_desc',
      approved_symbol_asc: 'symbol_asc',
      approved_symbol_desc: 'symbol_desc',
      evidence_count_desc: 'count_desc',
      evidence_count_asc: 'count_asc'
    }
    sortOption.value = sortMap[`${query.sort_by}_${query.sort_order}`] || 'score_desc'
  }

  if (query.min_score) {
    evidenceScoreRange.value[0] = parseInt(query.min_score as string) || 0
  }
  if (query.max_score) {
    evidenceScoreRange.value[1] = parseInt(query.max_score as string) || 100
  }

  if (query.min_count) {
    evidenceCountRange.value[0] = parseInt(query.min_count as string) || 0
  }
  if (query.max_count) {
    evidenceCountRange.value[1] = parseInt(query.max_count as string) || 7
  }

  if (query.source) {
    selectedSources.value = [query.source as string]
  }

  if (query.tier) {
    selectedTiers.value = (query.tier as string)
      .split(',')
      .map(t => t.trim())
      .filter(t => t)
  }

  if (query.show_zero_scores !== undefined) {
    showZeroScoreGenes.value = query.show_zero_scores === 'true'
  }
}

// Update URL with current state
const updateUrl = () => {
  if (isInitializing.value) return

  const query: Record<string, any> = {}

  if (page.value !== 1) query.page = page.value
  if (itemsPerPage.value !== 10) query.per_page = itemsPerPage.value
  if (search.value) query.search = search.value

  if (sortBy.value.length > 0) {
    query.sort_by = sortBy.value[0].key
    query.sort_order = sortBy.value[0].order
  }

  if (evidenceScoreRange.value[0] > 0) query.min_score = evidenceScoreRange.value[0]
  if (evidenceScoreRange.value[1] < 100) query.max_score = evidenceScoreRange.value[1]
  if (evidenceCountRange.value[0] > 0) query.min_count = evidenceCountRange.value[0]
  if (evidenceCountRange.value[1] < 7) query.max_count = evidenceCountRange.value[1]
  if (selectedSources.value.length > 0) query.source = selectedSources.value[0]
  if (selectedTiers.value.length > 0) query.tier = selectedTiers.value.join(',')
  if (showZeroScoreGenes.value) query.show_zero_scores = 'true'

  router.replace({ query })
}

// Methods
const loadGenes = async () => {
  if (loading.value) return

  loading.value = true
  try {
    const sortByField = sortBy.value?.[0]?.key || 'evidence_score'
    const sortDesc = sortBy.value?.[0]?.order === 'desc'
    const response = await geneApi.getGenes({
      page: page.value,
      perPage: itemsPerPage.value,
      search: search.value,
      minScore: evidenceScoreRange.value[0],
      maxScore: evidenceScoreRange.value[1],
      minCount: evidenceCountRange.value[0],
      maxCount:
        evidenceCountRange.value[1] < (filterMeta.value?.evidence_count?.max || 7)
          ? evidenceCountRange.value[1]
          : null,
      source: selectedSources.value.length > 0 ? selectedSources.value[0] : null,
      tiers: selectedTiers.value.length > 0 ? selectedTiers.value : null,
      sortBy: sortByField,
      sortDesc,
      hideZeroScores: !showZeroScoreGenes.value
    })

    genes.value = response.items
    totalItems.value = response.total

    if (response.meta && response.meta.filters) {
      filterMeta.value = response.meta.filters

      if (response.meta.filters.available_sources) {
        availableSources.value = response.meta.filters.available_sources.map((source: string) => ({
          title: source,
          value: source
        }))
      }

      if (response.meta.filters.evidence_count?.max && !filterMeta.value) {
        evidenceCountRange.value = [0, response.meta.filters.evidence_count.max]
      }
    }
  } catch (error) {
    window.logService.error('Error loading genes:', error)
    genes.value = []
    totalItems.value = 0
  } finally {
    loading.value = false
  }
}

// Event handlers
const applySorting = (value: string) => {
  sortOption.value = value
  const [field, order] = value.split('_')
  const fieldMap: Record<string, string> = {
    score: 'evidence_score',
    symbol: 'approved_symbol',
    count: 'evidence_count',
    tier: 'evidence_tier'
  }
  sortBy.value = [{ key: fieldMap[field], order }]
  updateUrl()
  loadGenes()
}

let searchTimeout: ReturnType<typeof setTimeout>
const debouncedSearch = () => {
  clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    page.value = 1
    updateUrl()
    loadGenes()
  }, 300)
}

const clearAllFilters = () => {
  search.value = ''
  evidenceScoreRange.value = [0, 100]
  evidenceCountRange.value = [0, filterMeta.value?.evidence_count?.max || 7]
  selectedSources.value = []
  selectedTiers.value = []
  sortOption.value = 'score_desc'
  sortBy.value = [{ key: 'evidence_score', order: 'desc' }]
  showZeroScoreGenes.value = false
  page.value = 1
  updateUrl()
  loadGenes()
}

const refreshData = () => {
  loadGenes()
}

const exportData = () => {
  window.logService.info('Export functionality to be implemented')
}

const clearSources = () => {
  selectedSources.value = []
  page.value = 1
  updateUrl()
  loadGenes()
}

const clearTiers = () => {
  selectedTiers.value = []
  page.value = 1
  updateUrl()
  loadGenes()
}

// Source toggle helper
const toggleSource = (source: string) => {
  const idx = selectedSources.value.indexOf(source)
  if (idx >= 0) {
    selectedSources.value = selectedSources.value.filter(s => s !== source)
  } else {
    selectedSources.value = [...selectedSources.value, source]
  }
  page.value = 1
  updateUrl()
  loadGenes()
}

const toggleTier = (tier: string) => {
  const idx = selectedTiers.value.indexOf(tier)
  if (idx >= 0) {
    selectedTiers.value = selectedTiers.value.filter(t => t !== tier)
  } else {
    selectedTiers.value = [...selectedTiers.value, tier]
  }
  page.value = 1
  updateUrl()
  loadGenes()
}

// Helper methods
const getSourcesAsBreakdown = (sources: string[]) => {
  if (!sources || sources.length === 0) return {}
  const breakdown: Record<string, boolean> = {}
  sources.forEach(source => {
    breakdown[source] = true
  })
  return breakdown
}

const getEvidenceStrength = (count: number) => {
  const max = filterMeta.value?.evidence_count?.max || 6
  return max > 0 ? Math.min((count / max) * 100, 100) : 0
}

// Watch for route changes
watch(
  () => route.query,
  (newQuery, oldQuery) => {
    if (!isInitializing.value && JSON.stringify(newQuery) !== JSON.stringify(oldQuery)) {
      isNavigating.value = true
      parseUrlParams()
      loadGenes().then(() => {
        setTimeout(() => {
          isNavigating.value = false
        }, 100)
      })
    }
  },
  { deep: true }
)

// Lifecycle
onMounted(async () => {
  isInitializing.value = true
  parseUrlParams()
  await loadGenes()
  await new Promise(resolve => setTimeout(resolve, 100))
  isInitializing.value = false
})
</script>

<template>
  <div class="space-y-3">
    <!-- Search & Filter Bar -->
    <Card>
      <CardContent class="py-3 px-4">
        <!-- Row 1: Search + Sort + Action buttons -->
        <div class="flex flex-col sm:flex-row gap-2">
          <div class="relative flex-1">
            <Search
              :size="16"
              class="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
            />
            <Input
              v-model="search"
              placeholder="PKD1, HGNC:9008..."
              class="pl-9 h-9"
              @input="debouncedSearch"
            />
          </div>
          <div class="flex gap-2">
            <Select :model-value="sortOption" @update:model-value="applySorting">
              <SelectTrigger class="w-[180px] h-9">
                <SelectValue placeholder="Sort by..." />
              </SelectTrigger>
              <SelectContent>
                <SelectItem v-for="opt in sortOptions" :key="opt.value" :value="opt.value">
                  {{ opt.title }}
                </SelectItem>
              </SelectContent>
            </Select>

            <!-- Source Filter -->
            <Popover>
              <PopoverTrigger as-child>
                <Button variant="outline" size="sm" class="h-9">
                  Sources
                  <Badge
                    v-if="selectedSources.length"
                    variant="secondary"
                    class="ml-1 rounded-sm px-1 text-xs"
                  >
                    {{ selectedSources.length }}
                  </Badge>
                </Button>
              </PopoverTrigger>
              <PopoverContent class="w-[200px] p-3" align="start">
                <div class="space-y-2">
                  <p class="text-sm font-medium">Filter by source</p>
                  <Separator />
                  <div
                    v-for="source in availableSources"
                    :key="source.value"
                    class="flex items-center gap-2"
                  >
                    <Checkbox
                      :id="`source-${source.value}`"
                      :checked="selectedSources.includes(source.value)"
                      @update:checked="toggleSource(source.value)"
                    />
                    <Label :for="`source-${source.value}`" class="text-sm cursor-pointer">
                      {{ source.title }}
                    </Label>
                  </div>
                  <Button
                    v-if="selectedSources.length > 0"
                    variant="ghost"
                    size="sm"
                    class="w-full"
                    @click="clearSources"
                  >
                    Clear
                  </Button>
                </div>
              </PopoverContent>
            </Popover>

            <!-- Tier Filter -->
            <Popover>
              <PopoverTrigger as-child>
                <Button variant="outline" size="sm" class="h-9">
                  Tiers
                  <Badge
                    v-if="selectedTiers.length"
                    variant="secondary"
                    class="ml-1 rounded-sm px-1 text-xs"
                  >
                    {{ selectedTiers.length }}
                  </Badge>
                </Button>
              </PopoverTrigger>
              <PopoverContent class="w-[250px] p-3" align="start">
                <div class="space-y-2">
                  <p class="text-sm font-medium">Filter by tier</p>
                  <Separator />
                  <div
                    v-for="tier in availableTiers"
                    :key="tier.value"
                    class="flex items-center gap-2"
                  >
                    <Checkbox
                      :id="`tier-${tier.value}`"
                      :checked="selectedTiers.includes(tier.value)"
                      @update:checked="toggleTier(tier.value)"
                    />
                    <Label :for="`tier-${tier.value}`" class="text-sm cursor-pointer">
                      <span
                        class="inline-block w-2 h-2 rounded-full mr-1"
                        :style="{ backgroundColor: tier.color }"
                      />
                      {{ tier.title }}
                    </Label>
                  </div>
                  <Button
                    v-if="selectedTiers.length > 0"
                    variant="ghost"
                    size="sm"
                    class="w-full"
                    @click="clearTiers"
                  >
                    Clear
                  </Button>
                </div>
              </PopoverContent>
            </Popover>

            <Button
              variant="outline"
              size="icon-sm"
              class="h-9 w-9"
              :disabled="loading"
              @click="exportData"
            >
              <Download class="h-4 w-4" />
            </Button>
            <Button
              variant="outline"
              size="icon-sm"
              class="h-9 w-9"
              :disabled="!hasActiveFilters"
              @click="clearAllFilters"
            >
              <FilterX class="h-4 w-4" />
            </Button>
            <Button variant="outline" size="icon-sm" class="h-9 w-9" @click="refreshData">
              <RefreshCw class="h-4 w-4" :class="{ 'animate-spin': loading }" />
            </Button>
          </div>
        </div>

        <!-- Row 2: Sliders + Zero-score toggle (compact) -->
        <div class="flex flex-col md:flex-row items-start md:items-center gap-x-6 gap-y-2 mt-2">
          <div class="flex items-center gap-2 min-w-[200px] flex-1">
            <Label class="text-xs whitespace-nowrap">Score</Label>
            <Slider
              v-model="evidenceScoreRange"
              :min="0"
              :max="100"
              :step="1"
              class="flex-1"
              @update:model-value="debouncedSearch"
            />
            <span class="text-xs text-muted-foreground font-mono whitespace-nowrap">
              {{ evidenceScoreRange[0] }}–{{ evidenceScoreRange[1] }}
            </span>
          </div>

          <div class="flex items-center gap-2 min-w-[180px] flex-1">
            <Label class="text-xs whitespace-nowrap">Count</Label>
            <Slider
              v-model="evidenceCountRange"
              :min="0"
              :max="filterMeta?.evidence_count?.max || 6"
              :step="1"
              class="flex-1"
              @update:model-value="debouncedSearch"
            />
            <span class="text-xs text-muted-foreground font-mono whitespace-nowrap">
              {{ evidenceCountRange[0] }}–{{ evidenceCountRange[1] }}
            </span>
          </div>

          <div class="flex items-center gap-2">
            <Switch
              id="zero-score"
              :checked="showZeroScoreGenes"
              @update:checked="
                val => {
                  showZeroScoreGenes = val
                  debouncedSearch()
                }
              "
            />
            <Label for="zero-score" class="text-xs cursor-pointer whitespace-nowrap">
              Include zero-score
            </Label>
            <Badge
              v-if="!showZeroScoreGenes && hiddenGeneCount > 0"
              variant="outline"
              class="text-xs"
            >
              <EyeOff class="h-3 w-3 mr-1" />
              {{ hiddenGeneCount.toLocaleString() }}
            </Badge>
          </div>

          <!-- Total gene count -->
          <Badge variant="secondary" class="text-xs font-normal ml-auto">
            {{ genes.length }}/{{ totalItems.toLocaleString() }} genes
          </Badge>
        </div>
      </CardContent>
    </Card>

    <!-- Data Table -->
    <Card v-if="genes.length > 0 || loading">
      <DataTablePagination :table="table" :page-size-options="itemsPerPageOptions" />
      <DataTable :table="table" />
    </Card>

    <!-- Empty State -->
    <Card v-if="!loading && genes.length === 0" class="text-center">
      <CardContent class="py-12">
        <Search class="h-8 w-8 mx-auto mb-4 text-muted-foreground" />
        <h3 class="text-lg font-medium mb-2">No genes found</h3>
        <p class="text-sm text-muted-foreground mb-4">
          {{ search ? `No results for "${search}"` : 'Try adjusting your filters' }}
        </p>
        <Button v-if="hasActiveFilters" variant="outline" @click="clearAllFilters">
          Clear Filters
        </Button>
      </CardContent>
    </Card>
  </div>
</template>
