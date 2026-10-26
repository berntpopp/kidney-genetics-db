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
}

withDefaults(defineProps<Props>(), { loading: false, loadingText: 'Loading...' })
</script>

<template>
  <div class="rounded-md px-2">
    <UiTable>
      <TableHeader>
        <TableRow v-for="headerGroup in table.getHeaderGroups()" :key="headerGroup.id">
          <TableHead
            v-for="header in headerGroup.headers"
            :key="header.id"
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
            <TableCell v-for="cell in row.getVisibleCells()" :key="cell.id">
              <FlexRender :render="cell.column.columnDef.cell" :props="cell.getContext()" />
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
