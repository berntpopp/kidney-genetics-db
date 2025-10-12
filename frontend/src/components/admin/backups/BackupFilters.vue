<template>
  <v-card class="mb-3" rounded="lg">
    <v-card-text>
      <v-row>
        <v-col cols="12" md="3">
          <v-select
            :model-value="filters.status"
            label="Status"
            :items="statusOptions"
            density="compact"
            variant="outlined"
            clearable
            hide-details
            @update:model-value="updateFilter('status', $event)"
          />
        </v-col>
        <v-col cols="12" md="3">
          <v-select
            :model-value="filters.triggerSource"
            label="Trigger Source"
            :items="triggerOptions"
            density="compact"
            variant="outlined"
            clearable
            hide-details
            @update:model-value="updateFilter('triggerSource', $event)"
          />
        </v-col>
        <v-col cols="12" md="3">
          <v-select
            :model-value="filters.timeRange"
            label="Time Range"
            :items="timeRanges"
            density="compact"
            variant="outlined"
            hide-details
            @update:model-value="updateFilter('timeRange', $event)"
          />
        </v-col>
        <v-col cols="12" md="3">
          <v-text-field
            :model-value="searchQuery"
            label="Search description..."
            prepend-inner-icon="mdi-magnify"
            density="compact"
            variant="outlined"
            clearable
            hide-details
            @update:model-value="$emit('update:searchQuery', $event)"
            @keyup.enter="$emit('apply')"
          />
        </v-col>
      </v-row>

      <v-row class="mt-3">
        <v-col cols="12" class="text-right">
          <v-btn
            color="primary"
            size="small"
            prepend-icon="mdi-filter"
            :loading="loading"
            class="mr-2"
            @click="$emit('apply')"
          >
            Apply Filters
          </v-btn>
          <v-btn
            color="warning"
            size="small"
            prepend-icon="mdi-filter-off"
            variant="outlined"
            class="mr-2"
            @click="$emit('clear')"
          >
            Clear
          </v-btn>
          <v-btn
            color="error"
            size="small"
            prepend-icon="mdi-delete-sweep"
            :loading="cleanupLoading"
            @click="$emit('cleanup')"
          >
            Cleanup Old
          </v-btn>
        </v-col>
      </v-row>
    </v-card-text>
  </v-card>
</template>

<script setup>
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
