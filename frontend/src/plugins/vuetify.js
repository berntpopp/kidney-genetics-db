/**
 * Vuetify plugin configuration
 * Implements the Kidney Genetics Database visual design system
 */

import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'

export default createVuetify({
  components,
  directives,
  theme: {
    defaultTheme: 'light',
    variations: {
      colors: ['primary', 'secondary', 'success'],
      lighten: 3,
      darken: 2
    },
    themes: {
      light: {
        dark: false,
        colors: {
          // Core Brand Colors
          primary: '#0EA5E9', // Sky blue
          'primary-darken-1': '#0284C7',
          'primary-darken-2': '#0369A1',
          'primary-lighten-1': '#38BDF8',
          'primary-lighten-2': '#7DD3FC',
          'primary-lighten-3': '#F0F9FF',

          // Semantic Colors
          secondary: '#8B5CF6', // Violet
          'secondary-darken-1': '#7C3AED',
          'secondary-lighten-1': '#A78BFA',
          success: '#10B981', // Emerald
          'success-darken-1': '#059669',
          'success-lighten-1': '#34D399',
          warning: '#F59E0B', // Amber
          'warning-lighten-1': '#FCD34D',
          error: '#EF4444', // Red
          'error-lighten-1': '#F87171',
          info: '#3B82F6', // Blue
          'info-lighten-1': '#60A5FA',

          // Surface Colors
          background: '#FAFAFA',
          surface: '#FFFFFF',
          'surface-bright': '#FFFFFF',
          'surface-light': '#F4F4F5',
          'surface-variant': '#E4E4E7',
          'on-surface-variant': '#52525B',

          // Text Colors
          'on-background': '#18181B',
          'on-surface': '#27272A',
          'on-primary': '#FFFFFF',
          'on-secondary': '#FFFFFF',
          'on-error': '#FFFFFF',
          'on-info': '#FFFFFF',
          'on-success': '#FFFFFF',
          'on-warning': '#FFFFFF',

          // Medical/Scientific Colors
          'kidney-primary': '#14B8A6', // Teal
          'kidney-secondary': '#0D9488',
          'dna-primary': '#0EA5E9', // Sky Blue
          'dna-secondary': '#8B5CF6' // Violet
        },
        variables: {
          'border-color': '#E4E4E7',
          'border-opacity': 0.12,
          'high-emphasis-opacity': 0.87,
          'medium-emphasis-opacity': 0.6,
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
          'theme-on-code': '#000000'
        }
      },
      dark: {
        dark: true,
        colors: {
          // Core Brand Colors (Dark Mode)
          primary: '#38BDF8',
          'primary-darken-1': '#0EA5E9',
          'primary-darken-2': '#0284C7',
          'primary-lighten-1': '#7DD3FC',

          // Semantic Colors (Dark Mode)
          secondary: '#A78BFA',
          'secondary-darken-1': '#8B5CF6',
          success: '#34D399',
          'success-darken-1': '#10B981',
          warning: '#FCD34D',
          'warning-darken-1': '#F59E0B',
          error: '#F87171',
          'error-darken-1': '#EF4444',
          info: '#60A5FA',
          'info-darken-1': '#3B82F6',

          // Surface Colors (Dark Mode)
          background: '#0F0F11',
          surface: '#1A1A1D',
          'surface-bright': '#27272A',
          'surface-light': '#1F1F23',
          'surface-variant': '#2A2A2E',
          'on-surface-variant': '#E4E4E7',

          // Text Colors (Dark Mode)
          'on-background': '#F4F4F5',
          'on-surface': '#F4F4F5',
          'on-primary': '#0F0F11',
          'on-secondary': '#0F0F11',

          // Medical/Scientific Colors (Dark Mode)
          'kidney-primary': '#5EEAD4',
          'kidney-secondary': '#2DD4BF',
          'dna-primary': '#60A5FA',
          'dna-secondary': '#A78BFA'
        },
        variables: {
          'border-color': '#2A2A2E',
          'border-opacity': 0.15,
          'high-emphasis-opacity': 0.95,
          'medium-emphasis-opacity': 0.7,
          'disabled-opacity': 0.4
        }
      }
    }
  },
  defaults: {
    VCard: {
      elevation: 1,
      rounded: 'lg'
    },
    VBtn: {
      rounded: 'md',
      elevation: 0
    },
    VTextField: {
      variant: 'outlined',
      density: 'comfortable',
      rounded: 'md'
    },
    VDataTable: {
      density: 'comfortable'
    },
    VChip: {
      rounded: 'pill'
    }
  }
})
