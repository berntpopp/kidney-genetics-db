# Kidney Genetics Database - Design System

**Current Status**: Production implementation based on comprehensive UX audit (January 2025)

## Design Philosophy

### Core Principles
1. **Single Path to Action** - Eliminate decision paralysis with clear user journeys
2. **Information Hierarchy** - Essential data first, technical details accessible but not prominent  
3. **Density Optimization** - Compact layouts for data-heavy scientific interfaces
4. **Professional Trust** - Medical-grade interface design that respects genetic research
5. **Accessibility First** - Controls visible without scrolling, proper contrast, keyboard navigation

## Logo & Branding System

### Brand Identity: "KGdb"

The KGDB logo embodies the project's identity as the **Kidney-Genetics database**. The branding emphasizes "KG" (Kidney-Genetics) as the primary identifier with "db" (database) as a descriptive suffix.

#### **Visual Hierarchy**
```
Kidney-Genetics  ← Primary brand name (100% size)
database         ← Descriptor (75% size, lowercase)
```

### Logo Variants

#### **1. Icon-Only** (`variant="icon-only"`)
```vue
<!-- Favicon, mobile icons, compact spaces -->
<KGDBLogo :size="32" variant="icon-only" />

Use cases:
- Browser favicon (16x16, 32x32)
- Mobile app icons (192x192, 512x512)
- Compact navigation bars
- Social media profile images
```

#### **2. With-Text Horizontal** (`variant="with-text" text-layout="horizontal"`)
```vue
<!-- Navigation bar, hero section -->
<KGDBLogo
  :size="40"
  variant="with-text"
  text-layout="horizontal"
  :interactive="true"
/>

Layout: [Kidney-icon] Kidney-Genetics
                       database

Use cases:
- Primary navigation bar (size: 40px)
- Hero section (size: 60-180px, responsive)
- Page headers
- Marketing materials
```

#### **3. With-Text Vertical** (`variant="with-text" text-layout="vertical"`)
```vue
<!-- Splash screens, print materials -->
<KGDBLogo
  :size="120"
  variant="with-text"
  text-layout="vertical"
/>

Layout:  [Kidney-icon]
         Kidney-Genetics
         database

Use cases:
- Splash screens
- Print materials (posters, reports)
- Standalone branding
```

#### **4. Text-Only** (`variant="text-only"`)
```vue
<!-- Fallback for accessibility -->
<KGDBLogo variant="text-only" />

Use cases:
- Screen readers
- Text-only contexts
- Email signatures
```

### Typography Specifications

#### **Text Styling**
```scss
.kgdb-logo__text {
  font-family: 'Roboto', -apple-system, BlinkMacSystemFont, sans-serif;
  font-weight: 700;          // Bold for brand prominence
  letter-spacing: -0.02em;   // Tight tracking for cohesion
  color: rgb(var(--v-theme-on-surface));  // Theme-aware
}

.kgdb-logo__text-primary {
  // "Kidney-Genetics" - Full size, title case
  font-size: 1em;            // Base size (scales with logo size)
}

.kgdb-logo__text-secondary {
  // "database" - Smaller, lowercase
  font-size: 0.75em;         // 75% of primary
  text-transform: lowercase;  // Always lowercase
}
```

#### **Size Scale**
```scss
// Size classes (automatically applied based on logo size prop)
.kgdb-logo--xs  { font-size: 10px; }  // 16-24px logo
.kgdb-logo--sm  { font-size: 14px; }  // 25-40px logo
.kgdb-logo--md  { font-size: 24px; }  // 41-64px logo (mobile hero)
.kgdb-logo--lg  { font-size: 36px; }  // 65-128px logo (tablet hero)
.kgdb-logo--xl  { font-size: 64px; }  // 129-512px logo (desktop hero)
```

### Responsive Sizing

#### **Breakpoint Guidelines**
```vue
<script setup>
import { computed } from 'vue'
import { useDisplay } from 'vuetify'

const { xs, sm } = useDisplay()

// Responsive logo sizing
const logoSize = computed(() => {
  if (xs.value) return 60   // Mobile (375px)
  if (sm.value) return 100  // Tablet (768px)
  return 180                // Desktop (1920px)
})
</script>

<template>
  <KGDBLogo
    :size="logoSize"
    variant="with-text"
    text-layout="horizontal"
  />
</template>
```

#### **Context-Specific Sizes**
```scss
// Navigation bar
.v-app-bar .kgdb-logo { size: 40px; }

// Hero section
.hero-section .kgdb-logo {
  size: 60px;   // Mobile
  size: 100px;  // Tablet
  size: 180px;  // Desktop
}

// Footer
.v-footer .kgdb-logo {
  size: 32px;
  monochrome: true;  // Grayscale version
}
```

### Interactive States

#### **Hover Effects** (when `interactive="true"`)
```scss
.kgdb-logo--interactive {
  cursor: pointer;
  transition: transform 0.2s ease;

  &:hover .kgdb-logo__image {
    transform: scale(1.05) rotate(-2deg);  // Subtle playful lift
    transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  }

  &:active .kgdb-logo__image {
    transform: scale(0.98);  // Press feedback
    transition-duration: 0.1s;
  }
}
```

#### **Focus States** (keyboard navigation)
```scss
.kgdb-logo--interactive:focus-visible {
  outline: 2px solid rgb(var(--v-theme-primary));
  outline-offset: 4px;
  border-radius: 8px;
}
```

### Animation System

#### **Entrance Animation** (when `animated="true"`)
```scss
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

#### **Breathing Animation** (when `breathing="true"`)
```scss
@keyframes logo-breathe {
  0%, 100% {
    transform: scale(1);
    filter: drop-shadow(0 0 0px rgba(72, 156, 158, 0.3));
  }
  50% {
    transform: scale(1.02);
    filter: drop-shadow(0 0 8px rgba(72, 156, 158, 0.3));
  }
}

.kgdb-logo--breathing .kgdb-logo__image {
  animation: logo-breathe 4s ease-in-out infinite;
}
```

#### **Motion Preferences**
```scss
@media (prefers-reduced-motion: reduce) {
  .kgdb-logo,
  .kgdb-logo * {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

### Color & Theme

#### **Light Mode**
```scss
.kgdb-logo {
  --kidney-color: #489c9e;           // Teal kidney shape
  --kidney-shadow: rgba(72, 156, 158, 0.3);
  --text-color: rgb(var(--v-theme-on-surface));
}
```

#### **Dark Mode**
```scss
.kgdb-logo--dark .kgdb-logo__image {
  filter: brightness(1.1) contrast(1.05);  // Enhance visibility
}
```

#### **Monochrome Mode** (footer)
```scss
.kgdb-logo--monochrome .kgdb-logo__image {
  filter: grayscale(100%) brightness(0.6) contrast(1.2);
}

.kgdb-logo--monochrome .kgdb-logo__text {
  opacity: 0.7;
}
```

### Accessibility

#### **Screen Reader Support**
```vue
<div
  role="img"
  :aria-label="ariaLabel"
  :tabindex="interactive ? 0 : -1"
>
  <!-- ariaLabel examples: -->
  <!-- "Kidney Genetics Database logo" (icon-only) -->
  <!-- "Kidney Genetics Database - click to navigate home" (interactive) -->
</div>
```

#### **Text Selection**
```scss
// Logo image is non-selectable
.kgdb-logo__image {
  user-select: none;
  -webkit-user-select: none;
}

// Text is selectable for copying
.kgdb-logo__text {
  user-select: auto;  // Default - text can be selected
}
```

#### **High Contrast Mode**
```scss
@media (prefers-contrast: high) {
  .kgdb-logo__image {
    filter: contrast(1.5) !important;
  }

  .kgdb-logo__text {
    font-weight: 800;  // Bolder for visibility
  }
}
```

### Usage Guidelines

#### **✅ Correct Usage**
```vue
<!-- Navigation bar -->
<KGDBLogo
  :size="40"
  variant="with-text"
  text-layout="horizontal"
  :animated="false"
  :interactive="true"
  @click="$router.push('/')"
/>

<!-- Hero section -->
<KGDBLogo
  :size="logoSize"  <!-- responsive -->
  variant="with-text"
  text-layout="horizontal"
  :animated="true"
  :breathing="true"
  :interactive="true"
  @click="$router.push('/')"
/>

<!-- Footer -->
<KGDBLogo
  :size="32"
  variant="icon-only"
  :monochrome="true"
/>
```

#### **❌ Incorrect Usage**
```vue
<!-- ❌ Don't mix layouts inconsistently -->
<KGDBLogo text-layout="vertical" />  <!-- Nav bar should be horizontal -->

<!-- ❌ Don't use oversized logos in navigation -->
<KGDBLogo :size="200" />  <!-- Too large for app bar -->

<!-- ❌ Don't animate in static contexts -->
<KGDBLogo :breathing="true" />  <!-- Footer should be static -->

<!-- ❌ Don't make footer logo interactive -->
<KGDBLogo variant="icon-only" :interactive="true" />  <!-- Footer is for display only -->
```

### Spacing & Clear Space

#### **Minimum Clear Space**
```scss
// Maintain clear space around logo
.logo-container {
  padding: calc(var(--logo-size) * 0.25);  // 25% of logo size
  min-height: calc(var(--logo-size) * 1.5);
}
```

#### **Gap Between Logo and Text**
```scss
.kgdb-logo__with-text-horizontal {
  gap: 4px;  // Very tight - text is part of logo lockup
}

.kgdb-logo__with-text-vertical {
  gap: calc(var(--logo-size) * 0.2);  // Proportional to size
}
```

### File Locations

#### **Component Files**
```
frontend/src/components/branding/
├── KGDBLogo.vue          # Main component
├── index.js              # Export file
└── README.md             # Component documentation
```

#### **Asset Files**
```
frontend/public/
├── KGDB_logo.svg                # Icon only (kidney shape)
├── KGDB_logo_with_letters.svg   # Full logo with "KGdb" letters
├── icon.svg                     # Optimized for web
├── favicon.ico                  # Multi-resolution ICO
├── icon-192.png                 # PWA icon (Android)
├── icon-512.png                 # PWA icon (Android)
├── apple-touch-icon.png         # iOS icon (180x180)
└── manifest.webmanifest         # PWA configuration
```

### Favicon Implementation

#### **HTML Meta Tags** (2025 Best Practices)
```html
<!-- Essential favicons -->
<link rel="icon" href="/favicon.ico" sizes="32x32">
<link rel="icon" href="/icon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">

<!-- PWA manifest -->
<link rel="manifest" href="/manifest.webmanifest">

<!-- Theme color -->
<meta name="theme-color" content="#0EA5E9" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#0284C7" media="(prefers-color-scheme: dark)">
```

#### **PWA Manifest**
```json
{
  "name": "Kidney Genetics Database",
  "short_name": "KGDB",
  "icons": [
    { "src": "/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/icon-512.png", "sizes": "512x512", "type": "image/png" }
  ],
  "theme_color": "#0EA5E9",
  "background_color": "#ffffff",
  "display": "standalone"
}
```

### Brand Consistency Checklist

- [ ] Logo uses "Kidney-Genetics" (title case) + "database" (lowercase)
- [ ] "database" text is 75% size of "Kidney-Genetics"
- [ ] Horizontal layout for navigation and hero sections
- [ ] Interactive logos have hover effects enabled
- [ ] Responsive sizing based on viewport (60px → 100px → 180px)
- [ ] Animation respects `prefers-reduced-motion`
- [ ] Proper ARIA labels for accessibility
- [ ] Clear space maintained (25% of logo size minimum)
- [ ] Favicon includes all required formats (ICO, SVG, PNG)
- [ ] Theme colors defined for light and dark modes

---

## Current Implementation

### Homepage Architecture (v2.0)

#### **Information Structure**
```
✅ Implemented Layout:
1. Hero Section - Logo+title alignment, single CTA
2. Statistics Cards - Visual data overview with gradients
3. Key Benefits - Value proposition (Evidence-Based, Multi-Source, Research-Grade)
4. Footer - Minimal branding and navigation

❌ Removed (cluttered):
- Quick Actions section (duplicate CTAs)
- Detailed Data Sources section (moved to About)
- Recent Activity timeline (developer-focused)
- Duplicate stats display
```

#### **Logo & Title Pattern**
```scss
// Horizontal alignment (implemented)
.hero-title {
  display: flex;
  align-items: center;     // Baseline alignment
  justify-content: center; // Centered layout
  gap: 16px;              // Logo to title spacing
}

.logo { width: 80px; }    // Proportional to text
.title { margin: 0; }     // Remove default margins
```

#### **Single CTA Strategy**
```scss
// ❌ Before: Multiple duplicate paths
// "Browse Genes", "View All Genes", "Start Searching" → /genes

// ✅ After: Single clear action
.primary-cta {
  action: "Explore Genes" → /genes;
  // Gene browser handles search + browse functionality
}
```

### Data Table Patterns (v2.0)

#### **Density & Accessibility**
```scss
.gene-table {
  // Compact density for scientific data
  density: 'compact';
  row-height: 48px;       // Reduced from 60px
  cell-padding: 8px 12px; // Reduced from 12px 16px
}

// Top-accessible pagination (no scrolling required)
.pagination-controls {
  position: sticky;
  top: 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
```

#### **Component Sizing System**
```scss
.data-components {
  // Size hierarchy for information density
  .evidence-score-chip { size: 'small'; }      // Primary metric
  .source-chips        { size: 'x-small'; }    // Secondary info
  .count-chips         { size: 'x-small'; }    // Supporting data
  .meta-chips          { size: 'x-small'; }    // Tags, labels
}
```

#### **Tooltip Pattern for Classifications**
```scss
.evidence-score-display {
  // ❌ Before: "20.9 Disputed" inline text
  // ✅ After: "20.9" with tooltip showing "Disputed"
  
  .score-chip {
    cursor: help;
    tooltip: "Classification: {label} - Evidence strength based on curated data sources";
  }
}
```

#### **Dynamic Progress Normalization**
```scss
.evidence-progress {
  // ❌ Before: Hardcoded maximum (/20)
  // ✅ After: Dynamic maximum from current dataset
  
  max-value: Math.max(...genes.map(g => g.evidence_count));
  // PKD1 with 4/4 evidence shows 100%, not 20%
}
```

### Color System (Material Design 3)

#### **Core Palette**
```scss
// Light Mode
$primary: #0EA5E9;         // Sky blue - Primary actions
$success: #10B981;         // Emerald - Positive indicators  
$info: #3B82F6;            // Blue - Information
$secondary: #8B5CF6;       // Violet - Secondary actions
$warning: #F59E0B;         // Amber - Caution
$error: #EF4444;           // Red - Critical alerts

// Dark Mode (auto-adjusted for contrast)
$dark-primary: #38BDF8;    // Higher luminance
$dark-success: #34D399;    // Adjusted for dark
```

#### **Evidence Score Colors** 
```scss
// Scientific confidence scale (0-100)
.evidence-scores {
  95-100: #059669;  // Definitive - Deep green
  80-94:  #10B981;  // Strong - Emerald  
  70-79:  #34D399;  // Moderate - Light green
  50-69:  #FCD34D;  // Limited - Amber
  30-49:  #FB923C;  // Minimal - Orange
  0-29:   #F87171;  // Disputed - Light red
}
```

### Typography (Vuetify + Material Design)

#### **Font Stack**
```scss
$font-primary: 'Roboto', -apple-system, BlinkMacSystemFont, sans-serif;
$font-mono: 'Roboto Mono', 'SF Mono', Monaco, monospace;
```

#### **Text Hierarchy**
```scss
// Page titles
.text-h1, .text-h2 { font-weight: 700; }

// Section headers  
.text-h4, .text-h5 { font-weight: 500; }

// Data labels
.text-caption { 
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

// Technical identifiers
.gene-symbol { font-weight: 500; color: var(--v-theme-primary); }
.hgnc-id { font-family: var(--font-mono); font-size: 12px; }
```

### Spacing System (4px grid)

#### **Component Spacing**
```scss
// Vuetify spacing scale
$spacer: 4px;
.pa-1 { padding: 4px; }    // Tight spacing
.pa-2 { padding: 8px; }    // Compact spacing  
.pa-4 { padding: 16px; }   // Default spacing
.pa-6 { padding: 24px; }   // Generous spacing

// Margins
.mb-3 { margin-bottom: 12px; }  // Section spacing
.mb-6 { margin-bottom: 24px; }  // Major section spacing
.mt-8 { margin-top: 32px; }     // Page section spacing
```

### Component Patterns

#### **Statistics Cards** (Homepage)
```scss
.stat-card {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
  
  &:hover {
    elevation: 4;           // Increased shadow on hover
  }
  
  .stat-gradient {
    background: linear-gradient(135deg, {color-start}, {color-end});
    text-align: center;
    padding: 16px;
    
    .stat-icon { size: x-large; color: white; }
    .stat-value { font-size: 3rem; font-weight: bold; color: white; }
    .stat-label { font-size: 14px; opacity: 0.95; color: white; }
  }
}
```

#### **Data Table Cells**
```scss
.gene-table-cell {
  // Gene symbols - primary identifier
  .gene-symbol {
    font-weight: 500;
    color: rgb(var(--v-theme-primary));
    text-decoration: none;
    
    &:hover {
      text-decoration: underline;
      color: rgb(var(--v-theme-primary-darken-1));
    }
  }
  
  // Technical references
  .hgnc-id {
    font-family: var(--font-mono);
    font-size: 12px;
    background: rgb(var(--v-theme-surface-variant));
    padding: 2px 6px;
    border-radius: 4px;
  }
  
  // Evidence metrics
  .evidence-score {
    font-weight: 600;
    font-variant-numeric: tabular-nums;
  }
}
```

## Implementation Guidelines

### ✅ Do's - Current Best Practices
- **Single primary action** per page/section (avoid duplicate CTAs)
- **Top-accessible pagination** (controls visible without scrolling)
- **Tooltips for classifications** (keep data display clean)
- **Dynamic progress normalization** (relative to actual data)
- **Horizontal logo-title alignment** (professional brand lockup)
- **Compact density for data interfaces** (scientific efficiency)
- **Consistent component sizing** (x-small/small hierarchy)

### ❌ Don'ts - Avoid These Patterns  
- **Multiple CTAs for same action** (Browse/Search/View All → same page)
- **Pagination only at bottom** (forces unnecessary scrolling)
- **Inline classification text** (clutters data display) 
- **Hardcoded progress maximums** (misleading relative values)
- **Vertically stacked logo-title** (looks misaligned)
- **Mixed component densities** (inconsistent information hierarchy)
- **Duplicate information sections** (increases cognitive load)

## Vuetify Integration

### Theme Configuration
```javascript
// vuetify.config.js
export default {
  theme: {
    defaultTheme: 'light',
    themes: {
      light: {
        colors: {
          primary: '#0EA5E9',
          secondary: '#8B5CF6', 
          success: '#10B981',
          warning: '#F59E0B',
          error: '#EF4444',
          info: '#3B82F6',
        }
      }
    }
  }
}
```

### Component Density
```javascript
// Density settings for different contexts
<v-data-table density="compact" />        // Data interfaces
<v-text-field density="compact" />        // Form fields in data UI
<v-btn size="small" />                    // Secondary actions
<v-chip size="x-small" />                 // Data labels/tags
```

## File Structure

```
frontend/src/
├── components/
│   ├── KidneyGeneticsLogo.vue        // Brand component
│   └── GeneTable.vue                 // Main data interface
├── views/
│   └── Home.vue                      // Landing page
└── assets/
    ├── nephrology.svg                // Material Design icons
    └── genetics.svg
```

## Performance Considerations

### Component Loading
```javascript
// Lazy load heavy data components
const GeneTable = () => import('./components/GeneTable.vue')

// Virtual scrolling for large datasets
<v-virtual-scroll :items="genes" :item-height="48" />
```

### CSS Optimization
```scss
// Use CSS custom properties for theme values
.component {
  background: rgb(var(--v-theme-surface));
  color: rgb(var(--v-theme-on-surface));
}
```

## Accessibility

### Focus States
```scss
.focusable:focus-visible {
  outline: 2px solid rgb(var(--v-theme-primary));
  outline-offset: 2px;
}
```

### Motion Preferences
```scss
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

## Version History

- **v2.1.0** (2025-10-10): Logo & branding system documentation
  - Comprehensive logo component guidelines
  - "KGdb" brand identity (Kidney-Genetics + database)
  - Four logo variants with usage specifications
  - Responsive sizing patterns (mobile/tablet/desktop)
  - Interactive states and animations
  - Accessibility features (ARIA, keyboard nav, motion preferences)
  - Favicon implementation (2025 best practices)
  - Brand consistency checklist

- **v2.0.0** (2025-01-16): Production implementation after UX audit
  - Homepage redesign with single CTA pattern
  - Logo alignment improvements
  - Data table density optimization
  - Pagination accessibility enhancements
  - Evidence display with tooltips
  - Systematic component sizing
  - Removal of duplicate information sections

---

*This style guide reflects the current production implementation. All patterns have been tested and validated through comprehensive UX audit.*