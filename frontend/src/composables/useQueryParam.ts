/**
 * Two-way bind one URL query parameter, so view settings are shareable links.
 * Defaults are left out of the URL; writes use router.replace unless `push` is set.
 */
import { computed } from 'vue'
import type { WritableComputedRef } from 'vue'
import { useRoute, useRouter } from 'vue-router'

/** `push` adds a history entry (tabs), so Back returns to the previous view */
export function useQueryParam(
  key: string,
  fallback = '',
  { push = false } = {}
): WritableComputedRef<string> {
  const route = useRoute()
  const router = useRouter()
  return computed({
    get: () => {
      const v = route.query[key]
      return (Array.isArray(v) ? v[0] : v) ?? fallback
    },
    set: value => {
      const query = { ...route.query }
      if (value === fallback || value === '') delete query[key]
      else query[key] = value
      ;(push ? router.push : router.replace)({ path: route.path, query })
    }
  })
}

/** Comma-separated list parameter, keeping only `allowed` values when given. */
export function useQueryList(key: string, allowed?: () => string[]): WritableComputedRef<string[]> {
  const raw = useQueryParam(key)
  return computed({
    get: () => {
      const list = raw.value.split(',').filter(Boolean)
      const ok = allowed?.()
      return ok ? list.filter(v => ok.includes(v)) : list
    },
    set: list => {
      raw.value = list.join(',')
    }
  })
}
