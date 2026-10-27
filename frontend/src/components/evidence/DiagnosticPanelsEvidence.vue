<template>
  <EvidenceList
    v-for="group in groups"
    :key="group.title"
    :title="group.title"
    :items="group.panels"
    :max="8"
  >
    <template #default="{ item }">
      <span class="text-foreground">{{ item }}</span>
    </template>
  </EvidenceList>
</template>

<script setup>
import { computed } from 'vue'
import EvidenceList from './EvidenceList.vue'
import { isRealProvider } from './evidenceMeta'

const props = defineProps({
  evidenceData: { type: Object, required: true },
  sourceName: { type: String, default: 'DiagnosticPanels' }
})

const sorted = list => [...new Set(list ?? [])].sort((a, b) => a.localeCompare(b))

// Group by laboratory when the data names real labs; ingestion labels such as
// "Seeded from 9 files" are not providers and are hidden (audit gene-diagnostic-panels-provider-lost)
const groups = computed(() => {
  const d = props.evidenceData ?? {}
  const byProvider = Object.entries(d.provider_panels ?? {}).filter(([p]) => isRealProvider(p))
  if (byProvider.length > 1)
    return byProvider
      .map(([provider, panels]) => ({ title: provider.replace(/_/g, ' '), panels: sorted(panels) }))
      .sort((a, b) => a.title.localeCompare(b.title))
  const panels = d.provider_panels ? Object.values(d.provider_panels).flat() : d.panels
  // Stored evidence lists labs per gene, not per panel, so name them beside the panels
  const labs = (d.provider_panels ? Object.keys(d.provider_panels) : (d.providers ?? []))
    .filter(isRealProvider)
    .map(p => p.replace(/_/g, ' '))
  return [
    { title: 'Panels', panels: sorted(panels) },
    { title: labs.length === 1 ? 'Laboratory' : 'Laboratories', panels: sorted(labs) }
  ]
})
</script>
