<template>
  <v-card class="pa-4" :hover="clickable" @click="handleClick">
    <div class="d-flex align-center justify-space-between">
      <div class="flex-grow-1">
        <p class="text-caption text-medium-emphasis mb-1">{{ title }}</p>
        <p class="text-h5 font-weight-medium">
          <v-progress-circular v-if="loading" indeterminate size="20" width="2" :color="color" />
          <span v-else>{{ formattedValue }}</span>
        </p>
        <p v-if="subtitle" class="text-caption text-medium-emphasis mt-1">
          {{ subtitle }}
        </p>
      </div>
      <component :is="resolvedIcon" v-if="resolvedIcon" class="size-6 ml-3" />
    </div>
    <div v-if="trend !== null" class="mt-3 d-flex align-center">
      <component :is="resolvedTrendIcon" v-if="resolvedTrendIcon" class="size-4 mr-1" />
      <span class="text-caption" :class="`text-${trendColor}`">
        {{ Math.abs(trend) }}% {{ trend > 0 ? 'increase' : 'decrease' }}
      </span>
    </div>
  </v-card>
</template>

<script setup>
/**
 * Compact stats display card for admin dashboard
 * Following Material Design 3 principles
 */

import { computed } from 'vue'
import { resolveMdiIcon, TrendingUp, TrendingDown } from '@/utils/icons'

const props = defineProps({
  title: {
    type: String,
    required: true
  },
  value: {
    type: [String, Number],
    required: true
  },
  icon: {
    type: String,
    required: true
  },
  color: {
    type: String,
    default: 'primary'
  },
  subtitle: {
    type: String,
    default: null
  },
  trend: {
    type: Number,
    default: null
  },
  loading: {
    type: Boolean,
    default: false
  },
  clickable: {
    type: Boolean,
    default: false
  },
  format: {
    type: String,
    default: 'number' // number, percent, bytes
  }
})

const emit = defineEmits(['click'])

const formattedValue = computed(() => {
  if (props.loading) return ''

  if (props.format === 'percent') {
    return `${props.value}%`
  } else if (props.format === 'bytes') {
    const bytes = Number(props.value)
    if (bytes >= 1024 * 1024 * 1024) {
      return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`
    } else if (bytes >= 1024 * 1024) {
      return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
    } else if (bytes >= 1024) {
      return `${(bytes / 1024).toFixed(2)} KB`
    }
    return `${bytes} B`
  }

  // Format large numbers with commas
  if (typeof props.value === 'number' && props.value >= 1000) {
    return props.value.toLocaleString()
  }

  return props.value
})

const resolvedIcon = computed(() => resolveMdiIcon(props.icon))

const resolvedTrendIcon = computed(() => {
  if (props.trend === null) return null
  return props.trend > 0 ? TrendingUp : TrendingDown
})

const trendColor = computed(() => {
  if (props.trend === null) return null
  return props.trend > 0 ? 'success' : 'error'
})

const handleClick = () => {
  if (props.clickable) {
    emit('click')
  }
}
</script>
