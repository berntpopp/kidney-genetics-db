# Frontend Implementation Plan (Lean Vue/Vuetify)

## Overview

Simple Vue 3 + Vuetify frontend for browsing and searching kidney genetics data with clean Material Design UI.

## Architecture

### Technology Stack
- **Framework**: Vue 3 with Composition API
- **UI Library**: Vuetify 3 (Material Design)
- **Build Tool**: Vite (fast dev server)
- **HTTP Client**: Axios for API calls
- **State Management**: Simple reactive stores (no Pinia needed for MVP)

### Project Structure
```
frontend/
├── src/
│   ├── api/
│   │   └── client.js           # Axios setup
│   ├── components/
│   │   ├── GeneTable.vue       # Main gene list table
│   │   ├── GeneDetail.vue      # Gene detail view
│   │   ├── SearchBar.vue       # Search/filter component
│   │   ├── ExportDialog.vue    # Export options
│   │   └── PipelineStatus.vue  # Pipeline run status
│   ├── views/
│   │   ├── Home.vue            # Dashboard/stats
│   │   ├── Genes.vue           # Gene browser
│   │   ├── About.vue           # Project info
│   │   └── Admin.vue           # Pipeline controls
│   ├── router/
│   │   └── index.js            # Vue Router setup
│   ├── App.vue                 # Root component
│   └── main.js                 # App entry point
├── public/
│   └── index.html
├── package.json
├── vite.config.js
└── Dockerfile
```

## Core Components

### 1. Main Application Setup

```javascript
// src/main.js
import { createApp } from 'vue'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import 'vuetify/styles'
import App from './App.vue'
import router from './router'

const vuetify = createVuetify({
  components,
  directives,
  theme: {
    defaultTheme: 'light'
  }
})

createApp(App)
  .use(router)
  .use(vuetify)
  .mount('#app')
```

### 2. API Client

```javascript
// src/api/client.js
import axios from 'axios'

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api',
  headers: {
    'Content-Type': 'application/json'
  }
})

// Add auth token if exists
apiClient.interceptors.request.use(config => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export default {
  // Genes
  getGenes(params) {
    return apiClient.get('/genes', { params })
  },
  getGene(symbol) {
    return apiClient.get(`/genes/${symbol}`)
  },
  
  // Export
  exportData(format) {
    return apiClient.get(`/export/${format}`, { responseType: 'blob' })
  },
  
  // Pipeline
  runPipeline() {
    return apiClient.post('/pipeline/run')
  },
  getPipelineStatus() {
    return apiClient.get('/pipeline/status')
  }
}
```

### 3. Gene Table Component

```vue
<!-- src/components/GeneTable.vue -->
<template>
  <v-card>
    <v-card-title>
      <v-text-field
        v-model="search"
        prepend-inner-icon="mdi-magnify"
        label="Search genes..."
        single-line
        hide-details
        clearable
        @input="debouncedSearch"
      />
    </v-card-title>
    
    <v-data-table
      :headers="headers"
      :items="genes"
      :loading="loading"
      :server-items-length="totalGenes"
      :options.sync="options"
      @click:row="showGeneDetail"
    >
      <template v-slot:item.evidence_score="{ item }">
        <v-chip
          :color="getScoreColor(item.evidence_score)"
          dark
          small
        >
          {{ item.evidence_score?.toFixed(1) }}
        </v-chip>
      </template>
      
      <template v-slot:item.source_count="{ item }">
        <v-tooltip bottom>
          <template v-slot:activator="{ on }">
            <span v-on="on">{{ item.source_count }}</span>
          </template>
          <span>
            PanelApp: {{ item.panelapp_panels?.length || 0 }}<br>
            Literature: {{ item.literature_refs?.length || 0 }}<br>
            Diagnostic: {{ item.diagnostic_panels?.length || 0 }}<br>
            HPO: {{ item.hpo_terms?.length || 0 }}<br>
            PubTator: {{ item.pubtator_pmids?.length || 0 }}
          </span>
        </v-tooltip>
      </template>
    </v-data-table>
  </v-card>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/api/client'
import { debounce } from 'lodash-es'

const router = useRouter()
const genes = ref([])
const loading = ref(false)
const search = ref('')
const totalGenes = ref(0)

const headers = [
  { text: 'Symbol', value: 'approved_symbol', sortable: true },
  { text: 'HGNC ID', value: 'hgnc_id', sortable: false },
  { text: 'Evidence Score', value: 'evidence_score', sortable: true },
  { text: 'Sources', value: 'source_count', sortable: true },
  { text: 'Classification', value: 'classification', sortable: false }
]

const options = ref({
  page: 1,
  itemsPerPage: 25,
  sortBy: ['evidence_score'],
  sortDesc: [true]
})

const fetchGenes = async () => {
  loading.value = true
  try {
    const { data } = await api.getGenes({
      skip: (options.value.page - 1) * options.value.itemsPerPage,
      limit: options.value.itemsPerPage,
      search: search.value,
      sort_by: options.value.sortBy[0],
      sort_desc: options.value.sortDesc[0]
    })
    genes.value = data.items
    totalGenes.value = data.total
  } catch (error) {
    console.error('Failed to fetch genes:', error)
  } finally {
    loading.value = false
  }
}

const debouncedSearch = debounce(fetchGenes, 300)

const showGeneDetail = (gene) => {
  router.push(`/genes/${gene.approved_symbol}`)
}

const getScoreColor = (score) => {
  if (score >= 8) return 'green'
  if (score >= 5) return 'orange'
  return 'grey'
}

watch(options, fetchGenes, { deep: true })

// Initial load
fetchGenes()
</script>
```

### 4. Simple Dashboard

```vue
<!-- src/views/Home.vue -->
<template>
  <v-container>
    <h1 class="text-h3 mb-4">Kidney Genetics Database</h1>
    
    <v-row>
      <v-col cols="12" md="3">
        <v-card>
          <v-card-text class="text-center">
            <div class="text-h2">{{ stats.total_genes }}</div>
            <div class="text-subtitle-1">Total Genes</div>
          </v-card-text>
        </v-card>
      </v-col>
      
      <v-col cols="12" md="3">
        <v-card>
          <v-card-text class="text-center">
            <div class="text-h2">{{ stats.high_confidence }}</div>
            <div class="text-subtitle-1">High Confidence</div>
          </v-card-text>
        </v-card>
      </v-col>
      
      <v-col cols="12" md="3">
        <v-card>
          <v-card-text class="text-center">
            <div class="text-h2">5</div>
            <div class="text-subtitle-1">Data Sources</div>
          </v-card-text>
        </v-card>
      </v-col>
      
      <v-col cols="12" md="3">
        <v-card>
          <v-card-text class="text-center">
            <div class="text-h2">{{ lastUpdate }}</div>
            <div class="text-subtitle-1">Last Update</div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
    
    <v-row class="mt-4">
      <v-col>
        <v-btn
          color="primary"
          size="large"
          to="/genes"
        >
          Browse Genes
        </v-btn>
        
        <v-btn
          color="secondary"
          size="large"
          class="ml-2"
          @click="exportData"
        >
          Export Data
        </v-btn>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '@/api/client'

const stats = ref({
  total_genes: 0,
  high_confidence: 0
})

const lastUpdate = ref('Loading...')

onMounted(async () => {
  try {
    const { data } = await api.getGenes({ limit: 1 })
    stats.value.total_genes = data.total
    
    const highConf = await api.getGenes({ min_score: 8.0, limit: 1 })
    stats.value.high_confidence = highConf.data.total
    
    const status = await api.getPipelineStatus()
    lastUpdate.value = new Date(status.data.completed_at).toLocaleDateString()
  } catch (error) {
    console.error('Failed to load stats:', error)
  }
})

const exportData = async () => {
  try {
    const blob = await api.exportData('csv')
    const url = window.URL.createObjectURL(blob.data)
    const link = document.createElement('a')
    link.href = url
    link.download = `kidney_genes_${new Date().toISOString().split('T')[0]}.csv`
    link.click()
  } catch (error) {
    console.error('Export failed:', error)
  }
}
</script>
```

## Docker Setup

```dockerfile
# Dockerfile
FROM node:18-alpine as builder

WORKDIR /app
COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
```

```nginx
# nginx.conf
server {
    listen 80;
    root /usr/share/nginx/html;
    index index.html;
    
    location / {
        try_files $uri $uri/ /index.html;
    }
    
    location /api {
        proxy_pass http://backend:8000;
    }
}
```

## Key Features

1. **Gene Browser** - Sortable, searchable table with evidence scores
2. **Gene Details** - View all evidence sources for a gene
3. **Search & Filter** - Real-time search with score filtering
4. **Data Export** - Download CSV or JSON
5. **Simple Dashboard** - Key statistics at a glance

This lean frontend focuses on presenting kidney genetics data clearly without unnecessary complexity.