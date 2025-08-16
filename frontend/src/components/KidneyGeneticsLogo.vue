<template>
  <div
    class="kidney-genetics-logo"
    :class="[
      `logo--${variant}`,
      `logo--${sizeClass}`,
      {
        'logo--animated': animated && !reducedMotion,
        'logo--interactive': interactive
      }
    ]"
    role="img"
    :aria-label="ariaLabel"
    :style="{ width: computedSize + 'px', height: computedSize + 'px' }"
    @click="$emit('click', $event)"
  >
    <!-- Simple nephrology logo -->
    <div v-if="variant === 'full'" class="logo-single">
      <img
        :src="nephrologyIcon"
        alt="Nephrology"
        class="nephrology-icon"
        :style="{ ...iconStyle, width: '100%', height: '100%' }"
      />
    </div>

    <!-- DNA-only variant -->
    <div v-else-if="variant === 'dna'" class="logo-single">
      <img
        :src="geneticsIcon"
        alt="Genetics"
        class="genetics-icon"
        :style="{ ...iconStyle, width: '100%', height: '100%' }"
      />
    </div>

    <!-- Kidney-only variant -->
    <div v-else-if="variant === 'kidneys'" class="logo-single">
      <img
        :src="nephrologyIcon"
        alt="Nephrology"
        class="nephrology-icon"
        :style="{ ...iconStyle, width: '100%', height: '100%' }"
      />
    </div>

    <!-- Icon variant (smaller stacked) -->
    <div v-else class="logo-stack">
      <img :src="nephrologyIcon" alt="Nephrology" class="nephrology-icon" :style="iconStyle" />
      <img :src="geneticsIcon" alt="Genetics" class="genetics-icon" :style="iconStyle" />
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { useTheme } from 'vuetify'
import nephrologyIcon from '@/assets/nephrology.svg'
import geneticsIcon from '@/assets/genetics.svg'

const props = defineProps({
  size: {
    type: [Number, String],
    default: 64,
    validator: val => {
      const num = Number(val)
      return num >= 16 && num <= 512
    }
  },
  variant: {
    type: String,
    default: 'full',
    validator: val => ['full', 'icon', 'dna', 'kidneys'].includes(val)
  },
  animated: {
    type: Boolean,
    default: true
  },
  interactive: {
    type: Boolean,
    default: false
  },
  monochrome: {
    type: Boolean,
    default: false
  },
  themeOverride: {
    type: String,
    default: 'auto',
    validator: val => ['auto', 'light', 'dark'].includes(val)
  }
})

defineEmits(['click'])

const theme = useTheme()
const reducedMotion = ref(false)

// Check for reduced motion preference
onMounted(() => {
  const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)')
  reducedMotion.value = mediaQuery.matches

  const handleChange = e => {
    reducedMotion.value = e.matches
  }

  mediaQuery.addEventListener('change', handleChange)

  onUnmounted(() => {
    mediaQuery.removeEventListener('change', handleChange)
  })
})

// Computed properties for sizing
const computedSize = computed(() => Number(props.size))

const sizeClass = computed(() => {
  const size = computedSize.value
  if (size <= 24) return 'xs'
  if (size <= 40) return 'sm'
  if (size <= 64) return 'md'
  if (size <= 128) return 'lg'
  return 'xl'
})

// Theme-aware colors
const isDark = computed(() => {
  if (props.themeOverride === 'light') return false
  if (props.themeOverride === 'dark') return true
  return theme.current.value.dark
})

const iconStyle = computed(() => ({
  width: '50%',
  height: '50%',
  filter: props.monochrome
    ? `brightness(${isDark.value ? '0.9' : '0.4'})`
    : isDark.value
      ? 'brightness(1.1) contrast(1.1)'
      : 'brightness(0.8) contrast(1.2)'
}))

const ariaLabel = computed(() => {
  const variants = {
    full: 'Kidney Genetics Database logo',
    icon: 'Kidney Genetics Database icon',
    dna: 'DNA helix icon',
    kidneys: 'Nephrology kidneys icon'
  }
  return variants[props.variant]
})
</script>

<style scoped>
.kidney-genetics-logo {
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.2s ease;
}

.logo-stack {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  gap: 4px;
}

.logo-single {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
}

.nephrology-icon,
.genetics-icon {
  display: block;
  transition: transform 0.3s ease;
}

/* Interactive states */
.logo--interactive {
  cursor: pointer;
}

.logo--interactive:hover {
  transform: scale(1.05);
}

.logo--interactive:active {
  transform: scale(0.98);
}

/* Animations */
.logo--animated .nephrology-icon {
  animation: gentle-pulse 3s ease-in-out infinite;
}

.logo--animated .genetics-icon {
  animation: gentle-pulse 3s ease-in-out infinite;
  animation-delay: 1.5s;
}

@keyframes gentle-pulse {
  0%,
  100% {
    opacity: 0.8;
    transform: scale(1);
  }
  50% {
    opacity: 1;
    transform: scale(1.02);
  }
}

/* Size-specific adjustments */
.logo--xs .logo-stack {
  gap: 2px;
}

.logo--sm .logo-stack {
  gap: 3px;
}

.logo--lg .logo-stack,
.logo--xl .logo-stack {
  gap: 6px;
}

/* Print styles */
@media print {
  .kidney-genetics-logo {
    animation: none !important;
  }

  .nephrology-icon,
  .genetics-icon {
    animation: none !important;
  }
}

/* High contrast mode support */
@media (prefers-contrast: high) {
  .nephrology-icon,
  .genetics-icon {
    filter: contrast(1.5) !important;
  }
}
</style>
