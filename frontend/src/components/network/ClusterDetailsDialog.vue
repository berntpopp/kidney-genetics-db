<template>
  <Dialog :open="modelValue" @update:open="$emit('update:modelValue', $event)">
    <!-- Focus the dialog itself, not the first gene: that gene's tooltip would open on focus
         and take the first Escape -->
    <DialogContent class="sm:max-w-4xl max-h-[90vh] overflow-y-auto" @open-auto-focus="focusDialog">
      <!-- Header -->
      <DialogHeader>
        <div class="flex items-center gap-3">
          <Badge
            variant="outline"
            :style="tintedChipStyle(clusterColor)"
            class="flex items-center gap-1"
          >
            <Atom class="size-4" aria-hidden="true" />
            {{ clusterDisplayName || `Cluster ${clusterId + 1}` }}
          </Badge>
          <div>
            <DialogTitle class="text-lg font-medium">
              <template v-if="clusterLabel">
                {{ clusterDisplayName || `Cluster ${clusterId + 1}` }} &middot;
                <span>{{ clusterLabel }}</span>
              </template>
              <template v-else>Cluster Details</template>
            </DialogTitle>
            <DialogDescription class="text-xs mt-1">
              {{ geneCount }} gene{{ geneCount !== 1 ? 's' : '' }} in cluster<template
                v-if="clusterLabel"
              >
                &middot; {{ LABEL_NOTE }}</template
              >
            </DialogDescription>
          </div>
        </div>
      </DialogHeader>

      <Separator />

      <!-- HPO Classification Statistics -->
      <div v-if="clusterStatistics" class="p-4 bg-muted/50 rounded-md">
        <div class="flex items-center mb-3">
          <ChartBarBig class="size-5 mr-2 text-primary" />
          <h3 class="text-sm font-medium">HPO Classification Summary</h3>
          <Badge variant="secondary" class="ml-auto flex items-center gap-1">
            <Database class="size-3" />
            {{ clusterStatistics.hpoDataCount }} / {{ clusterStatistics.total }} genes ({{
              clusterStatistics.hpoDataPercentage
            }}%)
          </Badge>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <!-- Clinical Classification -->
          <div v-if="clusterStatistics.clinical.length > 0" class="stats-section">
            <div class="text-xs font-medium text-muted-foreground mb-2">
              Clinical Classification
            </div>
            <div class="flex flex-wrap gap-1">
              <Badge
                v-for="stat in clusterStatistics.clinical"
                :key="stat.key"
                variant="outline"
                :style="tintedChipStyle(stat.color)"
              >
                {{ stat.label }}: {{ stat.percentage }}%
              </Badge>
            </div>
          </div>

          <!-- Age of Onset -->
          <div v-if="clusterStatistics.onset.length > 0" class="stats-section">
            <div class="text-xs font-medium text-muted-foreground mb-2">Age of Onset</div>
            <div class="flex flex-wrap gap-1">
              <Badge
                v-for="stat in clusterStatistics.onset"
                :key="stat.key"
                variant="outline"
                :style="tintedChipStyle(stat.color)"
              >
                {{ stat.label }}: {{ stat.percentage }}%
              </Badge>
            </div>
          </div>

          <!-- Syndromic Assessment: percentages of assessed genes; unassessed shown separately -->
          <div class="stats-section">
            <div class="text-xs font-medium text-muted-foreground mb-2">
              Syndromic Assessment ({{ clusterStatistics.syndromic.assessedCount }} assessed)
            </div>
            <div class="flex flex-wrap gap-1">
              <template v-if="clusterStatistics.syndromic.assessedCount > 0">
                <Badge
                  variant="outline"
                  :style="
                    tintedChipStyle(networkAnalysisConfig.nodeColoring.colorSchemes.syndromic.true)
                  "
                >
                  Syndromic: {{ clusterStatistics.syndromic.syndromicPercentage }}%
                </Badge>
                <Badge
                  variant="outline"
                  :style="
                    tintedChipStyle(networkAnalysisConfig.nodeColoring.colorSchemes.syndromic.false)
                  "
                >
                  Isolated: {{ clusterStatistics.syndromic.isolatedPercentage }}%
                </Badge>
              </template>
              <Badge
                v-if="clusterStatistics.syndromic.unknownCount > 0"
                variant="outline"
                :style="
                  tintedChipStyle(networkAnalysisConfig.nodeColoring.colorSchemes.syndromic.null)
                "
              >
                {{ networkAnalysisConfig.nodeColoring.labels.syndromic.null }}:
                {{ clusterStatistics.syndromic.unknownCount }}
                {{ clusterStatistics.syndromic.unknownCount === 1 ? 'gene' : 'genes' }}
              </Badge>
            </div>
          </div>
        </div>
      </div>

      <Separator v-if="clusterStatistics" />

      <!-- Gene Table -->
      <div class="rounded-md border">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b bg-muted/50">
              <th scope="col" class="p-2 text-left font-semibold whitespace-nowrap">Gene</th>
              <th
                v-if="hasDegree"
                scope="col"
                class="p-2 text-right font-semibold whitespace-nowrap"
                title="Interactions with other genes in this cluster"
              >
                Links in cluster
              </th>
              <th scope="col" class="p-2 text-right font-semibold whitespace-nowrap">
                <span class="sr-only">Actions</span>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="item in paginatedGenes"
              :key="item.gene_id"
              class="border-b last:border-0 hover:bg-muted/50"
            >
              <!-- Symbol once, with its HGNC identifier -->
              <td class="p-2 font-medium">
                <OntologyTerm v-if="item.hgnc_id" :id="item.hgnc_id" :name="item.symbol" />
                <router-link
                  v-else
                  :to="`/genes/${item.symbol}`"
                  class="rounded-sm underline-offset-4 hover:underline focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
                >
                  {{ item.symbol }}
                </router-link>
              </td>

              <td v-if="hasDegree" class="p-2 text-right tabular-nums">{{ item.degree ?? '—' }}</td>

              <!-- Actions -->
              <td class="p-2 text-right">
                <div class="flex items-center justify-end gap-1">
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger as-child>
                        <Button variant="ghost" size="icon" class="h-7 w-7" as-child>
                          <router-link
                            :aria-label="`View ${item.symbol} details`"
                            :to="`/genes/${item.symbol}`"
                          >
                            <Eye class="size-4" />
                          </router-link>
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent side="bottom">
                        <p>View gene details</p>
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>

                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger as-child>
                        <Button
                          :aria-label="`Copy ${item.symbol}`"
                          variant="ghost"
                          size="icon"
                          class="h-7 w-7"
                          @click="copyGeneSymbol(item.symbol)"
                        >
                          <Copy class="size-4" />
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent side="bottom">
                        <p>Copy gene symbol</p>
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>

                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger as-child>
                        <Button
                          :aria-label="`Highlight ${item.symbol} in network`"
                          variant="ghost"
                          size="icon"
                          class="h-7 w-7"
                          @click="$emit('highlightGene', item.gene_id)"
                        >
                          <MapPin class="size-4" />
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent side="bottom">
                        <p>Highlight in network</p>
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Pagination -->
      <template v-if="totalPages > 1">
        <Separator />
        <div class="flex items-center justify-between py-1">
          <div class="text-xs text-muted-foreground">
            {{ paginationText }}
          </div>
          <div class="flex items-center gap-2">
            <Select v-model="itemsPerPageStr">
              <SelectTrigger aria-label="Per page" class="h-8 w-[80px]">
                <SelectValue placeholder="Per page" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem v-for="opt in itemsPerPageOptions" :key="opt" :value="String(opt)">
                  {{ opt }}
                </SelectItem>
              </SelectContent>
            </Select>
            <Button
              aria-label="Previous page"
              variant="ghost"
              size="icon"
              class="h-8 w-8"
              :disabled="page === 1"
              @click="page--"
            >
              <ChevronLeft class="size-4" />
            </Button>
            <span class="text-xs">{{ page }} / {{ totalPages }}</span>
            <Button
              aria-label="Next page"
              variant="ghost"
              size="icon"
              class="h-8 w-8"
              :disabled="page === totalPages"
              @click="page++"
            >
              <ChevronRight class="size-4" />
            </Button>
          </div>
        </div>
      </template>

      <Separator />

      <!-- Footer Actions -->
      <DialogFooter class="flex items-center sm:justify-between">
        <div class="flex flex-wrap items-center gap-1">
          <Button variant="ghost" size="sm" :disabled="geneCount === 0" @click="exportClusterGenes">
            <Download class="size-4 mr-2" aria-hidden="true" />
            Export genes (CSV)
          </Button>
          <Button v-if="stringUrl" variant="ghost" size="sm" as-child>
            <a :href="stringUrl" target="_blank" rel="noopener noreferrer">
              <ExternalLink class="size-4 mr-2" aria-hidden="true" />
              Open in STRING
              <span class="sr-only">(opens in a new tab)</span>
            </a>
          </Button>
        </div>
        <div class="flex-1" />
        <Button variant="secondary" @click="$emit('update:modelValue', false)">Close</Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import {
  Atom,
  ChartBarBig,
  ChevronLeft,
  ChevronRight,
  Copy,
  Database,
  Download,
  ExternalLink,
  Eye,
  MapPin
} from 'lucide-vue-next'
import { toast } from 'vue-sonner'
import { networkAnalysisConfig, OTHER_CLUSTER_COLOR } from '../../config/networkAnalysis'
import { tintedChipStyle } from '@/utils/evidenceTiers'
import { OntologyTerm } from '@/components/shared'
import { computeHpoClusterStats } from './hpoClusterStats'
import { LABEL_MAX_FDR } from '@/composables/useNetworkAnalysis'
import { downloadFile, fileSlug, isoDate, toCsv } from '@/utils/csv'

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '@/components/ui/dialog'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { Button } from '@/components/ui/button'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@/components/ui/select'

// Props
const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  clusterId: {
    type: Number,
    default: null
  },
  clusterDisplayName: {
    type: String,
    default: ''
  },
  /** Naming HPO term (useNetworkAnalysis clusterLabels), if any */
  clusterLabel: {
    type: String,
    default: ''
  },
  clusterColor: {
    type: String,
    default: OTHER_CLUSTER_COLOR
  },
  genes: {
    type: Array,
    default: () => []
  },
  hpoClassifications: {
    type: Object,
    default: null
  }
})

const LABEL_NOTE = `named after its most significant specific HPO term (FDR < ${LABEL_MAX_FDR})`

const focusDialog = event => {
  event.preventDefault()
  event.target?.focus()
}

// Emits
defineEmits(['update:modelValue', 'highlightGene'])

// Refs
const page = ref(1)
const itemsPerPage = ref(10)

// String version for Select component (radix-vue Select works with strings)
const itemsPerPageStr = computed({
  get: () => String(itemsPerPage.value),
  set: val => {
    itemsPerPage.value = Number(val)
    page.value = 1
  }
})

// Computed
const geneCount = computed(() => props.genes.length)

// Intra-cluster degree is shown when the graph passed it (genes arrive sorted hubs first)
const hasDegree = computed(() => props.genes.some(g => typeof g.degree === 'number'))

// STRING caps a network request at a few thousand identifiers; clusters stay far below that
const stringUrl = computed(() =>
  geneCount.value === 0
    ? null
    : `https://string-db.org/cgi/network?identifiers=${props.genes
        .map(g => encodeURIComponent(g.symbol))
        .join('%0d')}&species=9606`
)

const totalPages = computed(() => Math.ceil(geneCount.value / itemsPerPage.value))

const paginatedGenes = computed(() => {
  const start = (page.value - 1) * itemsPerPage.value
  const end = start + itemsPerPage.value
  return props.genes.slice(start, end)
})

const paginationText = computed(() => {
  if (geneCount.value === 0) return ''
  const start = (page.value - 1) * itemsPerPage.value + 1
  const end = Math.min(page.value * itemsPerPage.value, geneCount.value)
  return `Showing ${start}–${end} of ${geneCount.value}`
})

// HPO classification statistics for this cluster
const clusterStatistics = computed(() => {
  if (!props.hpoClassifications?.data || props.genes.length === 0) {
    return null
  }

  // Build HPO lookup
  const hpoLookup = new Map()
  props.hpoClassifications.data.forEach(item => {
    hpoLookup.set(item.gene_id, item)
  })

  const stats = computeHpoClusterStats(
    props.genes.map(gene => gene.gene_id),
    hpoLookup
  )
  return stats.hpoDataCount === 0 ? null : stats
})

// Options
const itemsPerPageOptions = [10, 20, 50, 100]

// Methods
const copyGeneSymbol = symbol => {
  navigator.clipboard
    .writeText(symbol)
    .then(() => {
      toast.success(`Copied ${symbol}`)
      window.logService?.debug('[ClusterDetails] Gene symbol copied to clipboard', { symbol })
    })
    .catch(error => {
      toast.error(`Could not copy ${symbol}`)
      window.logService?.error('[ClusterDetails] Failed to copy gene symbol', {
        symbol,
        error: error.message
      })
    })
}

const exportClusterGenes = () => {
  if (props.genes.length === 0) return

  // Use display name or fallback to cluster ID
  const clusterName = props.clusterDisplayName || `Cluster ${props.clusterId + 1}`

  const headers = ['Gene Symbol', 'HGNC ID', 'Cluster']
  if (hasDegree.value) headers.push('Links in Cluster')
  const rows = props.genes.map(g => {
    const row = [g.symbol, g.hgnc_id ?? '', clusterName]
    if (hasDegree.value) row.push(g.degree ?? '')
    return row
  })
  downloadFile(
    toCsv(headers, rows),
    `kgdb_${fileSlug(clusterName)}_${geneCount.value}genes_${isoDate()}.csv`,
    'text/csv'
  )
}

// Reset page when genes change
watch(
  () => props.genes,
  () => {
    page.value = 1
  }
)
</script>

<style scoped>
/* Statistics section styling */
.stats-section {
  height: 100%;
}
</style>
