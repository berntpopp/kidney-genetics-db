/**
 * SEO meta tag composable using @unhead/vue
 *
 * Sets title, description, canonical URL, Open Graph, Twitter Cards,
 * and robots directives for each page.
 */

import { computed, type MaybeRefOrGetter, toValue } from 'vue'
import { useHead } from '@unhead/vue'

const SITE_URL = (import.meta.env.VITE_SITE_URL as string) || 'https://kidney-genetics.org'
const SITE_NAME = 'Kidney Genetics Database'
const DEFAULT_OG_IMAGE = `${SITE_URL}/icon-512.png`

export interface SeoMetaOptions {
  /** Page title — will be suffixed with " | KGDB" */
  title: MaybeRefOrGetter<string>
  /** Meta description */
  description: MaybeRefOrGetter<string>
  /** Canonical path (e.g. "/genes/PKD1"). Omit for current route. */
  canonicalPath?: MaybeRefOrGetter<string>
  /** Set true to add noindex robots tag */
  noindex?: MaybeRefOrGetter<boolean>
  /** Override OG image URL */
  ogImage?: MaybeRefOrGetter<string>
}

export function useSeoMeta(options: SeoMetaOptions) {
  const fullTitle = computed(() => {
    const t = toValue(options.title)
    return t ? `${t} | KGDB` : 'KGDB - Kidney Genetics Database'
  })

  const desc = computed(() => toValue(options.description))
  const canonical = computed(() => {
    const p = options.canonicalPath ? toValue(options.canonicalPath) : undefined
    return p ? `${SITE_URL}${p}` : undefined
  })
  const robots = computed(() => (toValue(options.noindex) ? 'noindex, nofollow' : undefined))
  const ogImage = computed(() => (options.ogImage ? toValue(options.ogImage) : DEFAULT_OG_IMAGE))

  useHead(
    computed(() => ({
      title: fullTitle.value,
      meta: [
        { name: 'description', content: desc.value },
        // Open Graph
        { property: 'og:title', content: fullTitle.value },
        { property: 'og:description', content: desc.value },
        { property: 'og:image', content: ogImage.value },
        { property: 'og:type', content: 'website' },
        { property: 'og:site_name', content: SITE_NAME },
        ...(canonical.value ? [{ property: 'og:url', content: canonical.value }] : []),
        // Twitter Card
        { name: 'twitter:card', content: 'summary' },
        { name: 'twitter:title', content: fullTitle.value },
        { name: 'twitter:description', content: desc.value },
        { name: 'twitter:image', content: ogImage.value },
        // Robots (only when noindex)
        ...(robots.value ? [{ name: 'robots', content: robots.value }] : [])
      ],
      link: canonical.value ? [{ rel: 'canonical', href: canonical.value }] : []
    }))
  )
}
