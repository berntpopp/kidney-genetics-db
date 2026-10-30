/**
 * DiagnosticPanels provenance: the laboratory registry (scrape date, lab and panel links)
 * shared by the card's stat row and its body. The registry is an enhancement; while it loads
 * or after it fails, the card shows the gene's own labs and panels without links or dates.
 */
import { onMounted, ref, shallowRef } from 'vue'
import { datasourceApi, type DiagnosticPanelsProvider } from '@/api/datasources'
import { isRealProvider } from './evidenceMeta'

type Data = Record<string, any>

export type RegistryState = 'loading' | 'ready' | 'error'

/** Registry keyed by provider_name; `enabled` keeps other sources from requesting it */
export function useProviderRegistry(enabled: () => boolean = () => true) {
  const byName = shallowRef(new Map<string, DiagnosticPanelsProvider>())
  const state = ref<RegistryState>('loading')
  onMounted(async () => {
    if (!enabled()) return
    try {
      const providers = await datasourceApi.getDiagnosticPanelsProviders()
      byName.value = new Map(providers.map(p => [p.provider_name, p]))
      state.value = 'ready'
    } catch {
      state.value = 'error'
    }
  })
  return { byName, state }
}

/** The gene's real laboratories (raw provider keys), sorted by display name */
export const geneLabs = (d: Data): string[] =>
  [...new Set<string>(d.provider_panels ? Object.keys(d.provider_panels) : (d.providers ?? []))]
    .filter(isRealProvider)
    .sort((a, b) => labName(a).localeCompare(labName(b)))

export const labName = (provider: string) => provider.replace(/_/g, ' ')

const toDate = (iso: string | null | undefined) => {
  const date = iso ? new Date(iso) : null
  return date && !Number.isNaN(date.getTime()) ? date : null
}

/** "24 Aug 2025" in UTC, so a scrape date reads the same in every time zone */
export const formatDay = (date: Date) =>
  date.toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    timeZone: 'UTC'
  })

export const scrapedAt = (entry: DiagnosticPanelsProvider | undefined) => toDate(entry?.scraped_at)

/** Captured more than 12 months before now */
export const isOverAYearOld = (date: Date, now = new Date()) => {
  const cutoff = new Date(now)
  cutoff.setUTCFullYear(cutoff.getUTCFullYear() - 1)
  return date < cutoff
}

/** Oldest and newest scrape among the given registry entries */
export function captureRange(entries: (DiagnosticPanelsProvider | undefined)[]) {
  const dates = entries
    .map(scrapedAt)
    .filter((d): d is Date => !!d)
    .sort((a, b) => a.getTime() - b.getTime())
  if (!dates.length) return null
  const oldest = dates[0]!
  const newest = dates[dates.length - 1]!
  return formatDay(oldest) === formatDay(newest) ? { oldest } : { oldest, newest }
}

/** Footer provenance: distinct scraper versions and the latest upload into KGDB */
export function uploadProvenance(entries: (DiagnosticPanelsProvider | undefined)[]) {
  const present = entries.filter((e): e is DiagnosticPanelsProvider => !!e)
  const versions = [
    ...new Set(present.map(e => e.scraper_version).filter((v): v is string => !!v))
  ].sort()
  const uploads = present
    .map(e => toDate(e.uploaded_at))
    .filter((d): d is Date => !!d)
    .sort((a, b) => b.getTime() - a.getTime())
  return { versions, uploaded: uploads[0] ?? null }
}
