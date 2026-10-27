<template>
  <Dialog :open="modelValue" @update:open="$emit('update:modelValue', $event)">
    <DialogContent class="sm:max-w-4xl max-h-[90vh] overflow-y-auto">
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
            <DialogTitle class="text-lg font-medium">Cluster Details</DialogTitle>
            <p class="text-xs text-muted-foreground mt-1">
              {{ geneCount }} gene{{ geneCount !== 1 ? 's' : '' }} in cluster
            </p>
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
              <th class="p-2 text-left font-semibold whitespace-nowrap">Gene Symbol</th>
              <th class="p-2 text-left font-semibold whitespace-nowrap">HGNC</th>
              <th class="p-2 text-right font-semibold whitespace-nowrap">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="item in paginatedGenes"
              :key="item.gene_id"
              class="border-b last:border-0 hover:bg-muted/50"
            >
              <!-- Gene Symbol with Link -->
              <td class="p-2">
                <router-link :to="`/genes/${item.symbol}`" class="gene-link">
                  <Badge variant="outline" class="flex items-center gap-1 w-fit">
                    <Dna class="size-4" />
                    {{ item.symbol }}
                  </Badge>
                </router-link>
              </td>

              <!-- HGNC identifier, named by its symbol -->
              <td class="p-2">
                <OntologyTerm v-if="item.hgnc_id" :id="item.hgnc_id" :name="item.symbol" />
                <span v-else class="text-xs text-muted-foreground">Not available</span>
              </td>

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
        <Button variant="ghost" size="sm" @click="exportClusterGenes">
          <Download class="size-4 mr-2" />
          Export Genes
        </Button>
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
  Dna,
  Download,
  Eye,
  MapPin
} from 'lucide-vue-next'
import { toast } from 'vue-sonner'
import { networkAnalysisConfig, OTHER_CLUSTER_COLOR } from '../../config/networkAnalysis'
import { tintedChipStyle } from '@/utils/evidenceTiers'
import { OntologyTerm } from '@/components/shared'
import { computeHpoClusterStats } from './hpoClusterStats'

import {
  Dialog,
  DialogContent,
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

  // Create CSV content
  const csvHeaders = ['Gene Symbol', 'HGNC ID', 'Cluster']
  const rows = props.genes.map(g => [g.symbol, g.hgnc_id ?? '', clusterName])

  const csv = [csvHeaders.join(','), ...rows.map(row => row.join(','))].join('\n')

  // Download CSV
  const blob = new Blob([csv], { type: 'text/csv' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  const sanitizedName = clusterName.toLowerCase().replace(/\s+/g, '_')
  link.download = `${sanitizedName}_genes_${Date.now()}.csv`
  link.click()
  setTimeout(() => URL.revokeObjectURL(link.href))
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
.gene-link {
  text-decoration: none;
  transition: opacity 0.2s;
}

.gene-link:hover {
  opacity: 0.8;
}

/* Statistics section styling */
.stats-section {
  height: 100%;
}
</style>
