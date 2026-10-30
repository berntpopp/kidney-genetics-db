<script setup lang="ts">
/** Mode of inheritance as a short, aligned chip; the full HPO term is in the tooltip */
import { computed } from 'vue'
import { MOI_ABBREVIATIONS, MOI_TERMS } from '@/api/curation'
import { Chip } from '@/components/shared'

const props = defineProps<{ moi: string | null | undefined }>()

const short = computed(() => (props.moi ? (MOI_ABBREVIATIONS[props.moi] ?? props.moi) : '—'))
const full = computed(() =>
  props.moi
    ? `${MOI_TERMS[props.moi] ?? 'Unknown inheritance term'} (${props.moi})`
    : 'Mode of inheritance not specified'
)
</script>

<template>
  <Chip kind="neutral" :tooltip="full" class="min-w-11 justify-center font-mono" data-testid="moi">
    <span aria-hidden="true">{{ short }}</span>
    <span class="sr-only">{{ full }}</span>
  </Chip>
</template>
