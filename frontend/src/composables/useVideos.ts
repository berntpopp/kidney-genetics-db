/**
 * Shared state of the optional video bundle.
 *
 * Module-level instead of a Pinia store: PageHeader and the footer read it on every view,
 * including in tests that mount views without Pinia. Loaded once, client-side only.
 */
import { ref, shallowRef } from 'vue'
import { fetchVideoManifest, type VideoManifest } from '@/api/videos'

const manifest = shallowRef<VideoManifest | null>(null)
/** loading until the first load settles; absent hides every video entry point */
const status = ref<'loading' | 'ready' | 'absent'>('loading')
let pending: Promise<void> | null = null

export function loadVideos(): Promise<void> {
  pending ??= fetchVideoManifest().then(m => {
    manifest.value = m
    status.value = m ? 'ready' : 'absent'
  })
  return pending
}

export function useVideos() {
  return { manifest, status }
}

/** Test hook: forget the loaded manifest */
export function resetVideos() {
  manifest.value = null
  status.value = 'loading'
  pending = null
}
