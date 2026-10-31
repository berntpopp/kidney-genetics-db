<script setup lang="ts">
/**
 * Susceptibility tier chip: neutral, never a Mendelian class colour (#437). Refuted is muted,
 * struck through and carries a cross icon so it never reads as a risk (#473).
 */
import { computed } from 'vue'
import { CircleX } from 'lucide-vue-next'
import { Chip } from '@/components/shared'

const props = defineProps<{ strength: string }>()
const refuted = computed(() => props.strength === 'Refuted association')
</script>

<template>
  <Chip
    kind="neutral"
    :icon="refuted ? CircleX : undefined"
    :class="refuted ? 'text-muted-foreground line-through' : undefined"
    :label="strength"
    :tooltip="
      refuted
        ? 'Refuted association: refuting evidence outweighs the support, so this is not a risk allele'
        : 'Susceptibility (risk) association, not a Mendelian validity class'
    "
  />
</template>
