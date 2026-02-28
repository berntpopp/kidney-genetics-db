import { computed, watch } from 'vue'
import { useColorMode } from '@vueuse/core'
import { useTheme } from 'vuetify'

export function useAppTheme() {
  const colorMode = useColorMode({
    attribute: 'class',
    modes: { light: 'light', dark: 'dark' },
    storageKey: 'kgdb-color-mode'
  })
  const vuetifyTheme = useTheme()
  const isDark = computed(() => colorMode.value === 'dark')

  // Sync VueUse colorMode -> Vuetify theme
  watch(
    isDark,
    dark => {
      vuetifyTheme.global.name.value = dark ? 'dark' : 'light'
    },
    { immediate: true }
  )

  // Sync Vuetify -> html class (for shadcn-vue)
  watch(
    () => vuetifyTheme.global.current.value.dark,
    dark => {
      document.documentElement.classList.toggle('dark', dark)
    },
    { immediate: true }
  )

  const toggleTheme = () => {
    colorMode.value = isDark.value ? 'light' : 'dark'
  }

  return { isDark, toggleTheme, colorMode }
}
