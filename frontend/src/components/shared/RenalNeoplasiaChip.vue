<script setup lang="ts">
/** Flags renal-neoplasia (tumour-predisposition) genes; the backend decides which (#447). */
import { Ribbon } from 'lucide-vue-next'
import Chip from './Chip.vue'
import { STATUS_TONE_CLASSES } from '@/utils/status'
</script>

<template>
  <Chip
    kind="neutral"
    :icon="Ribbon"
    label="Renal neoplasia"
    :class="STATUS_TONE_CLASSES.warning"
    tooltip="HPO places this gene in the renal neoplasia clinical group (tumour predisposition). Its ClinGen/GenCC assertions still count toward the score."
  />
</template>
