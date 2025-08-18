<template>
  <div>
    <!-- Hero Section -->
    <v-container fluid class="pa-0">
      <div class="about-hero text-center py-12 px-4">
        <v-container>
          <KidneyGeneticsLogo :size="100" variant="full" :animated="true" class="mb-6" />
          <h1 class="text-h2 text-md-h1 font-weight-bold mb-4">About Our Project</h1>
          <p class="text-h6 text-md-h5 text-medium-emphasis mx-auto" style="max-width: 700px">
            Advancing nephrology research through comprehensive genetic data curation and
            evidence-based clinical insights
          </p>
        </v-container>
      </div>
    </v-container>

    <v-container class="mt-n8">
      <!-- Mission Statement -->
      <v-row class="mb-8">
        <v-col cols="12">
          <v-card class="mission-card" rounded="xl" elevation="3">
            <v-card-item class="pa-8">
              <div class="text-center">
                <v-icon icon="mdi-target" size="large" color="primary" class="mb-4" />
                <h2 class="text-h4 font-weight-medium mb-4">Our Mission</h2>
                <p class="text-h6 text-medium-emphasis mx-auto" style="max-width: 800px">
                  To provide researchers and clinicians worldwide with the most comprehensive,
                  accurate, and accessible database of kidney disease-related genetic information,
                  enabling precision medicine and accelerating therapeutic discoveries.
                </p>
              </div>
            </v-card-item>
          </v-card>
        </v-col>
      </v-row>

      <!-- Project Overview -->
      <v-row class="mb-8">
        <v-col cols="12" lg="8">
          <div class="mb-6">
            <div class="d-flex align-center mb-4">
              <v-icon icon="mdi-information" size="small" class="mr-2" color="primary" />
              <h2 class="text-h4 font-weight-medium">Project Overview</h2>
            </div>
            <v-card rounded="lg" class="overview-card">
              <v-card-text class="pa-6">
                <div class="text-body-1 mb-4" style="line-height: 1.7">
                  The Kidney Genetics Database represents a significant advancement in nephrology
                  research infrastructure. Our platform modernizes genetic data curation by
                  replacing legacy R-based pipelines with a scalable, cloud-native architecture
                  built on Python/FastAPI and Vue.js.
                </div>
                <div class="text-body-1 mb-4" style="line-height: 1.7">
                  We integrate data from multiple authoritative sources, applying sophisticated
                  evidence scoring algorithms to provide researchers with confidence levels for
                  gene-disease associations. Our GenCC-compatible schema ensures international
                  interoperability and supports regulatory compliance for clinical applications.
                </div>
                <div class="d-flex flex-wrap ga-2 mt-6">
                  <v-chip color="primary" variant="tonal" size="small">
                    <v-icon icon="mdi-shield-check" size="x-small" start />
                    GenCC Compatible
                  </v-chip>
                  <v-chip color="success" variant="tonal" size="small">
                    <v-icon icon="mdi-cloud-check" size="x-small" start />
                    Cloud Native
                  </v-chip>
                  <v-chip color="info" variant="tonal" size="small">
                    <v-icon icon="mdi-chart-line" size="x-small" start />
                    Evidence Scoring
                  </v-chip>
                  <v-chip color="secondary" variant="tonal" size="small">
                    <v-icon icon="mdi-api" size="x-small" start />
                    RESTful API
                  </v-chip>
                </div>
              </v-card-text>
            </v-card>
          </div>
        </v-col>
        <v-col cols="12" lg="4">
          <v-card rounded="lg" class="stats-card h-100">
            <v-card-item class="pa-6">
              <v-card-title class="text-h6 mb-4">Project Metrics</v-card-title>
              <v-list class="transparent">
                <v-list-item class="px-0">
                  <template #prepend>
                    <v-avatar color="primary" size="40" class="mr-3">
                      <v-icon icon="mdi-dna" color="white" />
                    </v-avatar>
                  </template>
                  <v-list-item-title class="text-h5 font-weight-bold">403</v-list-item-title>
                  <v-list-item-subtitle>Curated Genes</v-list-item-subtitle>
                </v-list-item>
                <v-list-item class="px-0">
                  <template #prepend>
                    <v-avatar color="success" size="40" class="mr-3">
                      <v-icon icon="mdi-database-check" color="white" />
                    </v-avatar>
                  </template>
                  <v-list-item-title class="text-h5 font-weight-bold">5</v-list-item-title>
                  <v-list-item-subtitle>Data Sources</v-list-item-subtitle>
                </v-list-item>
                <v-list-item class="px-0">
                  <template #prepend>
                    <v-avatar color="info" size="40" class="mr-3">
                      <v-icon icon="mdi-view-dashboard" color="white" />
                    </v-avatar>
                  </template>
                  <v-list-item-title class="text-h5 font-weight-bold">27</v-list-item-title>
                  <v-list-item-subtitle>Gene Panels</v-list-item-subtitle>
                </v-list-item>
              </v-list>
            </v-card-item>
          </v-card>
        </v-col>
      </v-row>

      <!-- Data Sources -->
      <v-row class="mb-8">
        <v-col cols="12">
          <div class="d-flex align-center mb-6">
            <v-icon icon="mdi-database" size="small" class="mr-2" color="primary" />
            <h2 class="text-h4 font-weight-medium">Data Sources & Integration</h2>
          </div>
          <v-row>
            <v-col v-for="source in dataSources" :key="source.name" cols="12" md="6" lg="4">
              <v-card
                class="source-card h-100"
                rounded="lg"
                :class="{ 'source-card--featured': source.featured }"
              >
                <v-card-item>
                  <template #prepend>
                    <v-avatar :color="source.color" size="48">
                      <v-icon :icon="source.icon" color="white" />
                    </v-avatar>
                  </template>
                  <v-card-title class="text-h6">{{ source.name }}</v-card-title>
                  <template v-if="source.featured" #append>
                    <v-chip color="primary" size="x-small" variant="flat">
                      <v-icon icon="mdi-star" size="x-small" start />
                      Primary
                    </v-chip>
                  </template>
                </v-card-item>
                <v-card-text class="pt-0">
                  <p class="text-body-2 mb-3">{{ source.description }}</p>
                  <div class="d-flex justify-space-between align-center">
                    <v-chip size="small" variant="tonal" :color="source.color">
                      {{ source.coverage }}
                    </v-chip>
                    <v-chip size="small" variant="outlined" prepend-icon="mdi-update">
                      {{ source.frequency }}
                    </v-chip>
                  </div>
                </v-card-text>
              </v-card>
            </v-col>
          </v-row>
        </v-col>
      </v-row>

      <!-- Technology & Architecture -->
      <v-row class="mb-8">
        <v-col cols="12">
          <div class="d-flex align-center mb-6">
            <v-icon icon="mdi-cog" size="small" class="mr-2" color="primary" />
            <h2 class="text-h4 font-weight-medium">Technology Stack</h2>
          </div>
          <v-row>
            <v-col cols="12" md="6">
              <v-card rounded="lg" class="tech-card">
                <v-card-item>
                  <template #prepend>
                    <v-avatar color="primary" size="40">
                      <v-icon icon="mdi-server" color="white" />
                    </v-avatar>
                  </template>
                  <v-card-title class="text-h6">Backend Architecture</v-card-title>
                </v-card-item>
                <v-card-text>
                  <v-list class="transparent" density="compact">
                    <v-list-item v-for="tech in backendTech" :key="tech.name">
                      <template #prepend>
                        <v-icon :icon="tech.icon" size="small" :color="tech.color" class="mr-2" />
                      </template>
                      <v-list-item-title class="text-body-2 font-weight-medium">
                        {{ tech.name }}
                      </v-list-item-title>
                      <v-list-item-subtitle>{{ tech.description }}</v-list-item-subtitle>
                    </v-list-item>
                  </v-list>
                </v-card-text>
              </v-card>
            </v-col>
            <v-col cols="12" md="6">
              <v-card rounded="lg" class="tech-card">
                <v-card-item>
                  <template #prepend>
                    <v-avatar color="secondary" size="40">
                      <v-icon icon="mdi-monitor" color="white" />
                    </v-avatar>
                  </template>
                  <v-card-title class="text-h6">Frontend Experience</v-card-title>
                </v-card-item>
                <v-card-text>
                  <v-list class="transparent" density="compact">
                    <v-list-item v-for="tech in frontendTech" :key="tech.name">
                      <template #prepend>
                        <v-icon :icon="tech.icon" size="small" :color="tech.color" class="mr-2" />
                      </template>
                      <v-list-item-title class="text-body-2 font-weight-medium">
                        {{ tech.name }}
                      </v-list-item-title>
                      <v-list-item-subtitle>{{ tech.description }}</v-list-item-subtitle>
                    </v-list-item>
                  </v-list>
                </v-card-text>
              </v-card>
            </v-col>
          </v-row>
        </v-col>
      </v-row>

      <!-- Team & Contact -->
      <v-row class="mb-8">
        <v-col cols="12" md="8" class="mx-auto">
          <v-card rounded="xl" class="contact-card">
            <v-card-item class="pa-8 text-center">
              <v-icon icon="mdi-account-group" size="x-large" color="primary" class="mb-4" />
              <h2 class="text-h4 font-weight-medium mb-4">Get Involved</h2>
              <p class="text-h6 text-medium-emphasis mb-6" style="max-width: 600px; margin: 0 auto">
                Join our growing community of researchers, clinicians, and developers working to
                advance kidney disease genetics research.
              </p>
              <div class="d-flex justify-center flex-wrap ga-3">
                <v-btn
                  color="primary"
                  size="large"
                  href="https://github.com/kidney-genetics/kidney-genetics-db"
                  target="_blank"
                  prepend-icon="mdi-github"
                  variant="flat"
                >
                  View on GitHub
                </v-btn>
                <v-btn
                  color="secondary"
                  size="large"
                  href="mailto:info@kidney-genetics.org"
                  prepend-icon="mdi-email"
                  variant="outlined"
                >
                  Contact Team
                </v-btn>
                <v-btn
                  color="info"
                  size="large"
                  href="/genes"
                  prepend-icon="mdi-database-search"
                  variant="outlined"
                >
                  Explore Data
                </v-btn>
              </div>
            </v-card-item>
          </v-card>
        </v-col>
      </v-row>
    </v-container>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import KidneyGeneticsLogo from '@/components/KidneyGeneticsLogo.vue'

const dataSources = ref([
  {
    name: 'PanelApp',
    description: 'Gene panels from Genomics England and Australian Genomics with expert curation',
    color: 'primary',
    icon: 'mdi-view-dashboard',
    coverage: '27 panels',
    frequency: 'Weekly',
    featured: true
  },
  {
    name: 'HPO',
    description: 'Human Phenotype Ontology providing standardized phenotype-gene associations',
    color: 'secondary',
    icon: 'mdi-human',
    coverage: '500+ terms',
    frequency: 'Monthly',
    featured: true
  },
  {
    name: 'PubTator',
    description: 'Automated literature mining for gene-disease associations from PubTator',
    color: 'info',
    icon: 'mdi-file-document',
    coverage: '10K+ papers',
    frequency: 'Daily',
    featured: false
  },
  {
    name: 'Literature',
    description: 'Manual curation from peer-reviewed research and clinical guidelines',
    color: 'success',
    icon: 'mdi-book-open',
    coverage: 'Curated',
    frequency: 'Ongoing',
    featured: false
  },
  {
    name: 'Diagnostic Panels',
    description: 'Commercial diagnostic panel data from certified laboratory providers',
    color: 'warning',
    icon: 'mdi-test-tube',
    coverage: '15+ labs',
    frequency: 'Quarterly',
    featured: false
  }
])

const backendTech = ref([
  {
    name: 'FastAPI',
    description: 'High-performance Python web framework',
    icon: 'mdi-lightning-bolt',
    color: 'primary'
  },
  {
    name: 'PostgreSQL',
    description: 'Advanced relational database',
    icon: 'mdi-database',
    color: 'info'
  },
  {
    name: 'SQLAlchemy',
    description: 'Python ORM and database toolkit',
    icon: 'mdi-code-braces',
    color: 'success'
  },
  {
    name: 'Alembic',
    description: 'Database migration management',
    icon: 'mdi-source-branch',
    color: 'warning'
  }
])

const frontendTech = ref([
  {
    name: 'Vue 3',
    description: 'Progressive JavaScript framework',
    icon: 'mdi-vuejs',
    color: 'success'
  },
  {
    name: 'Vuetify 3',
    description: 'Material Design component library',
    icon: 'mdi-material-design',
    color: 'primary'
  },
  {
    name: 'Vite',
    description: 'Fast build tool and dev server',
    icon: 'mdi-flash',
    color: 'warning'
  },
  {
    name: 'TypeScript',
    description: 'Type-safe JavaScript development',
    icon: 'mdi-language-typescript',
    color: 'info'
  }
])
</script>

<style scoped>
.about-hero {
  background: linear-gradient(
    135deg,
    rgb(var(--v-theme-primary-lighten-3)) 0%,
    rgb(var(--v-theme-surface)) 100%
  );
}

.v-theme--dark .about-hero {
  background: linear-gradient(
    135deg,
    rgba(var(--v-theme-primary), 0.1) 0%,
    rgb(var(--v-theme-background)) 100%
  );
}

.mission-card,
.overview-card,
.stats-card,
.source-card,
.tech-card,
.contact-card {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.mission-card:hover,
.overview-card:hover,
.stats-card:hover,
.source-card:hover,
.tech-card:hover,
.contact-card:hover {
  transform: translateY(-2px);
}

.source-card--featured {
  border: 2px solid rgb(var(--v-theme-primary-lighten-2));
}

.transparent {
  background: transparent !important;
}
</style>
