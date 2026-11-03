/**
 * Educational video bundle (/videos/videos.json).
 *
 * The bundle is mounted into the frontend container at deploy time; it is not part of the
 * build. A missing or malformed manifest resolves to null and the feature stays hidden.
 */

export interface Video {
  id: string
  title: string
  summary: string
  /** Route patterns ("/genes/:symbol") or exact paths this video introduces */
  pages: string[]
  /** Seconds */
  duration: number
  video: string
  captions: string
  poster: string
  width: number
  height: number
  language: string
  /** ISO date of the screen captures */
  captured?: string
  /** Provenance of the captures, e.g. the site version and data date */
  note?: string
}

export interface VideoManifest {
  version: string
  license: string
  videos: Video[]
}

export const VIDEOS_BASE = '/videos/'

const ID = /^[a-z0-9][a-z0-9-]*$/
// Plain file names inside /videos/ only: no paths, no "..", no URLs
const file = (ext: string) => new RegExp(`^[A-Za-z0-9][A-Za-z0-9._-]*\\.(${ext})$`)
const MP4 = file('mp4')
const VTT = file('vtt')
const IMAGE = file('jpg|jpeg|png|webp')

const str = (v: unknown): v is string => typeof v === 'string' && v.trim() !== ''
const pos = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v) && v > 0

function parseVideo(raw: unknown): Video | null {
  if (!raw || typeof raw !== 'object') return null
  const v = raw as Record<string, unknown>
  if (!str(v.id) || !ID.test(v.id) || !str(v.title) || !str(v.summary) || !pos(v.duration)) {
    return null
  }
  if (!str(v.video) || !MP4.test(v.video) || !str(v.captions) || !VTT.test(v.captions)) return null
  if (!str(v.poster) || !IMAGE.test(v.poster)) return null
  const pages = Array.isArray(v.pages)
    ? v.pages.filter((p): p is string => str(p) && p.startsWith('/'))
    : []
  return {
    id: v.id,
    title: v.title.trim(),
    summary: v.summary.trim(),
    pages,
    duration: v.duration,
    video: v.video,
    captions: v.captions,
    poster: v.poster,
    width: pos(v.width) ? v.width : 1920,
    height: pos(v.height) ? v.height : 1080,
    language: str(v.language) ? v.language : 'en',
    ...(str(v.captured) ? { captured: v.captured } : {}),
    ...(str(v.note) ? { note: v.note } : {})
  }
}

/** Validate the manifest: malformed entries are dropped; null when nothing usable is left */
export function parseVideoManifest(raw: unknown): VideoManifest | null {
  if (!raw || typeof raw !== 'object') return null
  const m = raw as Record<string, unknown>
  if (m.schema !== 1 || !str(m.version) || !Array.isArray(m.videos)) return null
  const seen = new Set<string>()
  const videos = m.videos
    .map(parseVideo)
    .filter((v): v is Video => v !== null && !seen.has(v.id) && !!seen.add(v.id))
  return videos.length
    ? { version: m.version, license: str(m.license) ? m.license : '', videos }
    : null
}

/** Fetch and validate the manifest; null when absent (404), unreachable or invalid */
export async function fetchVideoManifest(): Promise<VideoManifest | null> {
  try {
    const res = await fetch(`${VIDEOS_BASE}videos.json`, { cache: 'no-cache' })
    // Without the bundle a dev server may answer with the SPA's HTML; only JSON counts
    if (!res.ok || !res.headers.get('content-type')?.includes('json')) return null
    return parseVideoManifest(await res.json())
  } catch {
    return null
  }
}

/** URL of a bundle file; file names are not content-hashed, so the version busts caches */
export const videoAsset = (manifest: VideoManifest, name: string) =>
  `${VIDEOS_BASE}${name}?v=${encodeURIComponent(manifest.version)}`

/** Does a video belong to this page? Matches the route pattern or the exact path */
export const videoMatchesRoute = (video: Video, path: string, pattern: string | undefined) =>
  video.pages.some(p => p === pattern || p === path)

/** 199.8 -> "3:20" */
export function formatDuration(seconds: number): string {
  const s = Math.round(seconds)
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`
}

/** 199.8 -> "PT3M20S" (schema.org duration) */
export function isoDuration(seconds: number): string {
  const s = Math.round(seconds)
  return `PT${Math.floor(s / 60)}M${s % 60}S`
}

/** Whole minutes for "3-min intro", never 0 */
export const durationMinutes = (seconds: number) => Math.max(1, Math.round(seconds / 60))

/** Licence page for the licences the bundle uses */
export const LICENSE_URLS: Record<string, string> = {
  'CC BY 4.0': 'https://creativecommons.org/licenses/by/4.0/'
}
