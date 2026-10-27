<script setup lang="ts">
/**
 * One chip for tiers, classifications, statuses and neutral labels (DESIGN.md Chips).
 * Colour comes only from evidenceTiers.ts / status.ts; the icon is the non-colour cue.
 * Renders a <button> only when a click listener is bound, otherwise a <span>; a chip with a
 * tooltip is focusable so the explanation is reachable by keyboard.
 */
import { computed, useAttrs, type Component } from 'vue'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { cn } from '@/lib/utils'
import { getClassificationConfig, getTierConfig, tintedChipStyle } from '@/utils/evidenceTiers'
import { getStatusConfig, STATUS_TONE_CLASSES } from '@/utils/status'

defineOptions({ inheritAttrs: false })

const props = defineProps<{
  kind?: 'strength' | 'neutral' | 'status'
  /** Evidence tier key, e.g. comprehensive_support */
  tier?: string | null
  /** ClinGen/GenCC classification, e.g. Definitive */
  classification?: string | null
  status?: string | number | null
  /** Overrides the resolved label (required for neutral chips) */
  label?: string | number
  /** Tooltip text; strength and status chips default to their description */
  tooltip?: string
  /** Icon for neutral chips; strength and status chips bring their own */
  icon?: Component
  class?: string
}>()

const attrs = useAttrs()
const clickable = computed(() => typeof attrs.onClick === 'function')

const resolved = computed(() => {
  const kind =
    props.kind ??
    (props.tier !== undefined || props.classification !== undefined
      ? 'strength'
      : props.status !== undefined
        ? 'status'
        : 'neutral')
  if (kind === 'strength' && props.classification !== undefined) {
    const c = getClassificationConfig(props.classification)
    return {
      label: c.label,
      icon: c.icon,
      tip: `${c.label}: ${c.description}`,
      style: c.tone === 'strength' ? tintedChipStyle(c.color) : undefined,
      cls: c.tone === 'strength' ? '' : STATUS_TONE_CLASSES[c.tone]
    }
  }
  if (kind === 'strength') {
    const t = getTierConfig(props.tier)
    return {
      label: t.label,
      icon: t.icon,
      tip: `${t.label}: ${t.description}`,
      style: tintedChipStyle(t.color),
      cls: ''
    }
  }
  if (kind === 'status') {
    const s = getStatusConfig(props.status)
    return {
      label: s.label,
      icon: s.icon,
      spin: s.spin,
      tip: '',
      style: undefined,
      cls: STATUS_TONE_CLASSES[s.tone]
    }
  }
  return {
    label: '',
    icon: props.icon,
    tip: '',
    style: undefined,
    cls: 'bg-muted text-foreground border-border'
  }
})

const label = computed(() => String(props.label ?? resolved.value.label))
const tip = computed(() => props.tooltip ?? resolved.value.tip)
</script>

<template>
  <Tooltip :disabled="!tip">
    <TooltipTrigger as-child>
      <component
        :is="clickable ? 'button' : 'span'"
        v-bind="attrs"
        :type="clickable ? 'button' : undefined"
        :tabindex="!clickable && tip ? 0 : undefined"
        data-slot="chip"
        :class="
          cn(
            'inline-flex w-fit shrink-0 items-center gap-1 rounded-md border px-2 py-0.5 text-xs font-medium whitespace-nowrap [&>svg]:size-3.5 [&>svg]:shrink-0',
            'focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none',
            clickable && 'transition-[filter] hover:brightness-95 dark:hover:brightness-110',
            resolved.cls,
            props.class
          )
        "
        :style="resolved.style"
      >
        <component
          :is="resolved.icon"
          v-if="resolved.icon"
          aria-hidden="true"
          :class="resolved.spin && 'motion-safe:animate-spin'"
        />
        <slot>{{ label }}</slot>
      </component>
    </TooltipTrigger>
    <TooltipContent v-if="tip" class="max-w-xs">{{ tip }}</TooltipContent>
  </Tooltip>
</template>
