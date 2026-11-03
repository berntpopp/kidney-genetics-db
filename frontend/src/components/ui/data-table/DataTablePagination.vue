<script setup lang="ts" generic="TData extends RowData">
import type { RowData, Table } from '@tanstack/vue-table'
import type { DataTableFeatures } from './features'
import PaginationBar from '@/components/shared/PaginationBar.vue'

interface Props {
  table: Table<DataTableFeatures, TData>
  pageSizeOptions?: number[]
  /** What a row is, singular ("gene"); the total reads "2,045 genes" */
  noun?: string
}

withDefaults(defineProps<Props>(), {
  pageSizeOptions: () => [10, 20, 30, 50, 100],
  noun: 'row'
})
</script>

<template>
  <PaginationBar
    :page="table.atoms.pagination.get().pageIndex"
    :page-size="table.atoms.pagination.get().pageSize"
    :total="table.getRowCount()"
    :page-size-options="pageSizeOptions"
    :noun="noun"
    @update:page="table.setPageIndex"
    @update:page-size="table.setPageSize"
  />
</template>
