import { computed } from 'vue'
import { useColorMode } from '@vueuse/core'

export function useAppTheme() {
  const mode = useColorMode({
    storageKey: 'kgdb-color-mode',
    initialValue: 'auto',
  })

  const isDark = computed(() => mode.value === 'dark')

  function toggleTheme() {
    mode.value = isDark.value ? 'light' : 'dark'
  }

  return { isDark, mode, toggleTheme }
}
