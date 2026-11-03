<script setup lang="ts">
/** Rows-per-page select, page position and first/previous/next/last buttons, for any paged list */
import { computed } from 'vue'
import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@/components/ui/select'

const props = withDefaults(
  defineProps<{
    /** Zero-based page index */
    page: number
    pageSize: number
    total: number
    pageSizeOptions?: number[]
    /** What a row is, singular ("gene"); the total reads "2,045 genes" */
    noun?: string
  }>(),
  { pageSizeOptions: () => [10, 20, 30, 50, 100], noun: 'row' }
)
const emit = defineEmits<{ 'update:page': [number]; 'update:pageSize': [number] }>()

const pageCount = computed(() => Math.max(1, Math.ceil(props.total / props.pageSize)))
const canPrevious = computed(() => props.page > 0)
const canNext = computed(() => props.page < pageCount.value - 1)
</script>

<template>
  <div class="flex flex-wrap items-center justify-between gap-x-4 gap-y-2 px-4 py-2">
    <div class="flex-1 text-sm text-muted-foreground tabular-nums whitespace-nowrap">
      {{ `${total.toLocaleString()} ${noun}${total === 1 ? '' : 's'}` }}
    </div>
    <div class="flex flex-wrap items-center gap-x-6 gap-y-2 lg:gap-x-8">
      <div class="flex items-center space-x-2">
        <p class="text-sm font-medium">Rows per page</p>
        <Select
          :model-value="`${pageSize}`"
          @update:model-value="val => emit('update:pageSize', Number(val))"
        >
          <SelectTrigger class="h-8 w-[70px]" aria-label="Rows per page">
            <SelectValue :placeholder="`${pageSize}`" />
          </SelectTrigger>
          <SelectContent side="top">
            <SelectItem v-for="size in pageSizeOptions" :key="size" :value="`${size}`">
              {{ size }}
            </SelectItem>
          </SelectContent>
        </Select>
      </div>
      <div class="flex min-w-[100px] items-center justify-center text-sm font-medium tabular-nums">
        Page {{ page + 1 }} of {{ pageCount }}
      </div>
      <div class="flex items-center space-x-2">
        <Button
          aria-label="Go to first page"
          variant="outline"
          class="hidden h-8 w-8 p-0 lg:flex"
          :disabled="!canPrevious"
          @click="emit('update:page', 0)"
        >
          <ChevronsLeft class="h-4 w-4" />
        </Button>
        <Button
          aria-label="Go to previous page"
          variant="outline"
          class="h-8 w-8 p-0"
          :disabled="!canPrevious"
          @click="emit('update:page', page - 1)"
        >
          <ChevronLeft class="h-4 w-4" />
        </Button>
        <Button
          aria-label="Go to next page"
          variant="outline"
          class="h-8 w-8 p-0"
          :disabled="!canNext"
          @click="emit('update:page', page + 1)"
        >
          <ChevronRight class="h-4 w-4" />
        </Button>
        <Button
          aria-label="Go to last page"
          variant="outline"
          class="hidden h-8 w-8 p-0 lg:flex"
          :disabled="!canNext"
          @click="emit('update:page', pageCount - 1)"
        >
          <ChevronsRight class="h-4 w-4" />
        </Button>
      </div>
    </div>
  </div>
</template>
