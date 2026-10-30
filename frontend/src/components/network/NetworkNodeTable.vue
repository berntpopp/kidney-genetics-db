<template>
  <div class="p-3">
    <Table>
      <caption class="sr-only">
        Genes in the network. Sortable by column; activate a gene for its details.
      </caption>
      <TableHeader>
        <TableRow>
          <TableHead v-for="col in columns" :key="col.key" :aria-sort="ariaSort(col.key)">
            <Button
              v-if="col.sortable"
              variant="ghost"
              size="sm"
              class="-ml-2 h-8 gap-1 px-2"
              @click="sortBy(col.key)"
            >
              {{ col.label }}
              <component :is="sortIcon(col.key)" class="size-3.5" aria-hidden="true" />
            </Button>
            <template v-else>{{ col.label }}</template>
          </TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        <TableRow v-for="row in pageRows" :key="row.gene_id">
          <TableCell>
            <Button
              variant="link"
              class="h-auto p-0 font-medium"
              @click="select(row)"
              @keydown.enter.prevent="select(row)"
            >
              {{ row.label }}
            </Button>
          </TableCell>
          <TableCell class="text-muted-foreground tabular-nums">{{ row.hgnc_id ?? '—' }}</TableCell>
          <TableCell>
            <span v-if="row.clusterName" class="inline-flex items-center gap-1.5">
              <span
                class="size-2.5 shrink-0 rounded-full border"
                :style="{ backgroundColor: row.color, borderColor: row.outline }"
                aria-hidden="true"
              />
              {{ row.clusterName }}
            </span>
            <span v-else class="text-muted-foreground">Not clustered</span>
          </TableCell>
          <TableCell class="tabular-nums">{{ row.degree }}</TableCell>
        </TableRow>
        <TableRow v-if="sorted.length === 0">
          <TableCell :colspan="columns.length" class="py-6 text-center text-muted-foreground">
            No genes match the search.
          </TableCell>
        </TableRow>
      </TableBody>
    </Table>

    <div
      v-if="pageCount > 1"
      class="mt-3 flex items-center justify-end gap-2 text-sm text-muted-foreground"
    >
      <span aria-live="polite" class="tabular-nums">
        {{ page * PAGE_SIZE + 1 }}–{{ Math.min((page + 1) * PAGE_SIZE, sorted.length) }} of
        {{ sorted.length }}
      </span>
      <Button variant="outline" size="sm" :disabled="page === 0" @click="page--">Previous</Button>
      <Button variant="outline" size="sm" :disabled="page >= pageCount - 1" @click="page++">
        Next
      </Button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ArrowDown, ArrowUp, ArrowUpDown } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from '@/components/ui/table'

export interface NodeRow {
  gene_id: number
  label: string
  hgnc_id: string | null
  cluster_id: number | null | undefined
  clusterName: string | null
  /** Display rank of the cluster, for sorting in legend order */
  clusterRank: number
  color: string
  outline: string
  degree: number
}
type SortKey = 'label' | 'cluster' | 'degree'

const props = defineProps<{ rows: NodeRow[] }>()
const emit = defineEmits<{
  select: [payload: { label: string; gene_id: number; cluster_id: NodeRow['cluster_id'] }]
}>()

const PAGE_SIZE = 25
const columns: { key: SortKey | 'hgnc'; label: string; sortable: boolean }[] = [
  { key: 'label', label: 'Gene', sortable: true },
  { key: 'hgnc', label: 'HGNC ID', sortable: false },
  { key: 'cluster', label: 'Cluster', sortable: true },
  { key: 'degree', label: 'Degree', sortable: true }
]

const sortKey = ref<SortKey>('degree')
const descending = ref(true)
const page = ref(0)

const compare = {
  label: (a: NodeRow, b: NodeRow) => a.label.localeCompare(b.label),
  cluster: (a: NodeRow, b: NodeRow) => a.clusterRank - b.clusterRank,
  degree: (a: NodeRow, b: NodeRow) => a.degree - b.degree
}

const sorted = computed(() => {
  const dir = descending.value ? -1 : 1
  const by = compare[sortKey.value]
  return [...props.rows].sort((a, b) => dir * by(a, b) || a.label.localeCompare(b.label))
})
const pageCount = computed(() => Math.ceil(sorted.value.length / PAGE_SIZE))
const pageRows = computed(() =>
  sorted.value.slice(page.value * PAGE_SIZE, (page.value + 1) * PAGE_SIZE)
)

// A new search or network starts on the first page
watch(
  () => props.rows,
  () => (page.value = 0)
)

const sortBy = (key: SortKey | 'hgnc') => {
  if (key === 'hgnc') return
  if (sortKey.value === key) descending.value = !descending.value
  else {
    sortKey.value = key
    descending.value = key === 'degree'
  }
  page.value = 0
}
const ariaSort = (key: string) =>
  key === sortKey.value ? (descending.value ? 'descending' : 'ascending') : undefined
const sortIcon = (key: string) =>
  key !== sortKey.value ? ArrowUpDown : descending.value ? ArrowDown : ArrowUp

const select = (row: NodeRow) =>
  emit('select', { label: row.label, gene_id: row.gene_id, cluster_id: row.cluster_id })
</script>
