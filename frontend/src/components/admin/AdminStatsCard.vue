<script setup lang="ts">
/**
 * One admin KPI card: label, tabular value, optional subtitle and trend. With `to` the whole
 * card is a link (keyboard reachable). Loading keeps the final height (skeleton value).
 */
import { computed, type Component } from 'vue'
import { RouterLink } from 'vue-router'
import { TrendingDown, TrendingUp } from 'lucide-vue-next'

const props = withDefaults(
  defineProps<{
    title: string
    /** null renders as an em dash (unknown or failed to load) */
    value: string | number | null
    icon: Component
    subtitle?: string | null
    /** Percent change; positive is shown as success, negative as danger */
    trend?: number | null
    loading?: boolean
    format?: 'number' | 'percent' | 'bytes'
    /** Route the card links to */
    to?: string
  }>(),
  { subtitle: null, trend: null, loading: false, format: 'number', to: undefined }
)

const formattedValue = computed(() => {
  const v = props.value
  if (v === null || v === '') return '—'
  if (props.format === 'percent') return `${v}%`
  if (props.format === 'bytes') {
    const bytes = Number(v)
    if (bytes >= 1024 ** 3) return `${(bytes / 1024 ** 3).toFixed(2)} GB`
    if (bytes >= 1024 ** 2) return `${(bytes / 1024 ** 2).toFixed(2)} MB`
    if (bytes >= 1024) return `${(bytes / 1024).toFixed(2)} KB`
    return `${bytes} B`
  }
  return typeof v === 'number' ? v.toLocaleString() : v
})
</script>

<template>
  <component
    :is="to ? RouterLink : 'div'"
    :to="to"
    data-slot="admin-stat"
    class="block rounded-xl border bg-card p-4"
    :class="
      to &&
      'transition-colors hover:border-primary/40 hover:bg-muted/50 focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none'
    "
  >
    <div class="flex items-start justify-between gap-3">
      <div class="min-w-0">
        <p class="text-xs font-medium text-muted-foreground">{{ title }}</p>
        <div
          v-if="loading"
          class="mt-1 h-8 w-16 rounded-md bg-muted motion-safe:animate-pulse"
          aria-hidden="true"
        />
        <p v-else class="mt-1 text-2xl font-semibold tabular-nums">{{ formattedValue }}</p>
        <p v-if="subtitle" class="mt-1 text-xs text-muted-foreground">{{ subtitle }}</p>
      </div>
      <component :is="icon" class="size-5 shrink-0 text-muted-foreground" aria-hidden="true" />
    </div>
    <div v-if="trend !== null && !loading" class="mt-2 flex items-center gap-1 text-xs">
      <TrendingUp v-if="trend > 0" class="size-3.5 text-success" aria-hidden="true" />
      <TrendingDown v-else-if="trend < 0" class="size-3.5 text-danger" aria-hidden="true" />
      <span
        class="tabular-nums"
        :class="trend > 0 ? 'text-success' : trend < 0 ? 'text-danger' : 'text-muted-foreground'"
      >
        {{ trend > 0 ? '+' : trend < 0 ? '−' : '' }}{{ Math.abs(trend).toFixed(1) }}%
      </span>
    </div>
  </component>
</template>
