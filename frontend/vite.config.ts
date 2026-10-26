import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import { compression } from 'vite-plugin-compression2'
import { fileURLToPath, URL } from 'node:url'
import { readFileSync } from 'fs'

// Read version from package.json
const packageJson = JSON.parse(
  readFileSync(new URL('./package.json', import.meta.url), 'utf-8')
)

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    tailwindcss(),
    vue(),
    // gzip + brotli by default. HTML is excluded: this runs before vite-ssg prerenders and
    // the entrypoint injects env-config.js, so a .html.gz would be a stale SPA shell (#312).
    compression({ exclude: [/\.html$/] }),
  ],
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
    // Load the full stylesheet normally; async-swapped critical CSS caused layout shift (#313)
    beastiesOptions: false,
    includedRoutes(paths) {
      // Only prerender public static pages (not dynamic gene pages or auth/admin routes)
      return paths.filter(
        (p) =>
          !p.startsWith('/admin') &&
          !p.startsWith('/login') &&
          !p.startsWith('/profile') &&
          !p.startsWith('/forgot-password') &&
          !p.startsWith('/curation') && // data loads client-side only
          !p.includes(':')
      )
    }
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          // vite-ssg externalises vue/pinia during SSR — use a function
          // to avoid EXTERNAL_MODULES_CANNOT_BE_INCLUDED_IN_MANUAL_CHUNKS
          if (id.includes('node_modules/vue/') || id.includes('node_modules/vue-router/') || id.includes('node_modules/pinia/')) {
            return 'vendor-vue'
          }
          if (id.includes('node_modules/d3-')) {
            return 'vendor-d3'
          }
          if (id.includes('node_modules/cytoscape/')) {
            return 'vendor-cytoscape'
          }
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