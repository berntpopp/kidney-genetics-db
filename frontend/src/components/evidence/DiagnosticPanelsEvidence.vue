<template>
  <section v-if="labs.length" aria-label="Laboratories and their panels">
    <ul class="space-y-3 text-sm">
      <li v-for="lab in visibleLabs" :key="lab.key" data-testid="lab">
        <div class="flex flex-wrap items-baseline gap-x-3 gap-y-1">
          <a
            v-if="lab.entry?.main_url"
            :href="lab.entry.main_url"
            target="_blank"
            rel="noopener noreferrer"
            class="rounded-sm font-medium text-foreground underline-offset-4 hover:underline focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
            >{{ lab.name }}<span class="sr-only"> (opens in a new tab)</span></a
          >
          <span v-else class="font-medium text-foreground">{{ lab.name }}</span>
          <!-- Reserved while the registry loads so the date does not push the row -->
          <span
            v-if="lab.date || registry.state.value === 'loading'"
            class="ml-auto inline-flex min-w-24 items-center justify-end gap-2 text-xs text-muted-foreground tabular-nums"
          >
            <StatusBadge
              v-if="lab.stale"
              status="stale"
              label="Over a year old"
              :tooltip="`Panel list captured ${formatDay(lab.date)}, more than 12 months ago`"
            />
            <time v-if="lab.date" :datetime="lab.date.toISOString()">{{
              formatDay(lab.date)
            }}</time>
          </span>
        </div>
        <ul class="mt-1 space-y-1 pl-4">
          <li v-for="panel in shownPanels(lab)" :key="panel.name">
            <a
              v-if="panel.url"
              :href="panel.url"
              target="_blank"
              rel="noopener noreferrer"
              class="rounded-sm text-foreground underline-offset-4 hover:underline focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
              >{{ panel.name }}<span class="sr-only"> (opens in a new tab)</span></a
            >
            <span v-else class="text-foreground">{{ panel.name }}</span>
          </li>
        </ul>
        <Button
          v-if="lab.panels.length > MAX"
          variant="link"
          size="sm"
          class="ml-4 h-auto px-0"
          :aria-expanded="openLabs.has(lab.key)"
          @click="toggleLab(lab.key)"
        >
          {{ openLabs.has(lab.key) ? 'Show fewer' : `+${lab.panels.length - MAX} more` }}
        </Button>
      </li>
    </ul>
    <Button
      v-if="labs.length > MAX"
      variant="link"
      size="sm"
      class="mt-1 h-auto px-0"
      :aria-expanded="allLabs"
      @click="allLabs = !allLabs"
    >
      {{ allLabs ? 'Show fewer' : `Show all ${labs.length} laboratories` }}
    </Button>
  </section>

  <template v-else>
    <EvidenceList
      v-for="group in legacyGroups"
      :key="group.title"
      :title="group.title"
      :items="group.items"
      :max="8"
    >
      <template #default="{ item }">
        <span class="text-foreground">{{ item }}</span>
      </template>
    </EvidenceList>
  </template>

  <p
    class="flex flex-wrap items-baseline gap-x-1.5 gap-y-1 text-xs text-muted-foreground"
    data-testid="panels-provenance"
  >
    <span>Panel lists scraped from laboratory websites</span>
    <template v-if="provenance.versions.length">
      <span aria-hidden="true">·</span>
      <span
        >KGDB scraper <span class="font-mono">{{ provenance.versions.join(', ') }}</span></span
      >
    </template>
    <template v-if="provenance.uploaded">
      <span aria-hidden="true">·</span>
      <span
        >uploaded
        <time :datetime="provenance.uploaded.toISOString()">{{
          formatDay(provenance.uploaded)
        }}</time></span
      >
    </template>
    <RouterLink
      :to="{ name: 'data-sources' }"
      class="ml-auto rounded-sm font-medium text-primary underline-offset-4 hover:underline focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
      >Sources &amp; method</RouterLink
    >
  </p>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { Button } from '@/components/ui/button'
import { StatusBadge } from '@/components/shared'
import EvidenceList from './EvidenceList.vue'
import { isRealProvider } from './evidenceMeta'
import {
  formatDay,
  geneLabs,
  isOverAYearOld,
  labName,
  scrapedAt,
  uploadProvenance,
  useProviderRegistry
} from './diagnosticPanels'

const props = defineProps({
  evidenceData: { type: Object, required: true },
  sourceName: { type: String, default: 'DiagnosticPanels' }
})

const MAX = 3

const registry = useProviderRegistry()
const sorted = list => [...new Set(list ?? [])].sort((a, b) => a.localeCompare(b))
const data = computed(() => props.evidenceData ?? {})
const entries = computed(() => geneLabs(data.value).map(p => registry.byName.value.get(p)))

// Grouped by laboratory when the evidence lists panels per lab; ingestion labels such as
// "Seeded from 9 files" are not providers and stay hidden
const labs = computed(() =>
  data.value.provider_panels
    ? geneLabs(data.value).map((key, i) => {
        const entry = entries.value[i]
        const urls = new Map((entry?.panels ?? []).map(p => [p.name.trim(), p.url]))
        const date = scrapedAt(entry)
        return {
          key,
          name: labName(key),
          entry,
          date,
          stale: !!date && isOverAYearOld(date),
          panels: sorted(data.value.provider_panels[key]).map(name => ({
            name,
            url: urls.get(name.trim()) ?? null
          }))
        }
      })
    : []
)

const allLabs = ref(false)
const visibleLabs = computed(() => (allLabs.value ? labs.value : labs.value.slice(0, MAX)))
const openLabs = reactive(new Set())
const toggleLab = key => (openLabs.has(key) ? openLabs.delete(key) : openLabs.add(key))
const shownPanels = lab => (openLabs.has(lab.key) ? lab.panels : lab.panels.slice(0, MAX))

// Legacy evidence lists labs per gene, not per panel, so name them beside the panels
const legacyGroups = computed(() => {
  const d = data.value
  const panels = d.provider_panels ? Object.values(d.provider_panels).flat() : d.panels
  const names = (d.provider_panels ? Object.keys(d.provider_panels) : (d.providers ?? []))
    .filter(isRealProvider)
    .map(labName)
  return [
    { title: 'Panels', items: sorted(panels) },
    { title: names.length === 1 ? 'Laboratory' : 'Laboratories', items: sorted(names) }
  ]
})

const provenance = computed(() => uploadProvenance(entries.value))
</script>
