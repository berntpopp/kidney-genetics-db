<script setup lang="ts">
/** A source's display name with its chart-colour marker dot and a description tooltip. */
import { computed } from 'vue'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { getSourceConfig } from '@/utils/sources'

const props = defineProps<{
  /** Backend source name, e.g. DiagnosticPanels */
  source: string
}>()

const config = computed(() => getSourceConfig(props.source))
</script>

<template>
  <Tooltip :disabled="!config.description">
    <TooltipTrigger as-child>
      <span
        data-slot="source-label"
        :tabindex="config.description ? 0 : undefined"
        class="inline-flex items-center gap-1.5 rounded-sm focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
      >
        <span
          class="size-2 shrink-0 rounded-full"
          :style="{ backgroundColor: config.chartColor }"
          aria-hidden="true"
        />
        <span>{{ config.displayName }}</span>
      </span>
    </TooltipTrigger>
    <TooltipContent v-if="config.description" class="max-w-xs">{{
      config.description
    }}</TooltipContent>
  </Tooltip>
</template>
