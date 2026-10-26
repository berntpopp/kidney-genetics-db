import {
  columnSizingFeature,
  columnVisibilityFeature,
  createPaginatedRowModel,
  createSortedRowModel,
  rowPaginationFeature,
  rowSelectionFeature,
  rowSortingFeature,
  sortFn_alphanumeric,
  sortFn_datetime,
  sortFn_text,
  tableFeatures
} from '@tanstack/vue-table'

// One feature set for every table so the shared components type-check against each of them.
// sortFns are the ones v8 'auto' sorting picked from; unpaged tables set manualPagination.
export const dataTableFeatures = tableFeatures({
  columnSizingFeature,
  columnVisibilityFeature,
  rowPaginationFeature,
  rowSelectionFeature,
  rowSortingFeature,
  sortedRowModel: createSortedRowModel(),
  paginatedRowModel: createPaginatedRowModel(),
  sortFns: { alphanumeric: sortFn_alphanumeric, datetime: sortFn_datetime, text: sortFn_text }
})

export type DataTableFeatures = typeof dataTableFeatures
