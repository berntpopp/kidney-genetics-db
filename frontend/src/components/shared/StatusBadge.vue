<script setup lang="ts">
/** A status chip: one status -> one tone, label and icon everywhere (utils/status.ts). */
import Chip from './Chip.vue'

defineProps<{
  status: string | number | null | undefined
  /** Overrides the status label, e.g. "Running (3/7)" */
  label?: string
  tooltip?: string
}>()
</script>

<template>
  <Chip kind="status" :status="status ?? 'unknown'" :label="label" :tooltip="tooltip" />
</template>
