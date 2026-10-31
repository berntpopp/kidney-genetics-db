<script setup lang="ts">
/** A Gene Curator import only an AI approved: pending, then done, KGDB human review (#639) */
import { computed } from 'vue'
import type { Association } from '@/api/curation'
import { Chip } from '@/components/shared'

const props = defineProps<{ record: Association }>()

const chip = computed(() => {
  const r = props.record
  if (r.approval_kind !== 'ai') return null
  const model = r.approval_model ? ` (${r.approval_model})` : ''
  if (!r.human_reviewed_at) {
    return {
      status: 'warning',
      label: 'AI-reviewed · pending human review',
      tooltip: `Approved in Gene Curator by an AI reviewer${model}; a KGDB curator has not reviewed it yet.`
    }
  }
  const by = r.human_reviewer_name ? ` by ${r.human_reviewer_name}` : ''
  return {
    status: 'approved',
    label: 'Human-reviewed',
    tooltip: `First approved by an AI reviewer${model}; reviewed${by} in KGDB on ${r.human_reviewed_at.slice(0, 10)}.`
  }
})
</script>

<template>
  <Chip v-if="chip" v-bind="chip" />
</template>
