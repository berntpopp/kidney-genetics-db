# Kidney Genetics Database - Design System

**Current Status**: Production implementation based on comprehensive UX audit (January 2025)

## Design Philosophy

### Core Principles
1. **Single Path to Action** - Eliminate decision paralysis with clear user journeys
2. **Information Hierarchy** - Essential data first, technical details accessible but not prominent  
3. **Density Optimization** - Compact layouts for data-heavy scientific interfaces
4. **Professional Trust** - Medical-grade interface design that respects genetic research
5. **Accessibility First** - Controls visible without scrolling, proper contrast, keyboard navigation

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