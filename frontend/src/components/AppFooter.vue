<template>
  <v-footer app class="bg-surface-light py-1">
    <v-container class="py-0">
      <v-row align="center" justify="space-between" class="py-0 ma-0">
        <!-- Left: Version Information -->
        <v-col cols="auto" class="py-0">
          <v-menu location="top" :close-on-content-click="false">
            <template #activator="{ props: menuProps }">
              <v-btn variant="text" size="small" class="text-caption" v-bind="menuProps">
                <v-icon icon="mdi-information-outline" size="small" start />
                v{{ frontendVersion }}
              </v-btn>
            </template>

            <v-card min-width="320" class="pa-0">
              <v-card-title class="text-subtitle-2 font-weight-bold">
                Component Versions
              </v-card-title>

              <v-divider />

              <v-list density="compact" class="pa-0">
                <!-- Frontend Version -->
                <v-list-item>
                  <template #prepend>
                    <v-icon icon="mdi-vuejs" color="success" />
                  </template>
                  <v-list-item-title class="text-caption font-weight-medium">
                    Frontend
                  </v-list-item-title>
                  <v-list-item-subtitle class="text-caption">
                    v{{ frontendVersion }} • Vue.js
                  </v-list-item-subtitle>
                </v-list-item>

                <v-divider />

                <!-- Backend Version -->
                <v-list-item>
                  <template #prepend>
                    <v-icon
                      icon="mdi-server"
                      :color="backendVersion === 'unknown' ? 'error' : 'primary'"
                    />
                  </template>
                  <v-list-item-title class="text-caption font-weight-medium">
                    Backend
                  </v-list-item-title>
                  <v-list-item-subtitle class="text-caption">
                    v{{ backendVersion }} • FastAPI
                  </v-list-item-subtitle>
                </v-list-item>

                <v-divider />

                <!-- Database Version -->
                <v-list-item>
                  <template #prepend>
                    <v-icon
                      icon="mdi-database"
                      :color="databaseVersion === 'unknown' ? 'error' : 'info'"
                    />
                  </template>
                  <v-list-item-title class="text-caption font-weight-medium">
                    Database
                  </v-list-item-title>
                  <v-list-item-subtitle class="text-caption">
                    v{{ databaseVersion }} • PostgreSQL
                  </v-list-item-subtitle>
                </v-list-item>

                <v-divider />

                <!-- Environment Badge -->
                <v-list-item>
                  <template #prepend>
                    <v-icon icon="mdi-cloud-outline" :color="environmentColor" />
                  </template>
                  <v-list-item-title class="text-caption font-weight-medium">
                    Environment
                  </v-list-item-title>
                  <v-list-item-subtitle class="text-caption">
                    {{ environment }}
                  </v-list-item-subtitle>
                </v-list-item>
              </v-list>

              <v-divider />

              <v-card-actions class="pa-2">
                <v-btn
                  size="x-small"
                  variant="text"
                  prepend-icon="mdi-refresh"
                  :loading="loading"
                  @click="refreshVersions"
                >
                  Refresh
                </v-btn>
                <v-spacer />
                <div class="text-caption text-medium-emphasis">
                  Updated: {{ formattedTimestamp }}
                </div>
              </v-card-actions>
            </v-card>
          </v-menu>
        </v-col>

        <!-- Right: Quick Links -->
        <v-col cols="12" sm="auto" class="text-right py-0">
          <v-btn
            icon="mdi-github"
            size="small"
            variant="text"
            href="https://github.com"
            target="_blank"
            title="GitHub"
          />
          <v-btn
            icon="mdi-file-document"
            size="small"
            variant="text"
            to="/about"
            title="Documentation"
          />
          <v-btn
            size="small"
            variant="text"
            :title="`Open Log Viewer (Ctrl+Shift+L) - ${logStore.errorCount} errors`"
            @click="logStore.showViewer"
          >
            <v-badge
              :content="logStore.errorCount"
              :model-value="logStore.errorCount > 0"
              color="error"
              dot
            >
              <v-icon>mdi-text-box-search-outline</v-icon>
            </v-badge>
          </v-btn>
        </v-col>
      </v-row>
    </v-container>
  </v-footer>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { getAllVersions, getFrontendVersion } from '@/utils/version'
import { useLogStore } from '@/stores/logStore'

const logStore = useLogStore()

// Reactive state
const loading = ref(false)
const frontendVersion = ref(getFrontendVersion())
const backendVersion = ref('...')
const databaseVersion = ref('...')
const environment = ref('...')
const timestamp = ref(null)

// Computed properties
const formattedTimestamp = computed(() => {
  if (!timestamp.value) return 'N/A'
  const date = new Date(timestamp.value)
  return date.toLocaleTimeString()
})

const environmentColor = computed(() => {
  const envMap = {
    production: 'success',
    staging: 'warning',
    development: 'info'
  }
  return envMap[environment.value?.toLowerCase()] || 'grey'
})

// Methods
async function refreshVersions() {
  loading.value = true
  try {
    const versions = await getAllVersions()

    frontendVersion.value = versions.frontend.version
    backendVersion.value = versions.backend.version
    databaseVersion.value = versions.database.version
    environment.value = versions.environment
    timestamp.value = versions.timestamp
  } catch (error) {
    console.error('Failed to refresh versions:', error)
    backendVersion.value = 'error'
    databaseVersion.value = 'error'
  } finally {
    loading.value = false
  }
}

// Lifecycle
onMounted(() => {
  refreshVersions()
})
</script>

<style scoped>
/* Following Style Guide - Compact density for footer */
.app-footer {
  min-height: 48px;
  z-index: 1000;
}

/* Ensure buttons have proper focus states - Following Style Guide */
.v-btn:focus-visible {
  outline: 2px solid rgb(var(--v-theme-primary));
  outline-offset: 2px;
}
</style>
