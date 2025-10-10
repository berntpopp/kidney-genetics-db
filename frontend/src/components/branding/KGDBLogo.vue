<template>
  <div
    class="kgdb-logo"
    :class="logoClasses"
    :style="logoStyles"
    role="img"
    :aria-label="ariaLabel"
    :tabindex="interactive ? 0 : -1"
    @click="handleClick"
    @keypress.enter="handleClick"
  >
    <!-- Icon-only variant -->
    <div v-if="variant === 'icon-only'" class="kgdb-logo__icon-only">
      <img :src="logoSrc" :alt="alt" class="kgdb-logo__image" />
    </div>

    <!-- With-text variant (horizontal layout) -->
    <div
      v-else-if="variant === 'with-text' && textLayout === 'horizontal'"
      class="kgdb-logo__with-text-horizontal"
    >
      <img :src="logoSrc" :alt="alt" class="kgdb-logo__image" />
      <div class="kgdb-logo__text">
        <span class="kgdb-logo__text-line kgdb-logo__text-primary">Kidney-Genetics</span>
        <span class="kgdb-logo__text-line kgdb-logo__text-secondary">Database</span>
      </div>
    </div>

    <!-- With-text variant (vertical layout for hero) -->
    <div
      v-else-if="variant === 'with-text' && textLayout === 'vertical'"
      class="kgdb-logo__with-text-vertical"
    >
      <img :src="logoSrc" :alt="alt" class="kgdb-logo__image" />
      <div class="kgdb-logo__text">
        <span class="kgdb-logo__text-line kgdb-logo__text-primary">Kidney-Genetics</span>
        <span class="kgdb-logo__text-line kgdb-logo__text-secondary">Database</span>
      </div>
    </div>

    <!-- Text-only variant (rarely used) -->
    <div v-else-if="variant === 'text-only'" class="kgdb-logo__text-only">
      <span class="kgdb-logo__text-line kgdb-logo__text-primary">Kidney-Genetics</span>
      <span class="kgdb-logo__text-line kgdb-logo__text-secondary">Database</span>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { useTheme } from 'vuetify'

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
    default: 'icon-only',
    validator: val => ['icon-only', 'with-text', 'text-only'].includes(val)
  },
  textLayout: {
    type: String,
    default: 'horizontal',
    validator: val => ['horizontal', 'vertical'].includes(val)
  },
  animated: {
    type: Boolean,
    default: true
  },
  interactive: {
    type: Boolean,
    default: false
  },
  breathing: {
    type: Boolean,
    default: false
  },
  monochrome: {
    type: Boolean,
    default: false
  },
  customColor: {
    type: String,
    default: null
  },
  alt: {
    type: String,
    default: 'KGDB Logo'
  }
})

const emit = defineEmits(['click'])

const theme = useTheme()
const reducedMotion = ref(false)

// Logo source - use the KGDB_logo.svg
const logoSrc = '/KGDB_logo.svg'

// Detect prefers-reduced-motion preference
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

// Computed size in pixels
const computedSize = computed(() => Number(props.size))

// Size class for responsive adjustments
const sizeClass = computed(() => {
  const size = computedSize.value
  if (size <= 24) return 'xs'
  if (size <= 40) return 'sm'
  if (size <= 64) return 'md'
  if (size <= 128) return 'lg'
  return 'xl'
})

// Theme-aware dark mode detection
const isDark = computed(() => theme.current.value.dark)

// Logo classes for styling
const logoClasses = computed(() => ({
  'kgdb-logo--animated': props.animated && !reducedMotion.value,
  'kgdb-logo--interactive': props.interactive,
  'kgdb-logo--breathing': props.breathing && !reducedMotion.value,
  'kgdb-logo--monochrome': props.monochrome,
  [`kgdb-logo--${props.variant}`]: true,
  [`kgdb-logo--${sizeClass.value}`]: true,
  'kgdb-logo--dark': isDark.value
}))

// Dynamic styles
const logoStyles = computed(() => ({
  '--logo-size': `${computedSize.value}px`,
  '--logo-text-size': `${Math.max(12, computedSize.value * 0.18)}px`,
  '--kidney-color': props.customColor || '#489c9e',
  '--kidney-shadow': props.customColor ? `${props.customColor}4d` : 'rgba(72, 156, 158, 0.3)'
}))

// Accessibility label
const ariaLabel = computed(() => {
  const variants = {
    'icon-only': 'Kidney Genetics Database logo',
    'with-text': 'Kidney Genetics Database - complete logo with text',
    'text-only': 'Kidney Genetics Database text'
  }
  const label = variants[props.variant]
  return props.interactive ? `${label} - click to navigate home` : label
})

// Click handler
const handleClick = event => {
  if (props.interactive) {
    emit('click', event)
  }
}
</script>

<style scoped>
/* Base logo container */
.kgdb-logo {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  position: relative;
  transition: transform 0.2s ease;
}

/* Disable text selection only for the image, not the text */
.kgdb-logo__image {
  user-select: none;
  -webkit-user-select: none;
}

/* Icon-only layout */
.kgdb-logo__icon-only {
  display: flex;
  align-items: center;
  justify-content: center;
  width: var(--logo-size);
  height: var(--logo-size);
}

/* With-text horizontal layout (nav bar) */
.kgdb-logo__with-text-horizontal {
  display: flex;
  align-items: center;
  gap: 4px;
}

.kgdb-logo__with-text-horizontal .kgdb-logo__image {
  width: var(--logo-size);
  height: var(--logo-size);
  flex-shrink: 0;
}

.kgdb-logo__with-text-horizontal .kgdb-logo__text {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0;
  line-height: 1.1;
  text-align: left;
}

/* With-text vertical layout (hero section) */
.kgdb-logo__with-text-vertical {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: calc(var(--logo-size) * 0.2);
}

.kgdb-logo__with-text-vertical .kgdb-logo__image {
  width: var(--logo-size);
  height: var(--logo-size);
}

.kgdb-logo__with-text-vertical .kgdb-logo__text {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 0;
  line-height: 1.2;
}

/* Text-only layout */
.kgdb-logo__text-only {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0;
  line-height: 1.2;
}

/* Logo image styling */
.kgdb-logo__image {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: contain;
  transition:
    transform 0.3s cubic-bezier(0.4, 0, 0.2, 1),
    filter 0.3s ease;
}

/* Text styling */
.kgdb-logo__text {
  font-family:
    'Roboto',
    -apple-system,
    BlinkMacSystemFont,
    sans-serif;
  font-weight: 700;
  font-size: var(--logo-text-size);
  color: rgb(var(--v-theme-on-surface));
  letter-spacing: -0.02em;
}

.kgdb-logo__text-line {
  display: block;
  white-space: nowrap;
}

.kgdb-logo__text-primary {
  /* Kidney-Genetics - full size */
}

.kgdb-logo__text-secondary {
  /* database - lowercase and smaller */
  text-transform: lowercase;
  font-size: 0.75em;
}

/* Interactive states */
.kgdb-logo--interactive {
  cursor: pointer;
  outline: none;
}

.kgdb-logo--interactive:hover .kgdb-logo__image {
  transform: scale(1.05) rotate(-2deg);
}

.kgdb-logo--interactive:active .kgdb-logo__image {
  transform: scale(0.98);
  transition-duration: 0.1s;
}

.kgdb-logo--interactive:focus-visible {
  outline: 2px solid rgb(var(--v-theme-primary));
  outline-offset: 4px;
  border-radius: 8px;
}

/* Load animation */
.kgdb-logo--animated {
  animation: logo-entrance 0.6s cubic-bezier(0.34, 1.56, 0.64, 1);
}

@keyframes logo-entrance {
  0% {
    opacity: 0;
    transform: scale(0.95) translateY(-10px);
  }
  100% {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

/* Breathing animation (idle state) */
.kgdb-logo--breathing .kgdb-logo__image {
  animation: logo-breathe 4s ease-in-out infinite;
}

@keyframes logo-breathe {
  0%,
  100% {
    transform: scale(1);
    filter: drop-shadow(0 0 0px var(--kidney-shadow));
  }
  50% {
    transform: scale(1.02);
    filter: drop-shadow(0 0 8px var(--kidney-shadow));
  }
}

/* Monochrome mode (footer) */
.kgdb-logo--monochrome .kgdb-logo__image {
  filter: grayscale(100%) brightness(0.6) contrast(1.2);
}

.kgdb-logo--monochrome.kgdb-logo--dark .kgdb-logo__image {
  filter: grayscale(100%) brightness(0.8) contrast(1.1);
}

.kgdb-logo--monochrome .kgdb-logo__text {
  opacity: 0.7;
}

/* Size-specific adjustments */
.kgdb-logo--xs .kgdb-logo__text {
  font-size: 10px;
}

.kgdb-logo--sm .kgdb-logo__text {
  font-size: 14px;
}

.kgdb-logo--md .kgdb-logo__text {
  font-size: 24px;
  /* Mobile hero - readable but compact */
}

.kgdb-logo--lg .kgdb-logo__text {
  font-size: 36px;
  /* Tablet hero */
}

.kgdb-logo--xl .kgdb-logo__text {
  font-size: 64px;
  /* Desktop hero - maximum prominence */
}

/* Respect reduced motion preference */
@media (prefers-reduced-motion: reduce) {
  .kgdb-logo,
  .kgdb-logo *,
  .kgdb-logo::before,
  .kgdb-logo::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}

/* Print styles */
@media print {
  .kgdb-logo {
    animation: none !important;
  }

  .kgdb-logo__image {
    animation: none !important;
    filter: none !important;
  }
}

/* High contrast mode support */
@media (prefers-contrast: high) {
  .kgdb-logo__image {
    filter: contrast(1.5) !important;
  }

  .kgdb-logo__text {
    font-weight: 800;
  }
}

/* Dark mode specific adjustments */
.kgdb-logo--dark .kgdb-logo__image {
  filter: brightness(1.1) contrast(1.05);
}

.kgdb-logo--dark.kgdb-logo--monochrome .kgdb-logo__image {
  filter: grayscale(100%) brightness(0.8) contrast(1.1);
}
</style>
