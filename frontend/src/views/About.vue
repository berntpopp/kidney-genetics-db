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
        <v-col cols="12">
          <div class="mb-6">
            <div class="d-flex align-center mb-4">
              <v-icon icon="mdi-information" size="small" class="mr-2" color="primary" />
              <h2 class="text-h4 font-weight-medium">Project Overview</h2>
            </div>
            <v-card rounded="lg" class="overview-card">
              <v-card-text class="pa-6">
                <div class="text-body-1 mb-4" style="line-height: 1.7">
                  The Kidney Genetics Database advances nephrology research through comprehensive
                  genetic data curation. Built on modern Python/FastAPI and Vue.js architecture,
                  we integrate evidence from multiple authoritative genomic databases.
                </div>
                <div class="text-body-1 mb-4" style="line-height: 1.7">
                  Our platform applies sophisticated evidence scoring algorithms to provide
                  researchers with confidence levels for gene-disease associations. The GenCC-compatible
                  schema ensures international interoperability for clinical applications.
                </div>
                <div class="d-flex flex-wrap ga-2 mt-6">
                  <v-chip color="primary" variant="tonal" size="x-small">
                    <v-icon icon="mdi-shield-check" size="x-small" start />
                    GenCC Compatible
                  </v-chip>
                  <v-chip color="success" variant="tonal" size="x-small">
                    <v-icon icon="mdi-chart-line" size="x-small" start />
                    Evidence Scoring
                  </v-chip>
                  <v-chip color="info" variant="tonal" size="x-small">
                    <v-icon icon="mdi-api" size="x-small" start />
                    RESTful API
                  </v-chip>
                  <v-chip color="secondary" variant="tonal" size="x-small">
                    <v-icon icon="mdi-database" size="x-small" start />
                    Multi-Source Integration
                  </v-chip>
                </div>
              </v-card-text>
            </v-card>
          </div>
        </v-col>
      </v-row>

      <!-- Data Sources -->
      <v-row class="mb-8">
        <v-col cols="12">
          <div class="d-flex align-center mb-6">
            <v-icon icon="mdi-database" size="small" class="mr-2" color="primary" />
            <h2 class="text-h4 font-weight-medium">Data Sources</h2>
          </div>
          <v-row>
            <v-col v-for="source in dataSources" :key="source.name" cols="12" md="6" lg="4">
              <v-card class="source-card h-100" rounded="lg">
                <v-card-item>
                  <template #prepend>
                    <v-avatar :color="source.color" size="40">
                      <v-icon :icon="source.icon" color="white" size="small" />
                    </v-avatar>
                  </template>
                  <v-card-title class="text-subtitle-1 font-weight-medium">{{ source.name }}</v-card-title>
                </v-card-item>
                <v-card-text class="pt-0">
                  <p class="text-body-2 text-medium-emphasis">{{ source.description }}</p>
                </v-card-text>
              </v-card>
            </v-col>
          </v-row>
        </v-col>
      </v-row>


      <!-- Contact -->
      <v-row class="mb-8">
        <v-col cols="12" md="8" class="mx-auto">
          <v-card rounded="xl" class="contact-card">
            <v-card-item class="pa-8 text-center">
              <v-icon icon="mdi-github" size="x-large" color="primary" class="mb-4" />
              <h2 class="text-h4 font-weight-medium mb-4">Open Source</h2>
              <p class="text-body-1 text-medium-emphasis mb-6" style="max-width: 600px; margin: 0 auto">
                This project is open source and available on GitHub.
              </p>
              <v-btn
                color="primary"
                size="large"
                href="https://github.com/bernt-popp/kidney-genetics-db"
                target="_blank"
                prepend-icon="mdi-github"
                variant="flat"
              >
                View on GitHub
              </v-btn>
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
    description: 'Gene panels from Genomics England and Australian Genomics',
    color: 'primary',
    icon: 'mdi-view-dashboard'
  },
  {
    name: 'HPO',
    description: 'Human Phenotype Ontology standardized associations',
    color: 'secondary',
    icon: 'mdi-human'
  },
  {
    name: 'ClinGen',
    description: 'Clinical genome resource curated gene validity',
    color: 'success',
    icon: 'mdi-dna'
  },
  {
    name: 'GenCC',
    description: 'Gene Curation Coalition consensus data',
    color: 'info',
    icon: 'mdi-account-group'
  },
  {
    name: 'PubTator',
    description: 'Literature mining for gene-disease associations',
    color: 'warning',
    icon: 'mdi-file-document'
  },
  {
    name: 'Diagnostic Panels',
    description: 'Commercial laboratory gene panel data',
    color: 'error',
    icon: 'mdi-test-tube'
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
.source-card,
.contact-card {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.mission-card:hover,
.overview-card:hover,
.source-card:hover,
.contact-card:hover {
  transform: translateY(-2px);
}

.transparent {
  background: transparent !important;
}
</style>
