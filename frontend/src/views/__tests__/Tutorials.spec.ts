/* global Response -- browser global; the shared ESLint globals list predates it */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { h, toValue } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter, RouterView } from 'vue-router'
import { TooltipProvider } from '@/components/ui/tooltip'
import { PageHeader } from '@/components/shared'
import Tutorials from '@/views/Tutorials.vue'
import { loadVideos, resetVideos } from '@/composables/useVideos'
import { useJsonLd } from '@/composables/useJsonLd'
import { manifestJson, video } from '@/test/videoFixtures'

vi.mock('@/composables/useSeoMeta', () => ({ useSeoMeta: vi.fn() }))
vi.mock('@/composables/useJsonLd', async importOriginal => ({
  ...(await importOriginal<typeof import('@/composables/useJsonLd')>()),
  useJsonLd: vi.fn()
}))

// A view with a PageHeader, as every public view has
const Page = {
  render: () =>
    h(PageHeader, { title: 'Page' }, { breadcrumb: () => h('nav', { 'aria-label': 'Breadcrumb' }) })
}

const FIXTURE = manifestJson([
  video('01-evidence-score', { pages: ['/genes/:symbol', '/about'] }),
  video('02-gene-browser', { pages: ['/genes'], duration: 117.7 })
])

function serve(body: unknown, status = 200) {
  vi.stubGlobal(
    'fetch',
    vi.fn(
      async () =>
        new Response(JSON.stringify(body), {
          status,
          headers: { 'content-type': 'application/json' }
        })
    )
  )
}

const mounted: Array<{ unmount: () => void }> = []

async function mountAt(path: string) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/tutorials', component: Tutorials },
      { path: '/genes', component: Page },
      { path: '/genes/:symbol', component: Page },
      { path: '/:rest(.*)', component: Page }
    ]
  })
  await router.push(path)
  const wrapper = mount(
    { render: () => h(TooltipProvider, () => h(RouterView)) },
    { global: { plugins: [router] }, attachTo: document.body }
  )
  mounted.push(wrapper)
  await loadVideos()
  await flushPromises()
  return { wrapper, router }
}

beforeEach(() => {
  resetVideos()
  Element.prototype.scrollIntoView = vi.fn() // not implemented by jsdom
})
afterEach(() => {
  vi.unstubAllGlobals()
  mounted.splice(0).forEach(w => w.unmount())
})

describe('Tutorials page', () => {
  it('renders every manifest video with a native, captioned, non-autoplaying player', async () => {
    serve(FIXTURE)
    const { wrapper } = await mountAt('/tutorials')
    const items = wrapper.findAll('nav[aria-label="All tutorials"] li')
    expect(items.map(i => i.find('a').attributes('href'))).toEqual([
      '/tutorials#01-evidence-score',
      '/tutorials#02-gene-browser'
    ])
    expect(items[0]?.text()).toContain('3:20')
    const player = wrapper.get('video')
    expect(player.attributes()).toMatchObject({ preload: 'none', controls: '' })
    expect(player.attributes('autoplay')).toBeUndefined()
    expect(player.attributes('poster')).toBe('/videos/01-evidence-score.jpg?v=1.0.0')
    expect(player.get('track').attributes()).toMatchObject({
      kind: 'captions',
      srclang: 'en',
      default: '',
      src: '/videos/01-evidence-score.vtt?v=1.0.0'
    })
    expect(wrapper.text()).toContain('CC BY 4.0')
  })

  it('opens the deep-linked video and marks it current', async () => {
    serve(FIXTURE)
    const { wrapper } = await mountAt('/tutorials#02-gene-browser')
    expect(wrapper.get('#tutorial-title').text()).toBe('Title 02-gene-browser')
    expect(wrapper.get('[aria-current="true"]').attributes('href')).toBe(
      '/tutorials#02-gene-browser'
    )
    expect(wrapper.find('section[id="02-gene-browser"]').exists()).toBe(true)
    expect(Element.prototype.scrollIntoView).toHaveBeenCalled()
  })

  it('emits one VideoObject per video for search engines', async () => {
    serve(FIXTURE)
    await mountAt('/tutorials')
    const schema = toValue(vi.mocked(useJsonLd).mock.calls.at(-1)![0]) as {
      '@graph': Array<Record<string, unknown>>
    }
    const videos = schema['@graph'].filter(n => n['@type'] === 'VideoObject')
    expect(videos).toHaveLength(2)
    expect(videos[0]).toMatchObject({
      name: 'Title 01-evidence-score',
      duration: 'PT3M20S',
      uploadDate: '2026-11-03',
      license: 'https://creativecommons.org/licenses/by/4.0/'
    })
  })

  it('is a plain Not Found page without the bundle (404)', async () => {
    serve({ detail: 'Not Found' }, 404)
    const { wrapper } = await mountAt('/tutorials')
    expect(wrapper.text()).toContain('Page not found')
    expect(wrapper.find('video').exists()).toBe(false)
  })
})

describe('Contextual intro chip', () => {
  it('appears on pages listed in the video’s pages and opens the player in place', async () => {
    serve(FIXTURE)
    const { wrapper } = await mountAt('/genes/PKD1')
    const chip = wrapper.get('button[aria-haspopup="dialog"]')
    expect(chip.text()).toBe('3-min intro')
    expect(chip.attributes('aria-label')).toBe('Watch the 3-minute intro: Title 01-evidence-score')
    await chip.trigger('click')
    await flushPromises()
    const dialog = document.querySelector('[role="dialog"]')
    expect(dialog?.querySelector('video track[kind="captions"]')).not.toBeNull()
    expect(dialog?.textContent).toContain('All tutorials')
  })

  it('matches the route pattern, not every page', async () => {
    serve(FIXTURE)
    const { wrapper } = await mountAt('/genes')
    expect(wrapper.findAll('button[aria-haspopup="dialog"]').map(b => b.text())).toEqual([
      '2-min intro'
    ])
    resetVideos()
    serve(FIXTURE)
    const other = await mountAt('/dashboard')
    expect(other.wrapper.find('button[aria-haspopup="dialog"]').exists()).toBe(false)
  })

  it('is absent when the bundle is missing', async () => {
    serve({ detail: 'Not Found' }, 404)
    const { wrapper } = await mountAt('/genes/PKD1')
    expect(wrapper.find('button[aria-haspopup="dialog"]').exists()).toBe(false)
  })
})
