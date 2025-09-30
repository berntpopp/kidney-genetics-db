<template>
  <v-tooltip location="bottom" max-width="320">
    <template #activator="{ props: tooltipProps }">
      <v-chip
        :color="tierConfig.color"
        :size="size"
        variant="flat"
        class="font-weight-medium tier-chip"
        v-bind="tooltipProps"
      >
        <v-icon :icon="tierConfig.icon" size="small" start />
        {{ tierConfig.label }}
      </v-chip>
    </template>
    <div class="pa-2">
      <div class="text-subtitle-2 font-weight-bold mb-1">{{ tierConfig.label }}</div>
      <div class="text-caption">{{ tierConfig.description }}</div>
    </div>
  </v-tooltip>
</template>

<script setup>
import { computed } from 'vue'
import { getTierConfig } from '@/utils/evidenceTiers'

/**
 * Props
 * @property {string|null} tier - Evidence tier name (comprehensive_support, multi_source_support, etc.)
 * @property {string} size - Chip size (x-small, small, default)
 */
const props = defineProps({
  tier: {
    type: String,
    default: null
  },
  size: {
    type: String,
    default: 'small',
    validator: value => ['x-small', 'small', 'default'].includes(value)
  }
})

// Computed properties
const tierConfig = computed(() => getTierConfig(props.tier))
</script>

<style scoped>
/* Following Style Guide - Compact density for data interfaces */
.tier-chip {
  cursor: help;
  transition: all 0.2s ease;
}

/* Focus states - Following Style Guide */
.tier-chip:focus-visible {
  outline: 2px solid rgb(var(--v-theme-primary));
  outline-offset: 2px;
}
</style>
