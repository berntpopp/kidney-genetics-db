/* global Response -- browser global; the shared ESLint globals list predates it */
import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  durationMinutes,
  fetchVideoManifest,
  formatDuration,
  isoDuration,
  parseVideoManifest,
  videoAsset,
  videoMatchesRoute
} from '@/api/videos'
import { manifestJson, video } from '@/test/videoFixtures'

describe('parseVideoManifest', () => {
  it('keeps valid entries and drops malformed ones', () => {
    const m = parseVideoManifest(
      manifestJson([
        video('01-ok'),
        video('02-path', { video: '../secret.mp4' }),
        video('03-url', { poster: 'https://evil.example/x.jpg' }),
        video('04-no-captions', { captions: undefined }),
        video('05-zero', { duration: 0 }),
        video('Bad Id'),
        video('01-ok', { title: 'duplicate' }),
        'not an object',
        null
      ])
    )
    expect(m?.videos.map(v => v.id)).toEqual(['01-ok'])
    expect(m?.videos[0]?.title).toBe('Title 01-ok')
  })

  it('drops non-path page entries and defaults the optional fields', () => {
    const m = parseVideoManifest(
      manifestJson([video('01', { pages: ['/genes', 'genes', 3], width: 'x', language: 7 })])
    )
    expect(m?.videos[0]).toMatchObject({ pages: ['/genes'], width: 1920, language: 'en' })
  })

  it('returns null for an unknown schema, a bad shape or no usable video', () => {
    expect(parseVideoManifest({ ...manifestJson(), schema: 2 })).toBeNull()
    expect(parseVideoManifest({ ...manifestJson(), videos: 'x' })).toBeNull()
    expect(parseVideoManifest(manifestJson([video('01', { title: '' })]))).toBeNull()
    expect(parseVideoManifest('<!doctype html>')).toBeNull()
    expect(parseVideoManifest(null)).toBeNull()
  })
})

describe('fetchVideoManifest', () => {
  afterEach(() => vi.unstubAllGlobals())
  const respond = (status: number, body: unknown, type = 'application/json') =>
    vi.stubGlobal(
      'fetch',
      vi.fn(
        async () =>
          new Response(JSON.stringify(body), { status, headers: { 'content-type': type } })
      )
    )

  it('reads /videos/videos.json without the HTTP cache', async () => {
    respond(200, manifestJson())
    expect((await fetchVideoManifest())?.version).toBe('1.0.0')
    expect(fetch).toHaveBeenCalledWith('/videos/videos.json', { cache: 'no-cache' })
  })

  it('is null (feature hidden) on 404, on an HTML fallback and on network errors', async () => {
    respond(404, { detail: 'Not Found' })
    expect(await fetchVideoManifest()).toBeNull()
    respond(200, manifestJson(), 'text/html')
    expect(await fetchVideoManifest()).toBeNull()
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('offline')))
    expect(await fetchVideoManifest()).toBeNull()
  })
})

describe('video helpers', () => {
  const m = parseVideoManifest(manifestJson())!
  const v = m.videos[0]!

  it('versions asset URLs', () => {
    expect(videoAsset(m, v.video)).toBe('/videos/01-evidence-score.mp4?v=1.0.0')
  })

  it('matches route patterns and exact paths only', () => {
    expect(videoMatchesRoute(v, '/genes/PKD1', '/genes/:symbol')).toBe(true)
    expect(videoMatchesRoute(v, '/about', '/about')).toBe(true)
    expect(videoMatchesRoute(v, '/genes/PKD1/structure', '/genes/:symbol/structure')).toBe(false)
    expect(videoMatchesRoute(v, '/genes', '/genes')).toBe(false)
  })

  it('formats durations', () => {
    expect(formatDuration(199.8)).toBe('3:20')
    expect(formatDuration(59.6)).toBe('1:00')
    expect(isoDuration(199.8)).toBe('PT3M20S')
    expect(durationMinutes(20)).toBe(1)
    expect(durationMinutes(199.8)).toBe(3)
  })
})
