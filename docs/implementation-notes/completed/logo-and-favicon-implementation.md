# Logo and Favicon Implementation Plan

**Status**: Active Planning
**Created**: 2025-10-10
**Issue**: #5 - Implement KGDB Logo Component and Professional Favicon System
**Priority**: High (Branding & UX)

## Executive Summary

This document outlines the comprehensive implementation plan for:
1. **New KGDB Logo Component** - A reusable Vue 3 component with smooth animations
2. **Professional Favicon System** - Modern multi-format favicon setup following 2025 best practices
3. **PWA Support** - Complete manifest and icon system for progressive web app functionality

## Current State Analysis

### Existing Logo System
- **Component**: `KidneyGeneticsLogo.vue`
  - Uses separate nephrology.svg and genetics.svg icons
  - Supports variants: full, icon, dna, kidneys
  - Has basic animations (gentle-pulse)
  - Theme-aware (light/dark mode)
  - Accessibility-conscious (prefers-reduced-motion)

### New Assets Available
- **KGDB_logo.svg** (1024×1024px)
  - Clean kidney-shaped icon design
  - Uses brand colors: #489c9e (primary), #327b82 (dark)
  - Optimized SVG structure

- **KGDB_logo_with_letters.svg** (1024×1024px)
  - Logo with KGDB letters (K, G, D, B in corners)
  - Perfect for favicons and app icons
  - Scaled down version: 85% of original with letters overlay

### Current Usage Locations
1. **Home.vue** (line 9): Hero section with full title
   ```vue
   <KidneyGeneticsLogo :size="80" variant="full" :animated="true" />
   <h1>Kidney Genetics Database</h1>
   ```

2. **App.vue** (line 12): Navigation bar
   ```vue
   <KidneyGeneticsLogo :size="40" variant="kidneys" :animated="false" interactive />
   <v-app-bar-title>Kidney Genetics Database</v-app-bar-title>
   ```

3. **App.vue** (line 223): Footer
   ```vue
   <KidneyGeneticsLogo :size="32" variant="kidneys" :animated="false" monochrome />
   ```

### Current Favicon Setup
- **index.html** (line 5): Default Vite SVG favicon
  ```html
  <link rel="icon" type="image/svg+xml" href="/vite.svg" />
  <title>Vite + Vue</title>
  ```
- **Missing**: ICO, PNG variants, Apple touch icons, manifest.webmanifest
- **Missing**: Proper meta tags for PWA support

## Research: 2025 Favicon Best Practices

### Minimal Essential Set (5 Icons + 1 Manifest)

Based on comprehensive research from Evil Martians, MDN, and Webflow:

| File | Size | Format | Purpose |
|------|------|--------|---------|
| `favicon.ico` | 32×32 (16×16 fallback) | ICO | Legacy browsers, bookmarks |
| `icon.svg` | Vector | SVG | Modern browsers, scales perfectly |
| `apple-touch-icon.png` | 180×180 | PNG | iOS home screen, Safari tabs |
| `icon-192.png` | 192×192 | PNG | Android home screen, PWA minimum |
| `icon-512.png` | 512×512 | PNG | App store listings, splash screens |
| `manifest.webmanifest` | - | JSON | PWA configuration |

### Optional Enhanced Set (For Better Coverage)

| File | Size | Format | Purpose |
|------|------|--------|---------|
| `icon-144.png` | 144×144 | PNG | Windows Metro tiles |
| `icon-384.png` | 384×384 | PNG | Enhanced Android support |

### HTML Implementation Template

```html
<head>
  <!-- Primary favicon (ICO for legacy browsers) -->
  <link rel="icon" href="/favicon.ico" sizes="32x32">

  <!-- Modern browsers (SVG preferred) -->
  <link rel="icon" href="/icon.svg" type="image/svg+xml">

  <!-- iOS/Safari -->
  <link rel="apple-touch-icon" href="/apple-touch-icon.png">

  <!-- PWA Manifest -->
  <link rel="manifest" href="/manifest.webmanifest">

  <!-- Meta tags -->
  <meta name="theme-color" content="#0EA5E9">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="default">
  <meta name="apple-mobile-web-app-title" content="KGDB">

  <!-- Title -->
  <title>KGDB - Kidney Genetics Database</title>
</head>
```

## Animation Design Specifications

### Research: Vue 3 Animation Best Practices

**Key Findings:**
- Use GPU-accelerated properties: `transform`, `opacity`
- Avoid animating: `width`, `height`, `margin` (causes expensive repaints)
- Optimal timing: 0.2-0.3s for responsiveness
- Use CSS transitions for performance
- Respect `prefers-reduced-motion`

### Animation Patterns

#### 1. Load Animation (Initial Page Load)
```scss
// Fade-in with subtle scale
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

.kgdb-logo--animated {
  animation: logo-entrance 0.6s cubic-bezier(0.34, 1.56, 0.64, 1);
}
```

#### 2. Hover Animation (Interactive State)
```scss
.kgdb-logo--interactive {
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  cursor: pointer;

  &:hover {
    transform: scale(1.05) rotate(-2deg);
  }

  &:active {
    transform: scale(0.98);
    transition-duration: 0.1s;
  }
}
```

#### 3. Idle Animation (Breathing Effect)
```scss
@keyframes logo-breathe {
  0%, 100% {
    transform: scale(1);
    filter: drop-shadow(0 0 0px rgba(72, 156, 158, 0));
  }
  50% {
    transform: scale(1.02);
    filter: drop-shadow(0 0 8px rgba(72, 156, 158, 0.3));
  }
}

.kgdb-logo--breathing {
  animation: logo-breathe 4s ease-in-out infinite;
}
```

## Component Architecture

### New Component: `KGDBLogo.vue`

**File Location**: `frontend/src/components/branding/KGDBLogo.vue`

**Component Specification:**

```vue
<template>
  <div
    class="kgdb-logo"
    :class="logoClasses"
    :style="logoStyles"
    role="img"
    :aria-label="ariaLabel"
    @click="handleClick"
  >
    <!-- Logo SVG Container -->
    <div class="kgdb-logo__icon">
      <img
        :src="logoSrc"
        :alt="alt"
        class="kgdb-logo__image"
      />
    </div>

    <!-- Text Container (optional) -->
    <div v-if="showText" class="kgdb-logo__text">
      <span class="kgdb-logo__title">
        Kidney-Genetics<br />Database
      </span>
    </div>
  </div>
</template>

<script setup>
// Props, computed properties, and logic
</script>
```

**Props API:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `size` | Number/String | 64 | Logo size in pixels (16-512) |
| `variant` | String | 'icon-only' | 'icon-only', 'with-text', 'text-only' |
| `animated` | Boolean | true | Enable load animations |
| `interactive` | Boolean | false | Enable hover effects |
| `breathing` | Boolean | false | Enable idle breathing animation |
| `monochrome` | Boolean | false | Grayscale mode for footer |
| `customColor` | String | null | Override default kidney color |
| `textLayout` | String | 'horizontal' | 'horizontal', 'vertical' |

**Computed Properties:**

```javascript
const logoClasses = computed(() => ({
  'kgdb-logo--animated': props.animated && !reducedMotion.value,
  'kgdb-logo--interactive': props.interactive,
  'kgdb-logo--breathing': props.breathing && !reducedMotion.value,
  'kgdb-logo--monochrome': props.monochrome,
  [`kgdb-logo--${props.variant}`]: true,
  [`kgdb-logo--${sizeClass.value}`]: true
}))

const logoStyles = computed(() => ({
  '--logo-size': `${props.size}px`,
  '--kidney-color': props.customColor || '#489c9e'
}))
```

## Implementation Tasks

### Phase 1: Component Development

#### Task 1.1: Create KGDBLogo.vue
**File**: `frontend/src/components/branding/KGDBLogo.vue`

**Requirements:**
- [ ] Set up component structure with proper props
- [ ] Import KGDB_logo.svg from public folder
- [ ] Implement three variants: icon-only, with-text, text-only
- [ ] Add size validation (16-512px range)
- [ ] Implement theme-aware color adjustment
- [ ] Add accessibility attributes (role, aria-label)

**Code Template:**
```vue
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
  // ... other props
})

defineEmits(['click'])

const theme = useTheme()
const reducedMotion = ref(false)

// Detect prefers-reduced-motion
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
</script>
```

#### Task 1.2: Implement Animations
**Animations to implement:**
1. **Load Animation** (0.6s, cubic-bezier ease)
   - Fade-in: opacity 0 → 1
   - Scale: 0.95 → 1
   - Translate: -10px → 0

2. **Hover Animation** (0.3s, ease-in-out)
   - Scale: 1 → 1.05
   - Rotate: 0deg → -2deg
   - Cursor: pointer

3. **Active Animation** (0.1s)
   - Scale: 1.05 → 0.98

4. **Breathing Animation** (4s, infinite)
   - Scale: 1 → 1.02 → 1
   - Shadow: 0px → 8px → 0px

**CSS Implementation:**
```scss
.kgdb-logo {
  display: inline-flex;
  align-items: center;
  gap: 16px;
  width: var(--logo-size);
  height: var(--logo-size);

  &__icon {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 100%;
    height: 100%;
  }

  &__image {
    width: 100%;
    height: 100%;
    object-fit: contain;
    transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  }

  &__text {
    font-family: 'Roboto', sans-serif;
    font-weight: 700;
    line-height: 1.2;
    color: rgb(var(--v-theme-on-surface));
  }

  // Animations
  &--animated {
    animation: logo-entrance 0.6s cubic-bezier(0.34, 1.56, 0.64, 1);
  }

  &--interactive {
    cursor: pointer;

    &:hover .kgdb-logo__image {
      transform: scale(1.05) rotate(-2deg);
    }

    &:active .kgdb-logo__image {
      transform: scale(0.98);
      transition-duration: 0.1s;
    }
  }

  &--breathing .kgdb-logo__image {
    animation: logo-breathe 4s ease-in-out infinite;
  }

  &--monochrome .kgdb-logo__image {
    filter: grayscale(100%) brightness(0.6);
  }
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

@keyframes logo-breathe {
  0%, 100% {
    transform: scale(1);
    filter: drop-shadow(0 0 0px rgba(72, 156, 158, 0));
  }
  50% {
    transform: scale(1.02);
    filter: drop-shadow(0 0 8px rgba(72, 156, 158, 0.3));
  }
}

// Respect reduced motion
@media (prefers-reduced-motion: reduce) {
  .kgdb-logo {
    animation: none !important;

    * {
      animation: none !important;
      transition-duration: 0.01ms !important;
    }
  }
}

// Print styles
@media print {
  .kgdb-logo {
    animation: none !important;
  }
}
```

#### Task 1.3: Create Component Storybook/Documentation
**Create usage examples:**

```vue
<!-- Example 1: Hero Logo with Text -->
<KGDBLogo
  :size="120"
  variant="with-text"
  :animated="true"
  :breathing="true"
/>

<!-- Example 2: Navigation Bar Logo -->
<KGDBLogo
  :size="40"
  variant="icon-only"
  :animated="false"
  :interactive="true"
  @click="router.push('/')"
/>

<!-- Example 3: Footer Logo -->
<KGDBLogo
  :size="32"
  variant="icon-only"
  :animated="false"
  :monochrome="true"
/>
```

### Phase 2: Favicon Generation

#### Task 2.1: Generate ICO Favicon
**Tool**: ImageMagick or online converter (e.g., favicon.io)

**Source**: `KGDB_logo_with_letters.svg`

**Command (if using ImageMagick):**
```bash
# Convert SVG to ICO with 32x32 and 16x16 sizes
convert KGDB_logo_with_letters.svg \
  -define icon:auto-resize=32,16 \
  -background none \
  favicon.ico
```

**Output**: `frontend/public/favicon.ico`

**Validation:**
- File size < 50KB (ICO format is larger)
- Contains both 32×32 and 16×16 versions
- Transparent background
- Clear visibility at small sizes

#### Task 2.2: Generate PNG Favicons
**Sizes Required:**
- 16×16 (optional, for old browsers)
- 32×32 (standard favicon)
- 180×180 (Apple touch icon)
- 192×192 (PWA minimum)
- 512×512 (PWA recommended)
- 144×144 (optional, Windows Metro)
- 384×384 (optional, enhanced Android)

**Generation Script:**
```bash
#!/bin/bash
# generate-favicons.sh

SOURCE="frontend/public/KGDB_logo_with_letters.svg"
OUTPUT_DIR="frontend/public"

# Standard favicons
convert "$SOURCE" -resize 16x16 -background none "$OUTPUT_DIR/favicon-16x16.png"
convert "$SOURCE" -resize 32x32 -background none "$OUTPUT_DIR/favicon-32x32.png"

# Apple touch icon (no transparency, add background)
convert "$SOURCE" -resize 180x180 -background white -alpha remove "$OUTPUT_DIR/apple-touch-icon.png"

# PWA icons (transparent background)
convert "$SOURCE" -resize 192x192 -background none "$OUTPUT_DIR/icon-192.png"
convert "$SOURCE" -resize 512x512 -background none "$OUTPUT_DIR/icon-512.png"

# Optional enhanced icons
convert "$SOURCE" -resize 144x144 -background none "$OUTPUT_DIR/icon-144.png"
convert "$SOURCE" -resize 384x384 -background none "$OUTPUT_DIR/icon-384.png"

echo "✅ All favicons generated successfully!"
```

**Validation Checklist:**
- [ ] All images have correct dimensions
- [ ] PNG images < 50KB each
- [ ] Transparent backgrounds (except Apple touch icon)
- [ ] Sharp edges, no blurriness
- [ ] Colors match brand (#489c9e)

#### Task 2.3: Optimize SVG Favicon
**Source**: `KGDB_logo_with_letters.svg`
**Output**: `frontend/public/icon.svg`

**Optimization Steps:**
1. Copy KGDB_logo_with_letters.svg to icon.svg
2. Remove unnecessary metadata
3. Optimize paths with SVGO
4. Ensure viewBox is set correctly
5. Test in browsers

**SVGO Command:**
```bash
npx svgo --multipass \
  --config '{"plugins": [{"removeTitle": true}, {"removeDesc": true}]}' \
  frontend/public/icon.svg
```

#### Task 2.4: Create Manifest File
**File**: `frontend/public/manifest.webmanifest`

**Content:**
```json
{
  "name": "Kidney Genetics Database",
  "short_name": "KGDB",
  "description": "Evidence-based kidney disease gene curation with multi-source integration",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#ffffff",
  "theme_color": "#0EA5E9",
  "orientation": "portrait-primary",
  "icons": [
    {
      "src": "/icon-192.png",
      "sizes": "192x192",
      "type": "image/png",
      "purpose": "any"
    },
    {
      "src": "/icon-512.png",
      "sizes": "512x512",
      "type": "image/png",
      "purpose": "any"
    },
    {
      "src": "/icon-192.png",
      "sizes": "192x192",
      "type": "image/png",
      "purpose": "maskable"
    },
    {
      "src": "/icon-512.png",
      "sizes": "512x512",
      "type": "image/png",
      "purpose": "maskable"
    }
  ],
  "categories": ["medical", "science", "education"],
  "screenshots": [],
  "shortcuts": [
    {
      "name": "Gene Browser",
      "short_name": "Genes",
      "description": "Browse curated kidney disease genes",
      "url": "/genes",
      "icons": [
        {
          "src": "/icon-192.png",
          "sizes": "192x192"
        }
      ]
    },
    {
      "name": "Network Analysis",
      "short_name": "Network",
      "description": "Explore gene interaction networks",
      "url": "/network-analysis",
      "icons": [
        {
          "src": "/icon-192.png",
          "sizes": "192x192"
        }
      ]
    }
  ]
}
```

**Key Configuration Notes:**
- `short_name`: "KGDB" (matches requirement)
- `theme_color`: #0EA5E9 (Vuetify primary color)
- `display`: "standalone" (full-screen PWA experience)
- `purpose`: "any maskable" (works in all contexts)

### Phase 3: HTML/Meta Updates

#### Task 3.0: Remove Old Vite Assets (CLEANUP)
**Files to Delete:**
- `frontend/public/vite.svg` - Default Vite logo (no longer needed)

**Command:**
```bash
rm frontend/public/vite.svg
```

**Verification:**
- [ ] vite.svg removed from public directory
- [ ] No references to vite.svg in index.html
- [ ] No import statements referencing vite.svg
- [ ] Git tracking updated

#### Task 3.1: Update index.html
**File**: `frontend/index.html`

**Changes Required:**

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />

    <!-- Favicon Links (2025 Best Practice) -->
    <link rel="icon" href="/favicon.ico" sizes="32x32">
    <link rel="icon" href="/icon.svg" type="image/svg+xml">
    <link rel="apple-touch-icon" href="/apple-touch-icon.png">

    <!-- PWA Manifest -->
    <link rel="manifest" href="/manifest.webmanifest">

    <!-- Viewport & Mobile -->
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />

    <!-- Theme Color -->
    <meta name="theme-color" content="#0EA5E9" media="(prefers-color-scheme: light)">
    <meta name="theme-color" content="#0284C7" media="(prefers-color-scheme: dark)">

    <!-- Apple-Specific Meta Tags -->
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="default">
    <meta name="apple-mobile-web-app-title" content="KGDB">

    <!-- Primary Meta Tags -->
    <title>KGDB - Kidney Genetics Database</title>
    <meta name="title" content="KGDB - Kidney Genetics Database">
    <meta name="description" content="Evidence-based kidney disease gene curation with multi-source integration. Professional-quality research platform for nephrology genomics.">

    <!-- Open Graph / Facebook -->
    <meta property="og:type" content="website">
    <meta property="og:url" content="https://kidney-genetics-db.org/">
    <meta property="og:title" content="KGDB - Kidney Genetics Database">
    <meta property="og:description" content="Evidence-based kidney disease gene curation with multi-source integration.">
    <meta property="og:image" content="/icon-512.png">

    <!-- Twitter -->
    <meta property="twitter:card" content="summary_large_image">
    <meta property="twitter:url" content="https://kidney-genetics-db.org/">
    <meta property="twitter:title" content="KGDB - Kidney Genetics Database">
    <meta property="twitter:description" content="Evidence-based kidney disease gene curation with multi-source integration.">
    <meta property="twitter:image" content="/icon-512.png">

    <!-- Microsoft Tiles (Optional) -->
    <meta name="msapplication-TileColor" content="#0EA5E9">
    <meta name="msapplication-TileImage" content="/icon-144.png">
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.js"></script>
  </body>
</html>
```

**Validation:**
- [ ] All favicon links resolve correctly
- [ ] Manifest loads without errors
- [ ] Theme color matches Vuetify primary
- [ ] Title shows "KGDB" prefix
- [ ] Meta descriptions are accurate

### Phase 4: Integration

#### Task 4.1: Update Home.vue Hero Section
**File**: `frontend/src/views/Home.vue` (line 7-11)

**Before:**
```vue
<div class="d-flex align-center justify-center mb-6">
  <KidneyGeneticsLogo :size="80" variant="full" :animated="true" class="mr-4" />
  <h1 class="text-h2 text-md-h1 font-weight-bold">Kidney Genetics Database</h1>
</div>
```

**After:**
```vue
<div class="d-flex align-center justify-center mb-6">
  <KGDBLogo
    :size="120"
    variant="with-text"
    :animated="true"
    :breathing="true"
    text-layout="vertical"
    class="kgdb-hero-logo"
  />
</div>
```

**Rationale:**
- Remove separate title element (logo component includes text)
- Larger size (120px) for hero prominence
- Enable breathing animation for visual interest
- Vertical text layout: "Kidney-Genetics\nDatabase"

#### Task 4.2: Update App.vue Navigation Bar
**File**: `frontend/src/App.vue` (line 11-22)

**Before:**
```vue
<div class="d-flex align-center">
  <KidneyGeneticsLogo
    :size="40"
    variant="kidneys"
    :animated="false"
    interactive
    class="mr-3 cursor-pointer"
    @click="$router.push('/')"
  />
  <v-app-bar-title class="text-h6 font-weight-medium">
    Kidney Genetics Database
  </v-app-bar-title>
</div>
```

**After:**
```vue
<div class="d-flex align-center">
  <KGDBLogo
    :size="40"
    variant="icon-only"
    :animated="false"
    :interactive="true"
    class="mr-3"
    @click="$router.push('/')"
  />
  <v-app-bar-title class="text-h6 font-weight-medium">
    Kidney Genetics Database
  </v-app-bar-title>
</div>
```

**Changes:**
- Replace KidneyGeneticsLogo with KGDBLogo
- Use icon-only variant (maintains compact nav bar)
- Keep interactive behavior for clickability

#### Task 4.3: Update App.vue Footer
**File**: `frontend/src/App.vue` (line 223-226)

**Before:**
```vue
<KidneyGeneticsLogo
  :size="32"
  variant="kidneys"
  :animated="false"
  monochrome
  class="mr-2 opacity-60"
/>
```

**After:**
```vue
<KGDBLogo
  :size="32"
  variant="icon-only"
  :animated="false"
  :monochrome="true"
  class="mr-2"
/>
```

**Changes:**
- Replace with KGDBLogo
- Maintain monochrome styling for subdued footer presence
- Keep small size (32px) for footer context

#### Task 4.4: Create Component Export
**File**: `frontend/src/components/branding/index.js`

```javascript
export { default as KGDBLogo } from './KGDBLogo.vue'
```

**Update imports:**
```javascript
// In Home.vue, App.vue
import { KGDBLogo } from '@/components/branding'
```

### Phase 5: Testing & Validation

#### Task 5.1: Visual Testing
**Test Matrix:**

| Context | Size | Variant | Animation | Device |
|---------|------|---------|-----------|--------|
| Hero | 120px | with-text | breathing | Desktop |
| Hero | 120px | with-text | breathing | Mobile |
| Nav Bar | 40px | icon-only | interactive | Desktop |
| Nav Bar | 40px | icon-only | interactive | Mobile |
| Footer | 32px | icon-only | monochrome | All |

**Validation Checklist:**
- [ ] Logo scales correctly at all sizes
- [ ] Text is legible in with-text variant
- [ ] Animations are smooth (60fps)
- [ ] No layout shifts during load
- [ ] Colors match design system (#489c9e)
- [ ] Dark mode works correctly
- [ ] Monochrome filter works in footer
- [ ] Interactive hover states work
- [ ] Reduced motion is respected

#### Task 5.2: Favicon Testing
**Test in Multiple Browsers:**

| Browser | Tab Icon | Bookmarks | Home Screen | PWA |
|---------|----------|-----------|-------------|-----|
| Chrome | ✓ | ✓ | ✓ | ✓ |
| Firefox | ✓ | ✓ | ✓ | N/A |
| Safari | ✓ | ✓ | ✓ | ✓ |
| Edge | ✓ | ✓ | ✓ | ✓ |
| Mobile Safari | ✓ | N/A | ✓ | ✓ |
| Mobile Chrome | ✓ | N/A | ✓ | ✓ |

**Validation Checklist:**
- [ ] ICO favicon appears in browser tabs
- [ ] SVG favicon scales correctly
- [ ] Apple touch icon shows on iOS home screen
- [ ] PWA icons appear in app drawer
- [ ] Manifest loads without console errors
- [ ] Theme color applies to browser UI
- [ ] Icons are sharp, not pixelated
- [ ] Transparent backgrounds work correctly

#### Task 5.3: Accessibility Testing
**Automated Tools:**
- Axe DevTools
- Lighthouse Accessibility Audit
- WAVE Browser Extension

**Manual Tests:**
- [ ] Keyboard navigation works
- [ ] Screen reader announces logo correctly
- [ ] Focus states are visible
- [ ] Sufficient color contrast (4.5:1 minimum)
- [ ] Reduced motion preference respected
- [ ] Touch targets ≥ 44×44px on mobile

#### Task 5.4: Performance Testing
**Metrics to Measure:**
- [ ] Logo component renders < 16ms
- [ ] Animations run at 60fps
- [ ] No layout shifts (CLS = 0)
- [ ] SVG loads < 50ms
- [ ] PNG favicons < 50KB each
- [ ] Total favicon size < 300KB

**Tools:**
- Chrome DevTools Performance
- Lighthouse Performance Audit
- WebPageTest

## File Structure

```
frontend/
├── public/
│   ├── favicon.ico                  # 32×32 ICO (with 16×16 fallback) [NEW]
│   ├── icon.svg                     # Optimized SVG favicon [NEW]
│   ├── apple-touch-icon.png         # 180×180 Apple touch icon [NEW]
│   ├── icon-192.png                 # 192×192 PWA minimum [NEW]
│   ├── icon-512.png                 # 512×512 PWA recommended [NEW]
│   ├── icon-144.png                 # 144×144 Windows (optional) [NEW]
│   ├── icon-384.png                 # 384×384 Android (optional) [NEW]
│   ├── manifest.webmanifest         # PWA manifest [NEW]
│   ├── KGDB_logo.svg                # Source: Main logo [EXISTING]
│   ├── KGDB_logo_with_letters.svg   # Source: Favicon base [EXISTING]
│   └── vite.svg                     # [DELETE] Old Vite default logo
├── src/
│   └── components/
│       └── branding/
│           ├── KGDBLogo.vue         # Main logo component
│           ├── index.js             # Component exports
│           └── README.md            # Usage documentation
└── index.html                        # Updated with favicon links
```

## Performance Optimizations

### 1. Lazy Loading
```javascript
// Only load logo component when needed
const KGDBLogo = defineAsyncComponent(() =>
  import('@/components/branding/KGDBLogo.vue')
)
```

### 2. Image Optimization
- Use `loading="lazy"` for non-critical logos
- Implement `srcset` for responsive images
- Optimize SVG with SVGO (remove metadata, compress paths)

### 3. Animation Optimization
- Use `will-change: transform` for animated elements
- Disable animations on print media
- Use GPU-accelerated properties only
- Respect `prefers-reduced-motion`

### 4. Caching Strategy
```nginx
# Nginx config for favicon caching
location ~* \.(ico|png|svg|webmanifest)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

## Accessibility Compliance

### WCAG 2.1 AA Requirements
- ✅ **1.1.1 Non-text Content**: Alt text and aria-label provided
- ✅ **1.4.3 Contrast**: Logo meets 4.5:1 contrast ratio
- ✅ **2.1.1 Keyboard**: Interactive logo is keyboard accessible
- ✅ **2.3.3 Animation**: Respects prefers-reduced-motion
- ✅ **2.5.5 Target Size**: Touch targets ≥ 44×44px

### Screen Reader Support
```vue
<div
  role="img"
  aria-label="Kidney Genetics Database logo - Interactive link to homepage"
  tabindex="0"
  @keypress.enter="handleClick"
>
  <!-- Logo content -->
</div>
```

## Browser Support Matrix

### Modern Browsers (Full Support)
- ✅ Chrome 90+
- ✅ Firefox 88+
- ✅ Safari 14+
- ✅ Edge 90+

### Mobile Browsers
- ✅ iOS Safari 14+
- ✅ Chrome Android 90+
- ✅ Samsung Internet 14+

### Legacy Browsers (Graceful Degradation)
- ⚠️ IE 11: Falls back to ICO favicon, no animations
- ⚠️ Safari 13: No SVG favicon, uses PNG fallback

## Maintenance & Future Work

### Regular Maintenance Tasks
- [ ] Update manifest when app features change
- [ ] Regenerate favicons if logo design changes
- [ ] Test favicons on new browser releases
- [ ] Monitor Core Web Vitals for logo performance

### Future Enhancements
1. **Animated SVG Logo** (Phase 2)
   - Replace static SVG with SMIL animations
   - Add micro-interactions within the logo

2. **Dark Mode Variant** (Phase 2)
   - Create separate dark theme logo
   - Auto-switch based on system preference

3. **Brand Guidelines** (Phase 3)
   - Document logo usage rules
   - Create brand asset library
   - Design logo variations (horizontal, stacked, icon)

4. **PWA Enhancements** (Phase 3)
   - Add splash screens
   - Implement service worker
   - Enable offline functionality

## Success Criteria

### Phase 1 (MVP - Week 1)
- [x] Research completed and documented
- [ ] KGDBLogo.vue component created with animations
- [ ] All favicons generated and optimized
- [ ] index.html updated with favicon links
- [ ] Manifest.webmanifest created

### Phase 2 (Integration - Week 1)
- [ ] Home.vue updated with new logo
- [ ] App.vue navigation updated
- [ ] App.vue footer updated
- [ ] Visual testing completed
- [ ] Favicon testing in all major browsers

### Phase 3 (Validation - Week 2)
- [ ] Accessibility audit passed
- [ ] Performance metrics meet targets
- [ ] Documentation completed
- [ ] Design system guide updated

## Related Issues & References

### GitHub Issues
- #5: Implement KGDB Logo Component and Professional Favicon System

### External References
- [Evil Martians: How to Favicon in 2025](https://evilmartians.com/chronicles/how-to-favicon-in-2021-six-files-that-fit-most-needs)
- [MDN: Define App Icons](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/How_to/Define_app_icons)
- [Vue.js: Animation Techniques](https://vuejs.org/guide/extras/animation)
- [LogRocket: Animated Logos with Lottie](https://blog.logrocket.com/creating-animated-logos-lottie-vue-3/)
- [Webflow: Favicon Guide 2025](https://webflow.com/blog/favicon-guide)

### Internal References
- `docs/reference/design-system.md` - Design principles and color system
- `frontend/src/components/KidneyGeneticsLogo.vue` - Existing logo component reference
- `frontend/public/KGDB_logo.svg` - Main logo asset
- `frontend/public/KGDB_logo_with_letters.svg` - Favicon source

## Notes & Decisions

### Design Decisions
1. **Logo Component Name**: `KGDBLogo` (concise, matches favicon branding)
2. **Text Layout**: Vertical by default for hero (`Kidney-Genetics\nDatabase`)
3. **Animation Style**: Subtle, professional (no excessive effects)
4. **Favicon Strategy**: Minimal essential set (5 files) for 99% coverage
5. **Color Preservation**: Use brand kidney color (#489c9e) throughout

### Technical Decisions
1. **Component Location**: `components/branding/` (separate namespace)
2. **SVG Format**: Inline `<img>` for simplicity and caching
3. **Animation Method**: CSS animations (better performance than JS)
4. **Favicon Format Priority**: SVG > PNG > ICO
5. **PWA Support**: Full manifest with shortcuts

### Open Questions
- ~~Should we support Lottie animations for more complex effects?~~ **Decision: No, CSS animations sufficient for MVP**
- ~~Do we need multiple color variants (light/dark)?~~ **Decision: Single color with theme-aware filters**
- ~~Should logo component be separate npm package?~~ **Decision: Keep internal for now**

## Changelog

- **2025-10-10**: Initial planning document created
- **2025-10-10**: Research phase completed (favicon best practices, Vue 3 animations)
- **2025-10-10**: Component architecture finalized
- **2025-10-10**: Animation specifications defined

---

**Document Version**: 1.0
**Last Updated**: 2025-10-10
**Status**: Active Planning → Ready for Implementation
