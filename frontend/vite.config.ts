import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import { fileURLToPath, URL } from 'node:url'
import { readFileSync } from 'fs'

// Read version from package.json
const packageJson = JSON.parse(
  readFileSync(new URL('./package.json', import.meta.url), 'utf-8')
)

// https://vite.dev/config/
export default defineConfig({
  plugins: [tailwindcss(), vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  define: {
    __APP_VERSION__: JSON.stringify(packageJson.version)
  },
  ssgOptions: {
    script: 'async',
    formatting: 'minify',
    dirStyle: 'nested',
    beastiesOptions: {
      preload: 'swap'
    },
    includedRoutes(paths) {
      // Only prerender public static pages (not dynamic gene pages or auth/admin routes)
      return paths.filter(
        (p) =>
          !p.startsWith('/admin') &&
          !p.startsWith('/login') &&
          !p.startsWith('/profile') &&
          !p.startsWith('/forgot-password') &&
          !p.includes(':')
      )
    }
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor-vue': ['vue', 'vue-router', 'pinia'],
          'vendor-tanstack': ['@tanstack/vue-table'],
          'vendor-d3': ['d3-selection', 'd3-scale', 'd3-shape', 'd3-axis', 'd3-array', 'd3-transition', 'd3-format', 'd3-color', 'd3-scale-chromatic', 'd3-interpolate', 'd3-zoom'],
          'vendor-cytoscape': ['cytoscape'],
        },
      },
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
})