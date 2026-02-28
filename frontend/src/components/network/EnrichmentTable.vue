<script setup lang="ts">
import { ref, computed, h } from 'vue'
import type { ColumnDef } from '@tanstack/vue-table'
import {
  useVueTable,
  getCoreRowModel,
  getPaginationRowModel,
  getSortedRowModel
} from '@tanstack/vue-table'
import { ChartBarBig, ChevronRight, Download, RefreshCw, Loader2 } from 'lucide-vue-next'
import { DataTable, DataTableColumnHeader, DataTablePagination } from '@/components/ui/data-table'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Separator } from '@/components/ui/separator'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@/components/ui/select'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'

// Props
const props = defineProps({
  results: {
    type: Array as () => any[],
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  },
  error: {
    type: String,
    default: null
  },
  enrichmentType: {
    type: String,
    default: 'hpo'
  },
  geneSet: {
    type: String,
    default: 'GO_Biological_Process_2023'
  },
  fdrThreshold: {
    type: Number,
    default: 0.05
  }
})

// Emits
const emit = defineEmits([
  'refresh',
  'update:enrichmentType',
  'update:geneSet',
  'update:fdrThreshold',
  'geneClick'
])

// Refs
const geneDialog = ref(false)
const selectedTerm = ref<any>(null)

// Computed
const enrichmentStats = computed(() => {
  if (!props.results || props.results.length === 0) {
    return 'No significant terms'
  }
  return `${props.results.length} significant term(s) at FDR < ${props.fdrThreshold}`
})

// Options
const enrichmentTypeOptions = [
  { title: 'HPO (Human Phenotype Ontology)', value: 'hpo' },
  { title: 'GO (Gene Ontology)', value: 'go' }
]

const geneSetOptions = [
  { title: 'GO Biological Process', value: 'GO_Biological_Process_2023' },
  { title: 'GO Molecular Function', value: 'GO_Molecular_Function_2023' },
  { title: 'GO Cellular Component', value: 'GO_Cellular_Component_2023' },
  { title: 'KEGG Pathways', value: 'KEGG_2021_Human' },
  { title: 'Reactome Pathways', value: 'Reactome_2022' },
  { title: 'WikiPathways', value: 'WikiPathway_2023_Human' }
]

// Column definitions
const columns: ColumnDef<any>[] = [
  {
    accessorKey: 'term_name',
    header: ({ column }) => h(DataTableColumnHeader, { column, title: 'Term' }),
    cell: ({ row }) => {
      const name = row.getValue('term_name') as string
      const id = row.original.term_id
      return h(TooltipProvider, null, () =>
        h(Tooltip, null, {
          default: () => [
            h(TooltipTrigger, { asChild: true }, () =>
              h(
                'span',
                { class: 'text-sm max-w-[300px] truncate block cursor-help' },
                truncateTerm(name)
              )
            ),
            h(TooltipContent, { side: 'bottom', class: 'max-w-[400px]' }, () =>
              h('div', null, [h('strong', null, id), h('br'), name])
            )
          ]
        })
      )
    }
  },
  {
    accessorKey: 'p_value',
    header: ({ column }) => h(DataTableColumnHeader, { column, title: 'P-value' }),
    cell: ({ row }) =>
      h('span', { class: 'font-mono text-sm' }, formatPValue(row.getValue('p_value') as number)),
    size: 100
  },
  {
    accessorKey: 'fdr',
    header: ({ column }) => h(DataTableColumnHeader, { column, title: 'FDR' }),
    cell: ({ row }) => {
      const fdr = row.getValue('fdr') as number
      return h(
        Badge,
        {
          variant: 'outline',
          class: 'font-mono text-xs',
          style: {
            backgroundColor: getFdrBgColor(fdr),
            borderColor: getFdrTextColor(fdr),
            color: getFdrTextColor(fdr)
          }
        },
        () => formatPValue(fdr)
      )
    },
    size: 100
  },
  {
    accessorKey: 'enrichment_score',
    header: ({ column }) => h(DataTableColumnHeader, { column, title: 'Score' }),
    cell: ({ row }) => {
      const score = row.getValue('enrichment_score') as number
      return h(
        Badge,
        {
          variant: 'secondary',
          class: 'font-mono text-xs',
          style: { color: getEnrichmentTextColor(score) }
        },
        () => score.toFixed(2)
      )
    },
    size: 80
  },
  {
    accessorKey: 'odds_ratio',
    header: ({ column }) => h(DataTableColumnHeader, { column, title: 'Odds Ratio' }),
    cell: ({ row }) =>
      h('span', { class: 'text-sm' }, (row.getValue('odds_ratio') as number).toFixed(2)),
    size: 90
  },
  {
    id: 'gene_ratio',
    header: 'Ratio',
    cell: ({ row }) =>
      h(
        'span',
        { class: 'text-sm font-mono' },
        `${row.original.gene_count}/${row.original.cluster_size}`
      ),
    enableSorting: false,
    size: 70
  },
  {
    accessorKey: 'genes',
    header: 'Genes',
    cell: ({ row }) => {
      const genes = row.getValue('genes') as string[]
      return h(
        Button,
        {
          variant: 'outline',
          size: 'sm',
          class: 'h-7 text-xs',
          onClick: () => showGenes(row.original)
        },
        () => [`${genes.length} genes`, h(ChevronRight, { class: 'h-3 w-3 ml-1' })]
      )
    },
    enableSorting: false,
    size: 100
  }
]

// TanStack Table (client-side)
const table = useVueTable({
  get data() {
    return props.results || []
  },
  columns,
  getCoreRowModel: getCoreRowModel(),
  getPaginationRowModel: getPaginationRowModel(),
  getSortedRowModel: getSortedRowModel(),
  initialState: {
    pagination: { pageSize: 10 }
  }
})

// Methods
const truncateTerm = (term: string) => {
  const maxLength = 60
  if (term.length <= maxLength) return term
  return term.substring(0, maxLength) + '...'
}

const formatPValue = (value: number) => {
  if (value < 0.0001) return value.toExponential(2)
  if (value < 0.01) return value.toFixed(4)
  return value.toFixed(3)
}

const getFdrBgColor = (fdr: number) => {
  if (fdr < 0.001) return 'hsl(var(--chart-2) / 0.1)'
  if (fdr < 0.01) return 'hsl(var(--chart-1) / 0.1)'
  if (fdr < 0.05) return 'hsl(var(--chart-4) / 0.1)'
  return 'hsl(var(--muted))'
}

const getFdrTextColor = (fdr: number) => {
  if (fdr < 0.001) return 'hsl(var(--chart-2))'
  if (fdr < 0.01) return 'hsl(var(--chart-1))'
  if (fdr < 0.05) return 'hsl(var(--chart-4))'
  return 'hsl(var(--muted-foreground))'
}

const getEnrichmentTextColor = (score: number) => {
  if (score >= 5) return 'hsl(var(--chart-2))'
  if (score >= 3) return 'hsl(var(--chart-1))'
  if (score >= 1.3) return 'hsl(var(--chart-4))'
  return 'hsl(var(--muted-foreground))'
}

const showGenes = (term: any) => {
  selectedTerm.value = term
  geneDialog.value = true
}

const exportResults = () => {
  if (!props.results || props.results.length === 0) return

  const csvHeaders = [
    'Term ID',
    'Term Name',
    'P-value',
    'FDR',
    'Enrichment Score',
    'Odds Ratio',
    'Gene Count',
    'Cluster Size',
    'Genes'
  ]
  const rows = props.results.map((r: any) => [
    r.term_id,
    r.term_name,
    r.p_value,
    r.fdr,
    r.enrichment_score,
    r.odds_ratio,
    r.gene_count,
    r.cluster_size,
    r.genes.join('; ')
  ])

  const csv = [
    csvHeaders.join(','),
    ...rows.map((row: any[]) => row.map((cell: any) => `"${cell}"`).join(','))
  ].join('\n')

  const blob = new Blob([csv], { type: 'text/csv' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = `enrichment_${props.enrichmentType}_${Date.now()}.csv`
  link.click()
}
</script>

<template>
  <Card>
    <CardHeader class="pb-3">
      <div class="flex items-start justify-between">
        <div>
          <CardTitle class="text-lg">Functional Enrichment Analysis</CardTitle>
          <p class="text-sm text-muted-foreground mt-1">
            {{ enrichmentStats }}
          </p>
        </div>
        <div class="flex gap-1">
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger as-child>
                <Button
                  variant="ghost"
                  size="icon-sm"
                  :disabled="!results || results.length === 0"
                  @click="exportResults"
                >
                  <Download class="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Export results as CSV</TooltipContent>
            </Tooltip>
          </TooltipProvider>
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger as-child>
                <Button variant="ghost" size="icon-sm" @click="$emit('refresh')">
                  <RefreshCw class="h-4 w-4" :class="{ 'animate-spin': loading }" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Refresh enrichment</TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>
      </div>
    </CardHeader>

    <Separator />

    <!-- Controls -->
    <CardContent class="py-3">
      <div class="flex flex-col sm:flex-row gap-3">
        <div class="flex-1">
          <Label class="text-xs mb-1 block">Enrichment Type</Label>
          <Select
            :model-value="enrichmentType"
            @update:model-value="$emit('update:enrichmentType', $event)"
          >
            <SelectTrigger>
              <SelectValue placeholder="Select type..." />
            </SelectTrigger>
            <SelectContent>
              <SelectItem v-for="opt in enrichmentTypeOptions" :key="opt.value" :value="opt.value">
                {{ opt.title }}
              </SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div v-if="enrichmentType === 'go'" class="flex-1">
          <Label class="text-xs mb-1 block">Gene Set</Label>
          <Select :model-value="geneSet" @update:model-value="$emit('update:geneSet', $event)">
            <SelectTrigger>
              <SelectValue placeholder="Select gene set..." />
            </SelectTrigger>
            <SelectContent>
              <SelectItem v-for="opt in geneSetOptions" :key="opt.value" :value="opt.value">
                {{ opt.title }}
              </SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div class="w-full sm:w-[160px]">
          <Label class="text-xs mb-1 block">FDR Threshold</Label>
          <Input
            type="number"
            :model-value="fdrThreshold"
            min="0.001"
            max="0.2"
            step="0.01"
            @update:model-value="$emit('update:fdrThreshold', $event)"
          />
        </div>
      </div>
    </CardContent>

    <Separator />

    <!-- Results -->
    <CardContent class="p-0">
      <!-- Loading State -->
      <div v-if="loading" class="flex flex-col items-center justify-center py-12">
        <Loader2 class="h-10 w-10 animate-spin text-primary mb-4" />
        <p class="text-sm text-muted-foreground">Running enrichment analysis...</p>
      </div>

      <!-- Error State -->
      <div v-else-if="error" class="p-4">
        <Alert variant="destructive">
          <AlertTitle>Enrichment Error</AlertTitle>
          <AlertDescription>{{ error }}</AlertDescription>
        </Alert>
      </div>

      <!-- Empty State -->
      <div
        v-else-if="!results || results.length === 0"
        class="flex flex-col items-center justify-center py-12 text-muted-foreground"
      >
        <ChartBarBig class="h-16 w-16 mb-4" />
        <p class="text-base">No significant enrichment found</p>
        <p class="text-sm">Try adjusting the FDR threshold or cluster selection</p>
      </div>

      <!-- Data Table -->
      <template v-else>
        <DataTable :table="table" />
        <DataTablePagination :table="table" :page-size-options="[10, 20, 50, 100]" />
      </template>
    </CardContent>

    <!-- Gene List Dialog -->
    <Dialog v-model:open="geneDialog">
      <DialogContent class="max-w-md">
        <DialogHeader>
          <DialogTitle>{{ selectedTerm?.term_name }}</DialogTitle>
          <p class="text-sm text-muted-foreground mt-1">
            {{ selectedTerm?.term_id }}
          </p>
        </DialogHeader>
        <ScrollArea class="max-h-[300px]">
          <div class="flex flex-wrap gap-2 p-1">
            <Badge
              v-for="gene in selectedTerm?.genes"
              :key="gene"
              variant="outline"
              class="cursor-pointer hover:bg-primary/10"
              @click="emit('geneClick', gene)"
            >
              {{ gene }}
            </Badge>
          </div>
        </ScrollArea>
        <div class="flex justify-end">
          <Button variant="ghost" @click="geneDialog = false">Close</Button>
        </div>
      </DialogContent>
    </Dialog>
  </Card>
</template>
