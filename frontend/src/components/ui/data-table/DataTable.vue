<script setup lang="ts" generic="TData extends RowData">
import type { RowData, Table } from '@tanstack/vue-table'
import { FlexRender } from '@tanstack/vue-table'
import type { DataTableFeatures } from './features'
import {
  Table as UiTable,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from '@/components/ui/table'

interface Props {
  table: Table<DataTableFeatures, TData>
  loading?: boolean
  loadingText?: string
  /** Skeleton rows shown while the first page loads, so the table keeps its final height */
  skeletonRows?: number
}

withDefaults(defineProps<Props>(), { loading: false, loadingText: 'Loading...', skeletonRows: 0 })

/** Per-column classes from `columnDef.meta.class`, e.g. 'text-right' for numeric columns */
const metaClass = (column: { columnDef: { meta?: unknown } }) =>
  (column.columnDef.meta as { class?: string } | undefined)?.class
</script>

<template>
  <div class="rounded-md px-2">
    <UiTable>
      <TableHeader>
        <TableRow v-for="headerGroup in table.getHeaderGroups()" :key="headerGroup.id">
          <TableHead
            v-for="header in headerGroup.headers"
            :key="header.id"
            :class="metaClass(header.column)"
            :style="{ width: header.getSize() !== 150 ? `${header.getSize()}px` : undefined }"
          >
            <FlexRender
              v-if="!header.isPlaceholder"
              :render="header.column.columnDef.header"
              :props="header.getContext()"
            />
          </TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        <template v-if="table.getRowModel().rows?.length">
          <TableRow
            v-for="row in table.getRowModel().rows"
            :key="row.id"
            :data-state="row.getIsSelected() ? 'selected' : undefined"
          >
            <TableCell
              v-for="cell in row.getVisibleCells()"
              :key="cell.id"
              :class="metaClass(cell.column)"
            >
              <FlexRender :render="cell.column.columnDef.cell" :props="cell.getContext()" />
            </TableCell>
          </TableRow>
        </template>
        <template v-else-if="loading && skeletonRows > 0">
          <TableRow v-for="n in skeletonRows" :key="n">
            <TableCell v-for="(column, i) in table.getVisibleLeafColumns()" :key="column.id">
              <span v-if="n === 1 && i === 0" class="sr-only" role="status">{{ loadingText }}</span>
              <div class="h-6 rounded-md bg-muted motion-safe:animate-pulse" aria-hidden="true" />
            </TableCell>
          </TableRow>
        </template>
        <template v-else>
          <TableRow>
            <TableCell
              :colspan="table.getAllColumns().length"
              class="h-24 text-center text-muted-foreground"
            >
              {{ loading ? loadingText : 'No results.' }}
            </TableCell>
          </TableRow>
        </template>
      </TableBody>
    </UiTable>
  </div>
</template>
