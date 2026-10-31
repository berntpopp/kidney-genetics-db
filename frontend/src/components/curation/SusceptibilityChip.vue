<script setup lang="ts">
/**
 * Susceptibility tier chip: neutral, never a Mendelian class colour (#437). Refuted is muted,
 * struck through and carries a cross icon so it never reads as a risk (#473).
 */
import { CircleX } from 'lucide-vue-next'
import { Chip } from '@/components/shared'

const props = defineProps<{ strength: string }>()
const refuted = props.strength === 'Refuted association'
</script>

<template>
  <Chip
    v-if="refuted"
    kind="neutral"
    :icon="CircleX"
    class="text-muted-foreground line-through"
    :label="strength"
    tooltip="Refuted association: refuting evidence outweighs the support, so this is not a risk allele"
  />
  <Chip
    v-else
    kind="neutral"
    :label="strength"
    tooltip="Susceptibility (risk) association, not a Mendelian validity class"
  />
</template>
