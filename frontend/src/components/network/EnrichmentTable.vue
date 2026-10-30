<script setup lang="ts">
import { ref, computed, h } from 'vue'
import type { ColumnDef } from '@tanstack/vue-table'
import { useTable } from '@tanstack/vue-table'
import { ChartBarBig, ChevronRight, Download, RefreshCw } from 'lucide-vue-next'
import {
  DataTable,
  DataTableColumnHeader,
  DataTablePagination,
  dataTableFeatures
} from '@/components/ui/data-table'
import type { DataTableFeatures } from '@/components/ui/data-table'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Separator } from '@/components/ui/separator'
import { DataState } from '@/components/shared'
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
import { downloadFile, fileSlug, isoDate, toCsv } from '@/utils/csv'
import { ontologyUrl } from '@/utils/ontology'

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
  },
  excludedGenes: {
    type: Array as () => number[],
    default: () => []
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
  // Never show the previous run's count while a new one is running
  if (props.loading) return 'Running enrichment analysis…'
  if (props.error) return 'Enrichment analysis failed'
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
const columns: ColumnDef<DataTableFeatures, any>[] = [
  {
    accessorKey: 'term_name',
    header: ({ column }) => h(DataTableColumnHeader, { column, title: 'Term' }),
    // CSS truncation keeps the full name in the DOM (screen readers, copy) and in the title
    cell: ({ row }) => {
      const name = row.getValue('term_name') as string
      return h('span', { class: 'block max-w-[320px] truncate text-sm', title: name }, name)
    }
  },
  {
    accessorKey: 'term_id',
    header: 'ID',
    cell: ({ row }) => {
      const id = row.getValue('term_id') as string
      const url = termUrl(id)
      const cls = 'font-mono text-xs whitespace-nowrap'
      return url
        ? h(
            'a',
            {
              href: url,
              target: '_blank',
              rel: 'noopener noreferrer',
              class: `${cls} rounded-sm text-primary underline-offset-4 hover:underline focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none`,
              'aria-label': `${id} (opens in a new tab)`
            },
            id
          )
        : h('span', { class: `${cls} text-muted-foreground` }, id)
    },
    enableSorting: false,
    size: 110
  },
  {
    accessorKey: 'p_value',
    header: ({ column }) => h(DataTableColumnHeader, { column, title: 'P-value' }),
    cell: ({ row }) =>
      h(
        'span',
        { class: 'font-mono text-sm tabular-nums' },
        formatPValue(row.getValue('p_value') as number)
      ),
    size: 100
  },
  {
    accessorKey: 'fdr',
    header: ({ column }) => h(DataTableColumnHeader, { column, title: 'FDR' }),
    cell: ({ row }) => {
      const fdr = row.getValue('fdr') as number
      return h('span', { class: 'font-mono text-sm tabular-nums' }, formatPValue(fdr))
    },
    size: 100
  },
  {
    accessorKey: 'enrichment_score',
    header: ({ column }) => h(DataTableColumnHeader, { column, title: 'Score' }),
    cell: ({ row }) => {
      const score = row.getValue('enrichment_score') as number
      return h('span', { class: 'font-mono text-sm tabular-nums' }, score.toFixed(2))
    },
    size: 80
  },
  {
    accessorKey: 'odds_ratio',
    header: ({ column }) => h(DataTableColumnHeader, { column, title: 'Odds Ratio' }),
    cell: ({ row }) =>
      h(
        'span',
        { class: 'font-mono text-sm tabular-nums' },
        (row.getValue('odds_ratio') as number).toFixed(2)
      ),
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
    accessorKey: 'background_count',
    header: ({ column }) => h(DataTableColumnHeader, { column, title: 'Background' }),
    cell: ({ row }) => {
      const n = row.original.background_count
      return h(
        'span',
        { class: 'text-sm tabular-nums', title: 'Background genes annotated with this term' },
        n === null || n === undefined ? '—' : n.toLocaleString()
      )
    },
    size: 90
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
const table = useTable({
  features: dataTableFeatures,
  get data() {
    return props.results || []
  },
  columns,
  initialState: {
    pagination: { pageIndex: 0, pageSize: 10 }
  }
})

// Methods
// HPO via the shared ontology helper; GO terms go to AmiGO. Other gene-set IDs stay plain text
const termUrl = (id: string) =>
  /^GO:\d{7}$/.test(id)
    ? `https://amigo.geneontology.org/amigo/term/${id}`
    : /^HP:\d{7}$/.test(id)
      ? ontologyUrl(id)
      : null

// p-values and FDR always in scientific notation, so columns compare at a glance
const formatPValue = (value: number) => value.toExponential(2)

const showGenes = (term: any) => {
  selectedTerm.value = term
  geneDialog.value = true
}

const exportResults = () => {
  if (!props.results || props.results.length === 0) return
  const headers = [
    'Term ID',
    'Term Name',
    'P-value',
    'FDR',
    'Enrichment Score',
    'Odds Ratio',
    'Gene Count',
    'Cluster Size',
    'Background Count',
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
    r.background_count,
    r.genes.join('; ')
  ])
  const kind = props.enrichmentType === 'go' ? fileSlug(props.geneSet) : props.enrichmentType
  downloadFile(
    toCsv(headers, rows),
    `kgdb_enrichment_${kind}_${props.results.length}terms_${isoDate()}.csv`,
    'text/csv'
  )
}
</script>

<template>
  <Card>
    <CardHeader class="pb-3">
      <div class="flex items-start justify-between">
        <div>
          <CardTitle tag="h2" class="text-lg">Functional Enrichment Analysis</CardTitle>
          <p class="text-sm text-muted-foreground mt-1">
            {{ enrichmentStats }}
          </p>
          <p v-if="excludedGenes.length" class="text-xs text-muted-foreground">
            {{ excludedGenes.length }} {{ excludedGenes.length === 1 ? 'gene' : 'genes' }} excluded
            (no HPO annotation / outside background)
          </p>
        </div>
        <div class="flex gap-1">
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger as-child>
                <Button
                  aria-label="Export results as CSV"
                  variant="ghost"
                  size="icon-sm"
                  :disabled="loading || !results || results.length === 0"
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
                <Button
                  aria-label="Refresh enrichment"
                  variant="ghost"
                  size="icon-sm"
                  @click="$emit('refresh')"
                >
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
          <Label for="et-type" class="text-xs mb-1 block">Enrichment Type</Label>
          <Select
            :model-value="enrichmentType"
            @update:model-value="$emit('update:enrichmentType', $event)"
          >
            <SelectTrigger id="et-type" class="w-full">
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
          <Label for="et-gene-set" class="text-xs mb-1 block">Gene Set</Label>
          <Select :model-value="geneSet" @update:model-value="$emit('update:geneSet', $event)">
            <SelectTrigger id="et-gene-set" class="w-full">
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
          <Label for="et-fdr" class="text-xs mb-1 block">FDR Threshold</Label>
          <Input
            id="et-fdr"
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
      <DataState
        :loading="loading"
        :error="error"
        :empty="!results || results.length === 0"
        error-title="Could not run the enrichment analysis"
        @retry="$emit('refresh')"
      >
        <template #loading>
          <div class="space-y-2 p-4">
            <p class="text-sm text-muted-foreground">Running enrichment analysis…</p>
            <div
              v-for="n in 6"
              :key="n"
              class="h-9 rounded-md bg-muted motion-safe:animate-pulse"
            />
          </div>
        </template>
        <template #empty>
          <ChartBarBig class="size-8 text-muted-foreground" aria-hidden="true" />
          <p class="text-sm font-medium">No significant enrichment found</p>
          <p class="text-sm text-muted-foreground">
            Try adjusting the FDR threshold or cluster selection.
          </p>
        </template>
        <DataTable :table="table" />
        <DataTablePagination :table="table" :page-size-options="[10, 20, 50, 100]" />
      </DataState>
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
            <Button
              v-for="gene in selectedTerm?.genes"
              :key="gene"
              variant="outline"
              size="sm"
              class="h-7 px-2 text-xs"
              @click="emit('geneClick', gene)"
            >
              {{ gene }}
            </Button>
          </div>
        </ScrollArea>
        <div class="flex justify-end">
          <Button variant="ghost" @click="geneDialog = false">Close</Button>
        </div>
      </DialogContent>
    </Dialog>
  </Card>
</template>
