<script setup>
/**
 * ClinVar variant filters shared by the gene-structure and protein-domain plots: one row per
 * dimension (classification, effect) of toggle buttons with a colour key, "All"/"None", and
 * a "Colour by" switch. Colours come from variantColors.ts so they match the ClinVar chips.
 */
import { Palette } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { EFFECTS, SIGNIFICANCE } from './variantColors'

const colorBy = defineModel('colorBy', { type: String, default: 'classification' })
const classifications = defineModel('classifications', { type: Array, default: () => [] })
const effects = defineModel('effects', { type: Array, default: () => [] })

const rows = [
  { key: 'classification', title: 'Classification', options: SIGNIFICANCE, model: classifications },
  { key: 'effect', title: 'Effect', options: EFFECTS, model: effects }
]

const toggle = (model, value) => {
  model.value = model.value.includes(value)
    ? model.value.filter(v => v !== value)
    : [...model.value, value]
}
</script>

<template>
  <div class="space-y-2">
    <div
      v-for="row in rows"
      :key="row.key"
      role="group"
      :aria-label="`${row.title} filter`"
      class="flex flex-wrap items-center gap-1.5"
    >
      <Button
        type="button"
        variant="ghost"
        size="sm"
        class="w-32 justify-start px-2"
        :class="colorBy === row.key ? 'font-semibold text-foreground' : 'text-muted-foreground'"
        :aria-pressed="colorBy === row.key"
        :title="`Colour variants by ${row.title.toLowerCase()}`"
        @click="colorBy = row.key"
      >
        {{ row.title }}
        <Palette v-if="colorBy === row.key" class="text-muted-foreground" aria-hidden="true" />
      </Button>
      <Button
        v-for="(option, value) in row.options"
        :key="value"
        type="button"
        variant="outline"
        size="sm"
        class="h-7 gap-1.5 px-2 text-xs"
        :class="row.model.value.includes(value) ? 'bg-muted font-medium' : 'text-muted-foreground'"
        :aria-pressed="row.model.value.includes(value)"
        :title="option.description"
        @click="toggle(row.model, value)"
      >
        <span
          class="size-2.5 shrink-0 rounded-full border border-border"
          :style="{
            backgroundColor: row.model.value.includes(value) ? option.color : 'transparent'
          }"
          aria-hidden="true"
        />
        {{ option.label }}
      </Button>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        class="h-7 px-2 text-xs"
        @click="row.model.value = Object.keys(row.options)"
      >
        All
      </Button>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        class="h-7 px-2 text-xs"
        @click="row.model.value = []"
      >
        None
      </Button>
    </div>
  </div>
</template>
