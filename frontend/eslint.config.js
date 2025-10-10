import js from '@eslint/js'
import pluginVue from 'eslint-plugin-vue'
import prettierConfig from '@vue/eslint-config-prettier'

export default [
  js.configs.recommended,
  ...pluginVue.configs['flat/recommended'],
  prettierConfig,
  {
    files: ['**/*.{js,mjs,cjs,vue}'],
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      globals: {
        console: 'readonly',
        process: 'readonly',
        localStorage: 'readonly',
        setTimeout: 'readonly',
        clearTimeout: 'readonly',
        setInterval: 'readonly',
        clearInterval: 'readonly',
        window: 'readonly',
        navigator: 'readonly',
        document: 'readonly',
        URL: 'readonly',
        URLSearchParams: 'readonly',
        Blob: 'readonly',
        WebSocket: 'readonly',
        fetch: 'readonly',
        confirm: 'readonly',
        CustomEvent: 'readonly',
        __APP_VERSION__: 'readonly'
      }
    },
    rules: {
      'vue/multi-word-component-names': 'off',
      'vue/no-v-html': 'off',
      'no-unused-vars': ['warn', { argsIgnorePattern: '^_' }],
      'vue/require-default-prop': 'off',
      'vue/valid-v-slot': 'off' // Disabled due to false positives with dot notation in slot names
    }
  },
  {
    ignores: ['dist/*', 'node_modules/*', '*.config.js']
  }
]