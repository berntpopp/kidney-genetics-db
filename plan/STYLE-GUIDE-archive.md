# Kidney Genetics Database - Visual Design System & Style Guide

## Design Philosophy

### Core Principles

#### 1. **Scientific Precision**
Every design decision prioritizes accuracy and clarity of data presentation over aesthetic flourishes.

#### 2. **Cognitive Efficiency**
Minimize cognitive load through consistent patterns, clear hierarchies, and predictable interactions.

#### 3. **Professional Trust**
Build confidence through refined, medical-grade interface design that respects the gravity of genetic research.

#### 4. **Accessible Intelligence**
Complex data made approachable without sacrificing depth or professional utility.

## Brand Identity

### Logo & Mark
```
Primary Mark: DNA double helix integrated with kidney silhouette
Wordmark: "KidneyGenetics" in Inter Medium
Icon: Simplified DNA strand for favicon/app icon
```

### Brand Values
- **Precision**: Exact, reliable, scientifically rigorous
- **Clarity**: Complex made comprehensible
- **Trust**: Medical-grade quality and reliability
- **Innovation**: Modern approaches to genetic research

## Color System

### Primary Palette

#### Light Mode
```scss
// Core Brand Colors - Optimized for Medical/Scientific UI
$primary: #0EA5E9;         // Sky blue - Primary actions, trust
$primary-darken-1: #0284C7; // Hover states
$primary-darken-2: #0369A1; // Active states
$primary-lighten-1: #38BDF8; // Light variant
$primary-lighten-2: #7DD3FC; // Lighter variant
$primary-lighten-3: #F0F9FF; // Subtle backgrounds

// Semantic Colors (Material Design 3 aligned)
$success: #10B981;         // Emerald - Positive indicators
$warning: #F59E0B;         // Amber - Caution states
$error: #EF4444;           // Red - Critical alerts
$info: #3B82F6;            // Blue - Information
$secondary: #8B5CF6;       // Violet - Secondary actions

// Surface Colors (Material Design 3)
$background: #FAFAFA;      // Main background
$surface: #FFFFFF;         // Card/component backgrounds
$surface-bright: #FFFFFF;  // Elevated surfaces
$surface-light: #F4F4F5;   // Alternate rows/subtle
$surface-variant: #E4E4E7; // Input backgrounds
$on-surface-variant: #52525B; // Text on variant surfaces

// Text Colors with Material Design opacity levels
$on-background: #18181B;   // Primary text (87% opacity)
$on-surface: #27272A;      // Surface text
$high-emphasis-opacity: 0.87;
$medium-emphasis-opacity: 0.60;
$disabled-opacity: 0.38;
```

#### Dark Mode
```scss
// Dark Theme (Material Design 3 aligned)
$dark-background: #0F0F11;     // Main background
$dark-surface: #1A1A1D;        // Card backgrounds
$dark-surface-bright: #27272A;  // Elevated surfaces
$dark-surface-light: #1F1F23;   // Subtle elevation
$dark-surface-variant: #2A2A2E; // Input backgrounds
$dark-on-surface-variant: #E4E4E7;

// Adjusted brand colors for dark mode (WCAG AAA compliant)
$dark-primary: #38BDF8;         // Higher luminance for contrast
$dark-primary-darken-1: #0EA5E9;
$dark-secondary: #A78BFA;       // Adjusted violet
$dark-success: #34D399;         // Adjusted for dark
$dark-warning: #FCD34D;         // Brighter amber
$dark-error: #F87171;           // Lighter red
```

### Vuetify Theme Configuration
```javascript
// vuetify.config.js - Aligned with Material Design 3
export default {
  theme: {
    defaultTheme: 'light',
    variations: {
      colors: ['primary', 'secondary', 'success'],
      lighten: 3,
      darken: 2,
    },
    themes: {
      light: {
        dark: false,
        colors: {
          background: '#FAFAFA',
          surface: '#FFFFFF',
          'surface-bright': '#FFFFFF',
          'surface-light': '#F4F4F5',
          'surface-variant': '#E4E4E7',
          'on-surface-variant': '#52525B',
          primary: '#0EA5E9',
          'primary-darken-1': '#0284C7',
          'primary-darken-2': '#0369A1',
          secondary: '#8B5CF6',
          'secondary-darken-1': '#7C3AED',
          error: '#EF4444',
          info: '#3B82F6',
          success: '#10B981',
          warning: '#F59E0B',
          'on-background': '#18181B',
          'on-surface': '#27272A',
          'on-primary': '#FFFFFF',
          'on-secondary': '#FFFFFF',
          'on-error': '#FFFFFF',
          'on-info': '#FFFFFF',
          'on-success': '#FFFFFF',
          'on-warning': '#FFFFFF',
        },
        variables: {
          'border-color': '#E4E4E7',
          'border-opacity': 0.12,
          'high-emphasis-opacity': 0.87,
          'medium-emphasis-opacity': 0.60,
          'disabled-opacity': 0.38,
          'idle-opacity': 0.04,
          'hover-opacity': 0.04,
          'focus-opacity': 0.12,
          'selected-opacity': 0.08,
          'activated-opacity': 0.12,
          'pressed-opacity': 0.12,
          'dragged-opacity': 0.08,
          'theme-kbd': '#212529',
          'theme-on-kbd': '#FFFFFF',
          'theme-code': '#F5F5F5',
          'theme-on-code': '#000000',
        }
      },
      dark: {
        dark: true,
        colors: {
          background: '#0F0F11',
          surface: '#1A1A1D',
          'surface-bright': '#27272A',
          'surface-light': '#1F1F23',
          'surface-variant': '#2A2A2E',
          'on-surface-variant': '#E4E4E7',
          primary: '#38BDF8',
          'primary-darken-1': '#0EA5E9',
          'primary-darken-2': '#0284C7',
          secondary: '#A78BFA',
          'secondary-darken-1': '#8B5CF6',
          error: '#F87171',
          info: '#60A5FA',
          success: '#34D399',
          warning: '#FCD34D',
          'on-background': '#F4F4F5',
          'on-surface': '#F4F4F5',
        }
      }
    }
  }
}
```

### Evidence Score Colors
```scss
// Scientific confidence scale (0-100)
$score-pristine: #059669;  // 95-100: Deep green
$score-high:     #10B981;  // 80-94: Emerald
$score-good:     #34D399;  // 70-79: Light green
$score-moderate: #FCD34D;  // 50-69: Amber
$score-low:      #FB923C;  // 30-49: Orange
$score-minimal:  #F87171;  // 10-29: Light red
$score-absent:   #B91C1C;  // 0-9: Deep red

// Usage in components
.evidence-score {
  @each $name, $color in $score-colors {
    &--#{$name} {
      background: $color;
      color: white;
    }
  }
}
```

### Data Source Colors
```scss
$source-panelapp:   #0891B2;  // Cyan
$source-hpo:        #7C3AED;  // Purple
$source-pubtator:   #DB2777;  // Pink
$source-literature: #059669;  // Green
$source-diagnostic: #DC2626;  // Red
```

## Typography

### Font Stack
```scss
// Primary Font - Roboto (Vuetify default, optimized for Material Design)
$font-primary: 'Roboto', 'Inter var', -apple-system, BlinkMacSystemFont, 
               'Segoe UI', Oxygen, Ubuntu, sans-serif;

// Monospace - For IDs, codes, technical data
$font-mono: 'JetBrains Mono', 'Roboto Mono', 'SF Mono', Monaco, 
            'Cascadia Code', monospace;

// Data Tables - Optimized for scanning
$font-data: 'Roboto', 'IBM Plex Sans', -apple-system, sans-serif;
```

### Vuetify Typography Classes
```html
<!-- Material Design Typography Scale -->
<h1 class="text-h1">Heading 1 (96px)</h1>
<h2 class="text-h2">Heading 2 (60px)</h2>
<h3 class="text-h3">Heading 3 (48px)</h3>
<h4 class="text-h4">Heading 4 (34px)</h4>
<h5 class="text-h5">Heading 5 (24px)</h5>
<h6 class="text-h6">Heading 6 (20px)</h6>

<p class="text-subtitle-1">Subtitle 1 (16px, medium)</p>
<p class="text-subtitle-2">Subtitle 2 (14px, medium)</p>
<p class="text-body-1">Body 1 (16px)</p>
<p class="text-body-2">Body 2 (14px)</p>
<p class="text-button">Button (14px, uppercase)</p>
<p class="text-caption">Caption (12px)</p>
<p class="text-overline">Overline (10px, uppercase)</p>
```

### Custom Type Scale for Data-Heavy UI
```scss
// Optimized for genetic data presentation
.text-gene-symbol {
  font-size: 1.125rem;  // 18px
  font-weight: 500;
  font-family: $font-mono;
  letter-spacing: 0.025em;
}

.text-evidence-score {
  font-size: 1.25rem;   // 20px
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.text-data-label {
  font-size: 0.75rem;   // 12px
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  opacity: 0.6;
}

.text-hgnc-id {
  font-family: $font-mono;
  font-size: 0.875rem;  // 14px
  letter-spacing: 0.025em;
}
```

### Font Weights (Vuetify)
```scss
.font-weight-thin { font-weight: 100; }
.font-weight-light { font-weight: 300; }
.font-weight-regular { font-weight: 400; }
.font-weight-medium { font-weight: 500; }
.font-weight-bold { font-weight: 700; }
.font-weight-black { font-weight: 900; }
```

### Text Utilities
```scss
// Vuetify text helpers
.text-uppercase { text-transform: uppercase; }
.text-lowercase { text-transform: lowercase; }
.text-capitalize { text-transform: capitalize; }
.text-truncate { 
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.text-no-wrap { white-space: nowrap; }
.text-break { 
  overflow-wrap: break-word;
  word-break: break-word;
}

// Text alignment
.text-left { text-align: left; }
.text-center { text-align: center; }
.text-right { text-align: right; }
.text-justify { text-align: justify; }

// Responsive alignment
.text-sm-left { @media (min-width: 600px) { text-align: left; } }
.text-md-center { @media (min-width: 960px) { text-align: center; } }
.text-lg-right { @media (min-width: 1264px) { text-align: right; } }
```

### Text Opacity (Material Design)
```scss
// Emphasis levels following Material Design guidelines
.text-high-emphasis { 
  opacity: var(--v-high-emphasis-opacity, 0.87); 
}
.text-medium-emphasis { 
  opacity: var(--v-medium-emphasis-opacity, 0.60); 
}
.text-disabled { 
  opacity: var(--v-disabled-opacity, 0.38); 
}

// Usage in components
.gene-card__label {
  @extend .text-caption;
  @extend .text-medium-emphasis;
  @extend .text-uppercase;
}
```

## Spacing System

### Vuetify Spacing Classes
```html
<!-- Margin and Padding: {property}{direction}-{size} -->
<!-- Properties: m (margin), p (padding) -->
<!-- Directions: t (top), b (bottom), l (left), r (right), 
                 s (start), e (end), x (horizontal), y (vertical), a (all) -->
<!-- Sizes: 0 to 16, n1 to n16 (negative), auto -->

<div class="ma-4">Margin all sides: 16px</div>
<div class="mt-2">Margin top: 8px</div>
<div class="px-6">Padding horizontal: 24px</div>
<div class="mb-n2">Negative margin bottom: -8px</div>
<div class="ml-auto">Margin left: auto</div>

<!-- Responsive spacing -->
<div class="pa-2 pa-md-4 pa-lg-6">Responsive padding</div>
```

### Spacing Scale (4px base unit)
```scss
// Vuetify spacing values
$spacer: 4px !default;
$spacers: (
  0: 0,
  1: $spacer * 1,    // 4px
  2: $spacer * 2,    // 8px
  3: $spacer * 3,    // 12px
  4: $spacer * 4,    // 16px
  5: $spacer * 5,    // 20px
  6: $spacer * 6,    // 24px
  7: $spacer * 7,    // 28px
  8: $spacer * 8,    // 32px
  9: $spacer * 9,    // 36px
  10: $spacer * 10,  // 40px
  11: $spacer * 11,  // 44px
  12: $spacer * 12,  // 48px
  13: $spacer * 13,  // 52px
  14: $spacer * 14,  // 56px
  15: $spacer * 15,  // 60px
  16: $spacer * 16,  // 64px
);
```

### Gap Utilities (Flexbox/Grid)
```html
<!-- Gap classes for flex and grid containers -->
<div class="d-flex ga-4">
  <div>Item 1</div>
  <div>Item 2</div>
</div>

<!-- Directional gaps -->
<div class="d-flex flex-column gap-y-3">
  <div>Row 1</div>
  <div>Row 2</div>
</div>
```

### Component Spacing Guidelines
```scss
// Standard component padding
.v-card { padding: 16px; }              // pa-4
.v-card-title { padding: 16px 16px 0; } // px-4 pt-4
.v-card-text { padding: 16px; }         // pa-4
.v-card-actions { padding: 8px 16px; }  // pa-2 px-4

// Data table spacing
.v-data-table {
  th { padding: 0 16px; }  // px-4
  td { padding: 0 16px; }  // px-4
}

// Form field spacing
.v-text-field { margin-bottom: 20px; }  // mb-5
.v-btn + .v-btn { margin-left: 8px; }   // ml-2
```

## Layout System

### Vuetify Grid System
```html
<!-- 12-column responsive grid -->
<v-container fluid>
  <v-row>
    <v-col cols="12" sm="6" md="4" lg="3">
      <!-- Responsive column -->
    </v-col>
  </v-row>
</v-row>

<!-- Column properties -->
<v-col 
  cols="12"      <!-- Mobile: full width -->
  sm="6"         <!-- Small: half width -->
  md="4"         <!-- Medium: one third -->
  lg="3"         <!-- Large: one quarter -->
  offset="2"     <!-- Offset by 2 columns -->
  order="2"      <!-- Display order -->
>
```

### Breakpoints (Vuetify 3)
```scss
// Vuetify responsive breakpoints
$grid-breakpoints: (
  'xs': 0,        // Extra small devices
  'sm': 600px,    // Small devices
  'md': 960px,    // Medium devices
  'lg': 1280px,   // Large devices
  'xl': 1920px,   // Extra large devices
  'xxl': 2560px   // Extra extra large
);

// Usage in classes
.hidden-sm-and-down  // Hidden on small and smaller
.hidden-md-and-up    // Hidden on medium and larger
.d-none d-md-block   // Hidden on mobile, visible on desktop
```

### Application Layout
```html
<!-- Standard Vuetify application structure -->
<v-app>
  <v-app-bar app>
    <!-- Top navigation -->
  </v-app-bar>
  
  <v-navigation-drawer app>
    <!-- Side navigation -->
  </v-navigation-drawer>
  
  <v-main>
    <v-container fluid>
      <!-- Main content -->
    </v-container>
  </v-main>
  
  <v-footer app>
    <!-- Footer content -->
  </v-footer>
</v-app>
```

### Container Variants
```html
<!-- Fluid container (full width) -->
<v-container fluid>
  <!-- Full width content -->
</v-container>

<!-- Fixed max-width container -->
<v-container>
  <!-- Centered content with max-width -->
</v-container>

<!-- Custom max-width -->
<v-container style="max-width: 1400px;">
  <!-- Custom width content -->
</v-container>
```

### Flex Utilities
```html
<!-- Flexbox layout helpers -->
<div class="d-flex">
  <div class="flex-grow-1">Grows to fill space</div>
  <div class="flex-shrink-0">Fixed width</div>
</div>

<!-- Alignment -->
<div class="d-flex align-center justify-space-between">
  <div>Left aligned</div>
  <div>Right aligned</div>
</div>

<!-- Direction -->
<div class="d-flex flex-column">
  <div>Stacked vertically</div>
  <div>Stacked vertically</div>
</div>

<!-- Responsive flex -->
<div class="d-flex flex-column flex-md-row">
  <!-- Stacked on mobile, horizontal on desktop -->
</div>
```

### Spacers
```html
<!-- v-spacer for distributing space -->
<v-row>
  <v-col>Left content</v-col>
  <v-spacer></v-spacer>
  <v-col>Right content</v-col>
</v-row>
```

## Component Patterns

### Homepage Design Principles

#### **Information Architecture**
```scss
// Hero Section - Single focused CTA
.hero-section {
  // Logo + Title alignment: horizontal flex layout
  .hero-title {
    display: flex;
    align-items: center;     // Proper vertical alignment
    justify-content: center; // Centered layout
    gap: 16px;              // Consistent spacing
  }
  
  // Simplified content hierarchy
  .hero-cta {
    margin-top: 32px;       // Single primary action only
  }
}

// Remove redundant sections
// ❌ Don't: Multiple "Browse Genes" links
// ✅ Do: Single "Explore Genes" CTA
```

#### **Content Reduction Strategy**
```scss
// Before: 6 sections (cluttered)
// After: 4 sections (focused)
.homepage-sections {
  .hero-section     { /* Primary entry point */ }
  .stats-compact    { /* Key metrics only */ }
  .key-benefits     { /* Value proposition */ }
  .data-sources     { /* Technical details */ }
  
  // Removed sections:
  // ❌ Quick Actions (redundant with hero)
  // ❌ Recent Activity (developer-focused)
}
```

### Cards
```scss
.card {
  background: white;
  border-radius: $radius-lg;
  border: 1px solid $gray-200;
  padding: $space-6;
  box-shadow: $shadow-sm;
  
  &:hover {
    box-shadow: $shadow-md;
    border-color: $gray-300;
  }
  
  // Dark mode
  .dark & {
    background: $dark-surface;
    border-color: $dark-border;
  }
}
```

### Buttons
```scss
// Primary Button
.btn-primary {
  background: $primary-500;
  color: white;
  padding: $space-2 $space-4;
  border-radius: $radius-md;
  font-weight: $font-medium;
  transition: all 0.2s;
  
  &:hover {
    background: $primary-600;
    transform: translateY(-1px);
    box-shadow: $shadow-md;
  }
  
  &:active {
    transform: translateY(0);
  }
}

// Button Sizes
.btn-sm { padding: $space-1.5 $space-3; font-size: $text-sm; }
.btn-md { padding: $space-2 $space-4; font-size: $text-base; }
.btn-lg { padding: $space-3 $space-6; font-size: $text-lg; }
```

### Data Tables - Enhanced for High-Density Data

#### **Density & Spacing Improvements**
```scss
.data-table {
  // Compact density for scientific data
  &.v-data-table {
    --v-table-row-height: 48px;     // Reduced from default 60px
    density: 'compact';              // Vuetify density prop
  }
  
  // Cell padding optimization
  .v-data-table__td {
    padding: 8px 12px;               // Reduced from 12px 16px
    height: 48px;                    // Fixed height for consistency
  }
  
  // Header styling
  .v-data-table__th {
    font-weight: 600;                // Medium weight for headers
    background: rgb(var(--v-theme-surface-light));
    border-bottom: 2px solid rgb(var(--v-theme-surface-variant));
  }
}
```

#### **Pagination Accessibility Pattern**
```scss
.gene-browser {
  // Top pagination controls (accessible without scrolling)
  .results-summary {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;             // Compact spacing
    
    .pagination-controls {
      display: flex;
      align-items: center;
      gap: 8px;
      
      .v-pagination {
        --v-pagination-item-size: 32px; // Compact pagination
      }
      
      .per-page-select {
        min-width: 100px;            // Minimal width
      }
    }
  }
  
  // Bottom pagination (minimal, reference only)
  .table-bottom {
    padding: 8px;                    // Minimal padding
    text-align: center;
    
    .page-indicator {
      font-size: 12px;              // Small reference text
      opacity: 0.6;
    }
  }
}
```

#### **Component Size System**
```scss
.data-components {
  // Chip sizes for dense layouts
  .v-chip {
    &--x-small {
      --v-chip-size: 20px;
      --v-chip-font-size: 11px;
    }
    
    &--small {
      --v-chip-size: 24px;
      --v-chip-font-size: 12px;
    }
  }
  
  // Evidence score display with tooltips
  .evidence-score-cell {
    text-align: center;
    
    .v-chip {
      cursor: help;                  // Indicates tooltip available
      font-variant-numeric: tabular-nums;
    }
    
    // Hide inline classification text
    // Use tooltips instead for cleaner display
  }
  
  // Progress indicators (normalized to actual data)
  .evidence-count-bar {
    .v-progress-linear {
      height: 2px;                   // Thin progress bar
      width: 32px;                   // Compact width
    }
  }
}
```

#### **Visual Hierarchy in Data**
```scss
.gene-table-content {
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
  
  // HGNC IDs - technical reference
  .hgnc-id {
    font-family: var(--font-mono);
    font-size: 12px;
    background: rgb(var(--v-theme-surface-variant));
    padding: 2px 6px;
    border-radius: 4px;
  }
  
  // Evidence scores - primary metric
  .evidence-score {
    font-weight: 600;
    font-size: 14px;               // Slightly larger for importance
  }
  
  // Data sources - secondary info
  .data-sources {
    .v-chip {
      font-size: 10px;             // Small, secondary information
      margin: 1px;
    }
  }
}
```

### Form Controls
```scss
.input {
  width: 100%;
  padding: $space-2 $space-3;
  border: 1px solid $gray-300;
  border-radius: $radius-md;
  font-size: $text-base;
  transition: all 0.2s;
  
  &:focus {
    outline: none;
    border-color: $primary-500;
    box-shadow: 0 0 0 3px rgba($primary-500, 0.1);
  }
  
  &::placeholder {
    color: $gray-400;
  }
}

// Floating label pattern
.input-group {
  position: relative;
  
  .input {
    padding-top: $space-5;
  }
  
  label {
    position: absolute;
    top: $space-2;
    left: $space-3;
    font-size: $text-xs;
    color: $gray-500;
    transition: all 0.2s;
  }
}
```

### Badges & Pills
```scss
.badge {
  display: inline-flex;
  align-items: center;
  padding: $space-0.5 $space-2;
  border-radius: $radius-full;
  font-size: $text-xs;
  font-weight: $font-medium;
  
  &--success {
    background: $success-100;
    color: $success-700;
  }
  
  &--warning {
    background: $warning-100;
    color: $warning-700;
  }
  
  &--score {
    min-width: 48px;
    justify-content: center;
    font-family: $font-mono;
  }
}
```

## Icons & Imagery

### Icon System - Material Design Icons (MDI)
```html
<!-- Vuetify uses Material Design Icons by default -->
<!-- Browse icons at: https://pictogrammers.com/library/mdi/ -->

<!-- Basic icon usage -->
<v-icon>mdi-home</v-icon>
<v-icon>mdi-dna</v-icon>
<v-icon>mdi-test-tube</v-icon>
<v-icon>mdi-microscope</v-icon>

<!-- Icon with size -->
<v-icon size="x-small">mdi-alert</v-icon>  <!-- 12px -->
<v-icon size="small">mdi-check</v-icon>    <!-- 16px -->
<v-icon size="default">mdi-search</v-icon> <!-- 24px -->
<v-icon size="large">mdi-database</v-icon> <!-- 28px -->
<v-icon size="x-large">mdi-dna</v-icon>    <!-- 36px -->

<!-- Icon with color -->
<v-icon color="primary">mdi-information</v-icon>
<v-icon color="success">mdi-check-circle</v-icon>
<v-icon color="error">mdi-alert-circle</v-icon>

<!-- In buttons -->
<v-btn prepend-icon="mdi-download">Export</v-btn>
<v-btn icon="mdi-filter-variant"></v-btn>
```

### Medical/Scientific Icons (MDI)
```scss
// Commonly used icons for genetics/medical UI
$icons-medical: (
  gene: 'mdi-dna',
  test: 'mdi-test-tube',
  research: 'mdi-microscope',
  hospital: 'mdi-hospital-box',
  medical: 'mdi-medical-bag',
  heart: 'mdi-heart-pulse',
  kidney: 'mdi-kidney', // Note: Custom icon may be needed
  database: 'mdi-database',
  chart: 'mdi-chart-line',
  filter: 'mdi-filter-variant',
  search: 'mdi-magnify',
  export: 'mdi-download',
  import: 'mdi-upload',
  settings: 'mdi-cog',
  user: 'mdi-account',
  panel: 'mdi-view-dashboard',
  evidence: 'mdi-file-document-check',
  link: 'mdi-link-variant',
  external: 'mdi-open-in-new'
);
```

### Icon Sizes (Vuetify)
```scss
// Vuetify icon size props
$icon-sizes: (
  'x-small': 12px,
  'small': 16px,
  'default': 24px,
  'large': 28px,
  'x-large': 36px
);

// Custom icon sizes
.v-icon {
  &--xs { font-size: 12px !important; }
  &--sm { font-size: 16px !important; }
  &--md { font-size: 20px !important; }
  &--lg { font-size: 24px !important; }
  &--xl { font-size: 32px !important; }
  &--2xl { font-size: 48px !important; }
}
```

### Custom SVG Icons
```vue
<!-- For specialized medical icons not in MDI -->
<template>
  <v-icon>
    <svg viewBox="0 0 24 24">
      <!-- Custom kidney icon path -->
      <path d="..." />
    </svg>
  </v-icon>
</template>

<!-- Or register custom icons -->
<script>
import { aliases, mdi } from 'vuetify/iconsets/mdi'

export default createVuetify({
  icons: {
    defaultSet: 'mdi',
    aliases: {
      ...aliases,
      kidney: 'custom:kidney', // Custom kidney icon
      genome: 'custom:genome', // Custom genome icon
    },
    sets: {
      custom: {
        component: CustomSvgIcon,
      },
    },
  },
})
</script>
```

### Data Visualization Colors
```scss
// Categorical palette for charts
$chart-colors: (
  $primary-500,
  #F59E0B,  // Amber
  #8B5CF6,  // Violet
  #10B981,  // Emerald
  #F43F5E,  // Rose
  #3B82F6,  // Blue
  #6366F1,  // Indigo
  #EC4899,  // Pink
);

// Sequential palette for heatmaps
$heat-colors: (
  #F0F9FF,  // Lightest
  #BAE6FD,
  #38BDF8,
  #0284C7,
  #075985,  // Darkest
);
```

## Motion & Transitions

### Timing Functions
```scss
$ease-in-out: cubic-bezier(0.4, 0, 0.2, 1);
$ease-out: cubic-bezier(0, 0, 0.2, 1);
$ease-in: cubic-bezier(0.4, 0, 1, 1);
$spring: cubic-bezier(0.175, 0.885, 0.32, 1.275);
```

### Duration Scale
```scss
$duration-75:  75ms;   // Micro interactions
$duration-150: 150ms;  // Default transitions
$duration-200: 200ms;  // Hover states
$duration-300: 300ms;  // Page transitions
$duration-500: 500ms;  // Complex animations
```

### Standard Transitions
```scss
// Default transition
$transition-base: all $duration-150 $ease-in-out;

// Specific transitions
$transition-colors: colors $duration-150 $ease-in-out;
$transition-transform: transform $duration-200 $ease-out;
$transition-shadow: box-shadow $duration-200 $ease-in-out;
```

### Loading States
```scss
// Skeleton loader pulse
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.skeleton {
  animation: pulse 2s $ease-in-out infinite;
  background: linear-gradient(
    90deg,
    $gray-200 25%,
    $gray-100 50%,
    $gray-200 75%
  );
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}

// Progress indicator
.progress-bar {
  height: 4px;
  background: $primary-500;
  animation: progress 2s $ease-in-out;
}
```

## Shadows & Elevation

```scss
$shadow-xs: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
$shadow-sm: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 
            0 1px 2px 0 rgba(0, 0, 0, 0.06);
$shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 
            0 2px 4px -1px rgba(0, 0, 0, 0.06);
$shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 
            0 4px 6px -2px rgba(0, 0, 0, 0.05);
$shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 
            0 10px 10px -5px rgba(0, 0, 0, 0.04);
$shadow-2xl: 0 25px 50px -12px rgba(0, 0, 0, 0.25);

// Elevation system
.elevation-1 { box-shadow: $shadow-sm; }
.elevation-2 { box-shadow: $shadow-md; }
.elevation-3 { box-shadow: $shadow-lg; }
.elevation-4 { box-shadow: $shadow-xl; }
```

## Border Radius

```scss
$radius-none: 0;
$radius-sm: 0.125rem;  // 2px
$radius-md: 0.375rem;  // 6px
$radius-lg: 0.5rem;    // 8px
$radius-xl: 0.75rem;   // 12px
$radius-2xl: 1rem;     // 16px
$radius-3xl: 1.5rem;   // 24px
$radius-full: 9999px;  // Pills
```

## Responsive Breakpoints

```scss
$breakpoint-xs: 475px;   // Mobile
$breakpoint-sm: 640px;   // Large mobile
$breakpoint-md: 768px;   // Tablet
$breakpoint-lg: 1024px;  // Desktop
$breakpoint-xl: 1280px;  // Large desktop
$breakpoint-2xl: 1536px; // Wide screen

// Media query mixins
@mixin responsive($breakpoint) {
  @media (min-width: $breakpoint) {
    @content;
  }
}

// Usage
.component {
  padding: $space-4;
  
  @include responsive($breakpoint-lg) {
    padding: $space-6;
  }
}
```

## Accessibility Guidelines

### Color Contrast
- **Normal text**: Minimum 4.5:1 contrast ratio
- **Large text**: Minimum 3:1 contrast ratio
- **Interactive elements**: Minimum 3:1 against background
- **Focus indicators**: Minimum 3:1 contrast

### Focus States
```scss
.focusable {
  &:focus-visible {
    outline: 2px solid $primary-500;
    outline-offset: 2px;
    border-radius: $radius-sm;
  }
}

// High contrast mode
@media (prefers-contrast: high) {
  .focusable:focus-visible {
    outline-width: 3px;
  }
}
```

### Motion Preferences
```scss
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

## Implementation Examples

### Vue Component Structure
```vue
<template>
  <div class="gene-card">
    <div class="gene-card__header">
      <h3 class="gene-card__title">{{ gene.symbol }}</h3>
      <Badge :score="gene.score" />
    </div>
    <div class="gene-card__body">
      <DataField label="HGNC ID" :value="gene.hgnc_id" />
      <DataField label="Evidence" :value="gene.evidence_count" />
    </div>
    <div class="gene-card__footer">
      <Button variant="primary" size="sm">View Details</Button>
    </div>
  </div>
</template>

<style scoped lang="scss">
.gene-card {
  @include card;
  
  &__header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: $space-4;
    padding-bottom: $space-3;
    border-bottom: 1px solid $gray-200;
  }
  
  &__title {
    @include heading-3;
    margin: 0;
  }
  
  &__body {
    display: grid;
    gap: $space-3;
  }
  
  &__footer {
    margin-top: $space-4;
    padding-top: $space-3;
    border-top: 1px solid $gray-100;
  }
}
</style>
```

### Vuetify Theme Configuration
```js
// vuetify.config.js
export default {
  theme: {
    defaultTheme: 'light',
    themes: {
      light: {
        dark: false,
        colors: {
          primary: '#0EA5E9',
          secondary: '#8B5CF6',
          success: '#10B981',
          warning: '#F59E0B',
          error: '#EF4444',
          info: '#3B82F6',
          background: '#FAFAFA',
          surface: '#FFFFFF',
          'on-surface': '#18181B',
        }
      },
      dark: {
        dark: true,
        colors: {
          primary: '#38BDF8',
          secondary: '#A78BFA',
          success: '#34D399',
          warning: '#FCD34D',
          error: '#F87171',
          info: '#60A5FA',
          background: '#0F0F11',
          surface: '#1A1A1D',
          'on-surface': '#F4F4F5',
        }
      }
    }
  }
}
```

### CSS Custom Properties
```css
:root {
  /* Colors */
  --color-primary: #0EA5E9;
  --color-surface: #FFFFFF;
  --color-text: #18181B;
  
  /* Spacing */
  --space-unit: 4px;
  --space-xs: calc(var(--space-unit) * 1);
  --space-sm: calc(var(--space-unit) * 2);
  --space-md: calc(var(--space-unit) * 4);
  --space-lg: calc(var(--space-unit) * 6);
  --space-xl: calc(var(--space-unit) * 8);
  
  /* Typography */
  --font-primary: 'Inter var', sans-serif;
  --font-mono: 'JetBrains Mono', monospace;
  
  /* Transitions */
  --transition-base: all 150ms cubic-bezier(0.4, 0, 0.2, 1);
  
  /* Shadows */
  --shadow-sm: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
  --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  
  /* Borders */
  --radius-sm: 2px;
  --radius-md: 6px;
  --radius-lg: 8px;
}

/* Dark mode overrides */
[data-theme="dark"] {
  --color-primary: #38BDF8;
  --color-surface: #1A1A1D;
  --color-text: #F4F4F5;
}
```

## Component Library Integration

### Recommended Libraries
1. **Vuetify 3** - Material Design components
2. **Headless UI** - Unstyled accessible components
3. **Radix Vue** - Low-level UI primitives
4. **Floating UI** - Positioning engine

### Custom Component Checklist
- [ ] Follows spacing system (4px grid)
- [ ] Uses design tokens (colors, typography)
- [ ] Includes hover, focus, active states
- [ ] Supports light and dark modes
- [ ] Meets WCAG 2.1 AA standards
- [ ] Has loading and error states
- [ ] Includes proper ARIA labels
- [ ] Responsive across breakpoints
- [ ] Follows BEM naming convention
- [ ] Documented with examples

## Design Tokens Export

```json
{
  "color": {
    "primary": {
      "50": "#F0F9FF",
      "500": "#0EA5E9",
      "600": "#0284C7",
      "700": "#0369A1"
    },
    "gray": {
      "50": "#FAFAFA",
      "100": "#F4F4F5",
      "200": "#E4E4E7",
      "300": "#D4D4D8",
      "400": "#A1A1AA",
      "500": "#71717A",
      "600": "#52525B",
      "700": "#3F3F46",
      "800": "#27272A",
      "900": "#18181B"
    }
  },
  "spacing": {
    "0": "0px",
    "1": "4px",
    "2": "8px",
    "3": "12px",
    "4": "16px",
    "5": "20px",
    "6": "24px",
    "8": "32px",
    "10": "40px",
    "12": "48px",
    "16": "64px"
  },
  "fontSize": {
    "xs": "12px",
    "sm": "14px",
    "base": "16px",
    "lg": "18px",
    "xl": "21px",
    "2xl": "28px",
    "3xl": "38px"
  },
  "borderRadius": {
    "sm": "2px",
    "md": "6px",
    "lg": "8px",
    "xl": "12px",
    "full": "9999px"
  }
}
```

## UX Principles & Patterns

### Information Architecture
```scss
// Single path to action - avoid decision paralysis
.homepage-cta {
  // ❌ Don't: Multiple identical CTAs
  // "Browse Genes", "View All Genes", "Start Searching" → /genes
  
  // ✅ Do: Single clear action
  // "Explore Genes" → /genes (with built-in search/browse)
}

// Content hierarchy for scientific interfaces
.content-structure {
  .primary-action    { /* Single focused CTA */ }
  .key-metrics      { /* Essential statistics */ }
  .value-props      { /* Why use this? */ }
  .technical-details { /* How it works */ }
  
  // Remove: redundant sections, developer logs, duplicate info
}
```

### Logo & Title Alignment
```scss
.brand-lockup {
  // Proper horizontal alignment
  display: flex;
  align-items: center;              // Baseline alignment
  justify-content: center;
  gap: 16px;                       // Consistent spacing
  
  .logo {
    flex-shrink: 0;                // Prevent logo compression
    width: 80px;                   // Proportional to text
  }
  
  .title {
    font-size: clamp(1.5rem, 4vw, 3rem); // Responsive scaling
    line-height: 1.1;              // Tight line height
    margin: 0;                     // Remove default margins
  }
}
```

### Data Table UX Patterns
```scss
.data-table-ux {
  // Pagination accessibility - always visible
  .pagination-top {
    position: sticky;
    top: 0;
    background: white;
    z-index: 5;
    
    // Users shouldn't scroll to change pages
    .controls {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
  }
  
  // Evidence normalization - relative to actual data
  .progress-indicators {
    // ❌ Don't: Hardcoded maximum (e.g., /20)
    // ✅ Do: Dynamic maximum from current dataset
    max-value: Math.max(...genes.map(g => g.evidence_count));
  }
  
  // Tooltip over inline text for classifications
  .evidence-classifications {
    // ❌ Don't: "20.9 Disputed" inline text
    // ✅ Do: "20.9" with tooltip showing "Disputed"
    .tooltip-trigger {
      cursor: help;
      border-bottom: 1px dotted;
    }
  }
}
```

### Component Density Guidelines
```scss
.density-system {
  // Default: Comfortable for content consumption
  .v-component { density: 'default'; }
  
  // Compact: For data-heavy interfaces
  .data-interface { density: 'compact'; }
  
  // Comfortable: For forms and primary interactions
  .form-interface { density: 'comfortable'; }
  
  // Size scale for chips in data tables
  .chip-sizes {
    primary-data:   'small';      // Evidence scores
    secondary-data: 'x-small';    // Sources, counts
    meta-data:      'x-small';    // Tags, labels
  }
}
```

## Usage Guidelines

### Do's - Enhanced
- ✅ Use consistent spacing from the scale
- ✅ Apply semantic colors for meaning
- ✅ Maintain visual hierarchy with typography
- ✅ Test in both light and dark modes
- ✅ Ensure 44px minimum touch targets
- ✅ Use system fonts for performance
- ✅ Apply transitions for state changes
- ✅ **Single path to primary actions** (avoid duplicate CTAs)
- ✅ **Top-accessible pagination** (no scrolling required)
- ✅ **Tooltips for secondary information** (keep UI clean)
- ✅ **Normalize progress bars to actual data** (not arbitrary maxes)
- ✅ **Horizontal logo-title alignment** (professional appearance)

### Don'ts - Enhanced
- ❌ Create one-off colors outside the palette
- ❌ Use more than 2 font families per page
- ❌ Apply shadows to small elements
- ❌ Mix border radius styles
- ❌ Use pure black (#000) for text
- ❌ Forget focus states
- ❌ Ignore loading states
- ❌ **Multiple CTAs for same action** (Browse/Search/View All → same page)
- ❌ **Pagination only at bottom** (forces unnecessary scrolling)
- ❌ **Inline classification text** (clutters data display)
- ❌ **Hardcoded progress maximums** (misleading relative values)
- ❌ **Vertically stacked logo-title** (looks misaligned)

## Tools & Resources

### Design Tools
- **Figma**: Component library and prototypes
- **Storybook**: Component documentation
- **Chromatic**: Visual regression testing

### Development Tools
- **Vite**: Build tool with CSS processing
- **PostCSS**: CSS transformations
- **Stylelint**: CSS linting
- **PurgeCSS**: Remove unused styles

### Accessibility Tools
- **axe DevTools**: Accessibility testing
- **WAVE**: Web accessibility evaluation
- **Contrast**: Color contrast checker

## Vuetify-Specific Implementation Notes

### Theme Switching
```javascript
// Using Vuetify's theme API
import { useTheme } from 'vuetify'

const theme = useTheme()

// Toggle between light/dark
theme.toggle()

// Change to specific theme
theme.change('dark')

// Cycle through themes
theme.cycle(['light', 'dark', 'system'])

// Access current theme
const currentTheme = theme.current.value
```

### Custom Component Styling
```scss
// Override Vuetify component variables
.v-btn {
  --v-btn-height: 40px;
  --v-btn-border-radius: 8px;
}

// Custom density for data-heavy UI
.v-data-table {
  --v-table-row-height: 48px;
}

// Evidence score chip styling
.evidence-chip {
  &--high {
    .v-chip {
      background-color: rgb(var(--v-theme-success));
    }
  }
  &--medium {
    .v-chip {
      background-color: rgb(var(--v-theme-warning));
    }
  }
  &--low {
    .v-chip {
      background-color: rgb(var(--v-theme-error));
    }
  }
}
```

### Performance Optimizations
```javascript
// Lazy load heavy components
const GeneNetworkVisualization = () => import('./components/GeneNetworkVisualization.vue')

// Virtual scrolling for large datasets
<v-virtual-scroll
  :items="genes"
  :item-height="64"
  height="600"
>
  <template v-slot:default="{ item }">
    <GeneListItem :gene="item" />
  </template>
</v-virtual-scroll>
```

## Version History

- **v1.0.0** (2025-01-16): Initial design system
- **v1.1.0** (2025-01-16): Added Vuetify 3 integration guidelines  
- **v1.2.0** (2025-01-16): Major UX improvements based on comprehensive audit
  - **Homepage redesign**: Removed duplicate CTAs, simplified information architecture
  - **Logo alignment**: Fixed horizontal logo+title layout pattern
  - **Data table density**: Implemented compact spacing and component sizing
  - **Pagination accessibility**: Top-accessible controls, no scrolling required
  - **Evidence display**: Tooltips for classifications, normalized progress bars
  - **Component sizing**: Systematic x-small/small chip scale for data interfaces
  - **Content reduction**: Eliminated redundant sections and decision paralysis
- Future updates will be documented here

---

*This style guide is a living document. Updates should be reviewed by the design team and documented with version changes.*