import { ref } from 'vue'

/** True while the browser prints, so collapsed content (cards, "Show all" lists) can render expanded */
export const isPrinting = ref(false)

if (typeof window !== 'undefined') {
  window.addEventListener('beforeprint', () => (isPrinting.value = true))
  window.addEventListener('afterprint', () => (isPrinting.value = false))
}
