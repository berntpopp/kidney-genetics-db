# KGDB Branding Components

Professional, reusable branding components for the Kidney Genetics Database.

## Components

### KGDBLogo

A flexible, animated logo component with multiple variants and accessibility features.

#### Usage Examples

```vue
<script setup>
import { KGDBLogo } from '@/components/branding'
</script>

<template>
  <!-- Hero section: Large logo with text, breathing animation -->
  <KGDBLogo
    :size="120"
    variant="with-text"
    text-layout="vertical"
    :animated="true"
    :breathing="true"
  />

  <!-- Navigation bar: Small icon, interactive -->
  <KGDBLogo
    :size="40"
    variant="icon-only"
    :animated="false"
    :interactive="true"
    @click="$router.push('/')"
  />

  <!-- Footer: Monochrome, subdued -->
  <KGDBLogo
    :size="32"
    variant="icon-only"
    :monochrome="true"
    :animated="false"
  />
</template>
```

#### Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `size` | Number/String | 64 | Logo size in pixels (16-512) |
| `variant` | String | 'icon-only' | Display variant: 'icon-only', 'with-text', 'text-only' |
| `textLayout` | String | 'horizontal' | Text layout: 'horizontal' (side-by-side), 'vertical' (stacked) |
| `animated` | Boolean | true | Enable entrance animation on mount |
| `interactive` | Boolean | false | Enable hover effects and cursor pointer |
| `breathing` | Boolean | false | Enable subtle idle breathing animation |
| `monochrome` | Boolean | false | Convert to grayscale (for footer, print) |
| `customColor` | String | null | Override default kidney color (#489c9e) |
| `alt` | String | 'KGDB Logo' | Alt text for screen readers |

#### Events

| Event | Payload | Description |
|-------|---------|-------------|
| `click` | MouseEvent | Emitted when logo is clicked (only if `interactive` is true) |

#### Variants

**icon-only** (Default)
- Just the kidney logo icon
- Perfect for navigation bars, footers, compact spaces
- Scales cleanly from 16px to 512px

**with-text**
- Icon + "Kidney-Genetics\nDatabase" text
- Available in horizontal (nav bar) or vertical (hero) layouts
- Professional branding for headers and landing pages

**text-only**
- Just the text without icon
- Rarely used, available for special layouts

#### Animations

**Load Animation** (0.6s, enabled by default)
- Smooth entrance: fade-in + scale + slide up
- Uses elastic easing for pleasant feel
- Automatically disabled if `prefers-reduced-motion`

**Hover Animation** (0.3s, interactive mode only)
- Subtle scale-up (1.05x) and rotation (-2deg)
- Smooth cubic-bezier easing
- Active state: quick scale-down (0.98x)

**Breathing Animation** (4s infinite, opt-in)
- Gentle pulse: scale 1.0 ↔ 1.02
- Soft glow: drop-shadow 0px ↔ 8px
- Perfect for hero sections to draw attention

#### Accessibility

- ✅ **ARIA labels**: Descriptive labels based on variant
- ✅ **Keyboard navigation**: Focusable when interactive
- ✅ **Reduced motion**: Respects `prefers-reduced-motion`
- ✅ **High contrast**: Enhanced for high-contrast mode
- ✅ **Screen readers**: Proper alt text and semantic HTML
- ✅ **Focus indicators**: Clear 2px outline on focus-visible

#### Performance

- **GPU-accelerated**: Uses `transform` and `opacity` only
- **60fps animations**: Smooth on all modern devices
- **Lazy loading**: Can be code-split with `defineAsyncComponent`
- **Small bundle**: < 5KB including styles

#### Theme Support

- **Light/Dark mode**: Automatically adjusts brightness
- **Vuetify integration**: Uses theme variables
- **Monochrome mode**: Perfect for subdued contexts
- **Custom colors**: Override kidney color for special branding

#### Browser Support

- ✅ Chrome 90+
- ✅ Firefox 88+
- ✅ Safari 14+
- ✅ Edge 90+
- ⚠️ IE 11: Falls back gracefully, no animations

## Design System Integration

These components follow the [Design System](../../docs/reference/design-system.md) guidelines:

- **Colors**: Uses brand kidney color (#489c9e, #327b82)
- **Typography**: Roboto Bold for text variants
- **Spacing**: 4px grid system
- **Animations**: Subtle, professional, respect user preferences
- **Accessibility**: WCAG 2.1 AA compliant

## File Structure

```
components/branding/
├── KGDBLogo.vue         # Main logo component
├── index.js             # Component exports
└── README.md            # This file
```

## Related Documentation

- [Implementation Plan](../../docs/implementation-notes/active/logo-and-favicon-implementation.md)
- [Design System](../../docs/reference/design-system.md)
- [GitHub Issue #5](https://github.com/berntpopp/kidney-genetics-db/issues/5)
