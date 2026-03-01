<template>
  <Card class="mb-3">
    <CardContent class="pt-6">
      <div class="grid grid-cols-1 gap-4 md:grid-cols-4">
        <div class="space-y-2">
          <Label for="filter-status">Status</Label>
          <Select
            :model-value="filters.status || 'all'"
            @update:model-value="updateFilter('status', $event === 'all' ? null : $event)"
          >
            <SelectTrigger id="filter-status">
              <SelectValue placeholder="All Statuses" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem
                v-for="option in statusOptions"
                :key="option.value ?? 'all'"
                :value="option.value ?? 'all'"
              >
                {{ option.title }}
              </SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div class="space-y-2">
          <Label for="filter-trigger">Trigger Source</Label>
          <Select
            :model-value="filters.triggerSource || 'all'"
            @update:model-value="updateFilter('triggerSource', $event === 'all' ? null : $event)"
          >
            <SelectTrigger id="filter-trigger">
              <SelectValue placeholder="All Triggers" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem
                v-for="option in triggerOptions"
                :key="option.value ?? 'all'"
                :value="option.value ?? 'all'"
              >
                {{ option.title }}
              </SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div class="space-y-2">
          <Label for="filter-time">Time Range</Label>
          <Select
            :model-value="filters.timeRange"
            @update:model-value="updateFilter('timeRange', $event)"
          >
            <SelectTrigger id="filter-time">
              <SelectValue placeholder="All Time" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem v-for="option in timeRanges" :key="option.value" :value="option.value">
                {{ option.title }}
              </SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div class="space-y-2">
          <Label for="filter-search">Search</Label>
          <Input
            id="filter-search"
            :model-value="searchQuery"
            placeholder="Search description..."
            @update:model-value="$emit('update:searchQuery', $event)"
            @keyup.enter="$emit('apply')"
          />
        </div>
      </div>

      <div class="mt-4 flex justify-end gap-2">
        <Button size="sm" :disabled="loading" @click="$emit('apply')">
          <span
            v-if="loading"
            class="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent"
          />
          <Filter class="mr-1 size-4" />
          Apply Filters
        </Button>
        <Button size="sm" variant="outline" @click="$emit('clear')">
          <FilterX class="mr-1 size-4" />
          Clear
        </Button>
        <Button
          size="sm"
          variant="destructive"
          :disabled="cleanupLoading"
          @click="$emit('cleanup')"
        >
          <span
            v-if="cleanupLoading"
            class="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent"
          />
          <Trash class="mr-1 size-4" />
          Cleanup Old
        </Button>
      </div>
    </CardContent>
  </Card>
</template>

<script setup>
import { Filter, FilterX, Trash } from 'lucide-vue-next'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@/components/ui/select'

const props = defineProps({
  filters: {
    type: Object,
    required: true
  },
  searchQuery: {
    type: String,
    default: ''
  },
  loading: {
    type: Boolean,
    default: false
  },
  cleanupLoading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:filters', 'update:searchQuery', 'apply', 'clear', 'cleanup'])

// Options
const statusOptions = [
  { title: 'All Statuses', value: null },
  { title: 'Completed', value: 'completed' },
  { title: 'Running', value: 'running' },
  { title: 'Failed', value: 'failed' },
  { title: 'Pending', value: 'pending' }
]

const triggerOptions = [
  { title: 'All Triggers', value: null },
  { title: 'Manual API', value: 'manual_api' },
  { title: 'Scheduled Cron', value: 'scheduled_cron' },
  { title: 'Pre-Restore Safety', value: 'pre_restore_safety' }
]

const timeRanges = [
  { title: 'All Time', value: 'all' },
  { title: 'Last 24 Hours', value: '24h' },
  { title: 'Last 7 Days', value: '7d' },
  { title: 'Last 30 Days', value: '30d' }
]

// Methods
const updateFilter = (key, value) => {
  emit('update:filters', {
    ...props.filters,
    [key]: value
  })
}
</script>
