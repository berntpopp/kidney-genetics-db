import { onScopeDispose, ref, shallowRef, watch, type Ref } from 'vue'
import { geneApi } from '@/api/genes'
import type { PositionStatistics } from '@/types/positionStats'

type Status = 'idle' | 'loading' | 'ready' | 'error' | 'withheld' | 'too-few'

/** Variant-position statistics from the backend; an empty symbol keeps it idle (lazy trigger). */
export function usePositionStats(input: { symbol: Ref<string> }) {
  const status = ref<Status>('idle')
  const message = ref('')
  const variantSet = shallowRef<PositionStatistics['variantSet'] | null>(null)
  const linear = shallowRef<PositionStatistics['linear']>(null)
  const spatial = shallowRef<PositionStatistics['spatial']>(null)
  const spatialMessage = ref('')
  const minStars = ref(1)

  let gen = 0
  let disposed = false

  async function run() {
    const my = ++gen
    const symbol = input.symbol.value
    spatial.value = linear.value = variantSet.value = null
    spatialMessage.value = message.value = ''
    if (!symbol) {
      status.value = 'idle'
      return
    }
    status.value = 'loading'
    try {
      const r = await geneApi.getPositionStatistics(symbol, minStars.value)
      if (disposed || my !== gen) return
      variantSet.value = r.variantSet
      linear.value = r.linear
      spatial.value = r.spatial
      spatialMessage.value = r.spatialMessage ?? ''
      message.value = r.message ?? ''
      status.value = r.status
    } catch (e) {
      if (disposed || my !== gen) return
      // The global error handler wraps as {error: {detail}}; plain FastAPI errors use top-level detail
      const data = (
        e as { response?: { data?: { detail?: unknown; error?: { detail?: unknown } } } }
      ).response?.data
      const detail = data?.error?.detail ?? data?.detail
      message.value = typeof detail === 'string' ? detail : 'Could not load statistics'
      status.value = 'error'
    }
  }

  watch([input.symbol, minStars], () => void run(), { immediate: true })
  onScopeDispose(() => {
    disposed = true
  })

  return {
    status,
    message,
    variantSet,
    linear,
    spatial,
    spatialMessage,
    minStars,
    retry: () => void run()
  }
}
