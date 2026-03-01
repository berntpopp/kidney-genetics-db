<template>
  <div
    class="rounded-lg border bg-card p-4 transition-shadow"
    :class="[clickable ? 'cursor-pointer hover:shadow-md' : '']"
    @click="handleClick"
  >
    <div v-if="loading" class="flex items-center justify-center py-4">
      <div class="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
    </div>
    <template v-else>
      <div class="flex items-center justify-between">
        <div>
          <p class="text-xs font-medium text-muted-foreground">{{ title }}</p>
          <p class="mt-1 text-2xl font-bold">{{ formattedValue }}</p>
          <p v-if="subtitle" class="mt-1 text-xs text-muted-foreground">
            {{ subtitle }}
          </p>
        </div>
        <div
          v-if="resolvedIcon"
          class="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10"
        >
          <component :is="resolvedIcon" :size="20" class="text-primary" />
        </div>
      </div>
      <div v-if="trend !== null" class="mt-2 flex items-center gap-1 text-xs">
        <TrendingUp v-if="trend > 0" :size="14" class="text-green-500" />
        <TrendingDown v-else-if="trend < 0" :size="14" class="text-red-500" />
        <span
          :class="
            trend > 0 ? 'text-green-500' : trend < 0 ? 'text-red-500' : 'text-muted-foreground'
          "
        >
          {{ Math.abs(trend).toFixed(1) }}%
        </span>
      </div>
    </template>
  </div>
</template>

<script setup>
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

  if (typeof props.value === 'number' && props.value >= 1000) {
    return props.value.toLocaleString()
  }

  return props.value
})

const resolvedIcon = computed(() => resolveMdiIcon(props.icon))

const handleClick = () => {
  if (props.clickable) {
    emit('click')
  }
}
</script>
