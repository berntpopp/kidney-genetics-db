<template>
  <v-container>
    <!-- Page Header (matches DataSources.vue pattern) -->
    <v-row>
      <v-col cols="12">
        <div class="d-flex align-center mb-6">
          <v-icon color="primary" size="large" class="mr-3">mdi-information</v-icon>
          <div>
            <h1 class="text-h4 font-weight-bold">About This Database</h1>
            <p class="text-body-2 text-medium-emphasis ma-0">
              Learn how to use the database, understand core concepts, and explore our technical
              architecture
            </p>
          </div>
        </div>
      </v-col>
    </v-row>

    <!-- How to Use Section -->
    <v-row class="mb-8">
      <v-col cols="12">
        <div class="d-flex align-center mb-4">
          <v-icon icon="mdi-compass" size="small" class="mr-2" color="primary" />
          <h2 class="text-h4 font-weight-medium">How to Use This Database</h2>
        </div>

        <!-- Usage Cards -->
        <v-row>
          <!-- Gene Search Card -->
          <v-col cols="12" md="6">
            <v-card rounded="lg" class="h-100">
              <v-card-item>
                <template #prepend>
                  <v-avatar color="primary" size="40">
                    <v-icon icon="mdi-magnify" color="white" size="small" />
                  </v-avatar>
                </template>
                <v-card-title class="text-subtitle-1 font-weight-medium">
                  Search & Browse Genes
                </v-card-title>
              </v-card-item>
              <v-card-text class="pt-0">
                <p class="text-body-2 mb-3">
                  Navigate to the
                  <router-link to="/genes" class="text-primary">Gene Browser</router-link>
                  to search curated kidney disease genes by symbol, HGNC ID, or disease association.
                </p>
                <v-chip size="x-small" color="info" variant="tonal" class="mr-2">
                  <v-icon icon="mdi-filter" size="x-small" start />
                  Filter by evidence score
                </v-chip>
                <v-chip size="x-small" color="success" variant="tonal">
                  <v-icon icon="mdi-sort" size="x-small" start />
                  Sort by any column
                </v-chip>
              </v-card-text>
            </v-card>
          </v-col>

          <!-- Evidence Scores Card -->
          <v-col cols="12" md="6">
            <v-card rounded="lg" class="h-100">
              <v-card-item>
                <template #prepend>
                  <v-avatar color="success" size="40">
                    <v-icon icon="mdi-chart-line" color="white" size="small" />
                  </v-avatar>
                </template>
                <v-card-title class="text-subtitle-1 font-weight-medium">
                  Understanding Evidence Scores
                </v-card-title>
              </v-card-item>
              <v-card-text class="pt-0">
                <p class="text-body-2 mb-3">
                  Evidence scores reflect confidence in gene-disease associations based on multiple
                  authoritative sources. Higher scores indicate stronger evidence from multiple
                  independent sources.
                </p>
                <div class="text-body-2">
                  <div class="d-flex align-center mb-1">
                    <v-chip size="x-small" color="#059669" class="mr-2" style="min-width: 60px">
                      95-100
                    </v-chip>
                    <span class="text-medium-emphasis">Definitive</span>
                  </div>
                  <div class="d-flex align-center mb-1">
                    <v-chip size="x-small" color="#10B981" class="mr-2" style="min-width: 60px">
                      80-94
                    </v-chip>
                    <span class="text-medium-emphasis">Strong</span>
                  </div>
                  <div class="d-flex align-center">
                    <v-chip size="x-small" color="#FCD34D" class="mr-2" style="min-width: 60px">
                      50-79
                    </v-chip>
                    <span class="text-medium-emphasis">Moderate/Limited</span>
                  </div>
                </div>
              </v-card-text>
            </v-card>
          </v-col>

          <!-- Annotations Card -->
          <v-col cols="12" md="6">
            <v-card rounded="lg" class="h-100">
              <v-card-item>
                <template #prepend>
                  <v-avatar color="secondary" size="40">
                    <v-icon icon="mdi-database" color="white" size="small" />
                  </v-avatar>
                </template>
                <v-card-title class="text-subtitle-1 font-weight-medium">
                  Exploring Annotations
                </v-card-title>
              </v-card-item>
              <v-card-text class="pt-0">
                <p class="text-body-2 mb-3">
                  Each gene includes rich annotations from multiple sources: HGNC (nomenclature),
                  gnomAD (constraint), ClinVar (variants), HPO (phenotypes), GTEx (expression),
                  Descartes (single-cell), MPO/MGI (mouse models), STRING (interactions), and
                  PubTator (literature).
                </p>
                <v-chip size="x-small" color="primary" variant="tonal">
                  <v-icon icon="mdi-check-circle" size="x-small" start />
                  Multi-source annotations
                </v-chip>
              </v-card-text>
            </v-card>
          </v-col>

          <!-- API Access Card -->
          <v-col cols="12" md="6">
            <v-card rounded="lg" class="h-100">
              <v-card-item>
                <template #prepend>
                  <v-avatar color="info" size="40">
                    <v-icon icon="mdi-api" color="white" size="small" />
                  </v-avatar>
                </template>
                <v-card-title class="text-subtitle-1 font-weight-medium">
                  API Access & Export
                </v-card-title>
              </v-card-item>
              <v-card-text class="pt-0">
                <p class="text-body-2 mb-3">
                  Access data programmatically via our JSON:API compliant REST API. Visit
                  <a href="/docs" target="_blank" class="text-primary">/docs</a>
                  for interactive API documentation.
                </p>
                <v-chip size="x-small" color="success" variant="tonal" class="mr-2">
                  <v-icon icon="mdi-code-json" size="x-small" start />
                  JSON export
                </v-chip>
                <v-chip size="x-small" color="warning" variant="tonal">
                  <v-icon icon="mdi-file-delimited" size="x-small" start />
                  CSV export
                </v-chip>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>
      </v-col>
    </v-row>

    <!-- Core Concepts Section -->
    <v-row class="mb-8">
      <v-col cols="12">
        <div class="d-flex align-center mb-4">
          <v-icon icon="mdi-lightbulb" size="small" class="mr-2" color="primary" />
          <h2 class="text-h4 font-weight-medium">Core Concepts</h2>
        </div>

        <!-- Concepts Cards -->
        <v-row>
          <!-- Gene Staging Card -->
          <v-col cols="12" md="6" lg="4">
            <v-card rounded="lg" class="concept-card h-100">
              <div
                class="concept-header pa-4"
                style="background: linear-gradient(135deg, #0ea5e9, #0284c7)"
              >
                <v-icon color="white" size="large" class="mb-2">mdi-swap-horizontal</v-icon>
                <h3 class="text-h6 font-weight-bold text-white">Gene Staging System</h3>
              </div>
              <v-card-text class="pa-4">
                <p class="text-body-2 text-medium-emphasis mb-3">
                  Two-stage data ingestion ensures quality: genes first enter a
                  <strong>staging</strong> area for normalization and validation, then move to
                  <strong>curated</strong> status after passing quality checks.
                </p>
                <div class="text-caption">
                  <div class="mb-1">
                    <v-icon icon="mdi-arrow-right" size="x-small" class="mr-1" />
                    Staging: Raw data ingestion + HGNC normalization
                  </div>
                  <div>
                    <v-icon icon="mdi-arrow-right" size="x-small" class="mr-1" />
                    Curated: Validated genes with complete annotations
                  </div>
                </div>
              </v-card-text>
            </v-card>
          </v-col>

          <!-- Multi-Source Integration Card -->
          <v-col cols="12" md="6" lg="4">
            <v-card rounded="lg" class="concept-card h-100">
              <div
                class="concept-header pa-4"
                style="background: linear-gradient(135deg, #10b981, #059669)"
              >
                <v-icon color="white" size="large" class="mb-2">mdi-database-sync</v-icon>
                <h3 class="text-h6 font-weight-bold text-white">Multi-Source Integration</h3>
              </div>
              <v-card-text class="pa-4">
                <p class="text-body-2 text-medium-emphasis mb-3">
                  Aggregates evidence from <strong>multiple authoritative sources</strong> with
                  automatic retry logic and cache validation. Each source contributes unique
                  annotations: nomenclature, constraint scores, variants, phenotypes, expression,
                  interactions, and literature.
                </p>
                <div class="text-caption">
                  <div class="mb-1">
                    <v-icon icon="mdi-check" size="x-small" class="mr-1" color="success" />
                    Comprehensive annotation coverage
                  </div>
                  <div>
                    <v-icon icon="mdi-check" size="x-small" class="mr-1" color="success" />
                    Exponential backoff retry with circuit breaker
                  </div>
                </div>
              </v-card-text>
            </v-card>
          </v-col>

          <!-- Evidence Scoring Card -->
          <v-col cols="12" md="6" lg="4">
            <v-card rounded="lg" class="concept-card h-100">
              <div
                class="concept-header pa-4"
                style="background: linear-gradient(135deg, #8b5cf6, #7c3aed)"
              >
                <v-icon color="white" size="large" class="mb-2">mdi-chart-bar</v-icon>
                <h3 class="text-h6 font-weight-bold text-white">Evidence Scoring</h3>
              </div>
              <v-card-text class="pa-4">
                <p class="text-body-2 text-medium-emphasis mb-3">
                  Weighted scoring algorithm aggregates evidence from multiple sources to produce a
                  confidence score (0-100). Scores are <strong>dynamic</strong> and update
                  automatically as new evidence becomes available from our data sources.
                </p>
                <div class="text-caption">
                  <div class="mb-1">
                    <v-icon icon="mdi-arrow-right" size="x-small" class="mr-1" />
                    Configurable source weights
                  </div>
                  <div>
                    <v-icon icon="mdi-arrow-right" size="x-small" class="mr-1" />
                    Transparent calculation methodology
                  </div>
                </div>
              </v-card-text>
            </v-card>
          </v-col>

          <!-- Performance Architecture Card -->
          <v-col cols="12" md="6" lg="4">
            <v-card rounded="lg" class="concept-card h-100">
              <div
                class="concept-header pa-4"
                style="background: linear-gradient(135deg, #3b82f6, #2563eb)"
              >
                <v-icon color="white" size="large" class="mb-2">mdi-lightning-bolt</v-icon>
                <h3 class="text-h6 font-weight-bold text-white">High-Performance Architecture</h3>
              </div>
              <v-card-text class="pa-4">
                <p class="text-body-2 text-medium-emphasis mb-3">
                  Non-blocking architecture with <strong>L1/L2 caching</strong> (memory + database)
                  delivers fast response times for cached requests. ThreadPoolExecutor ensures event
                  loop never blocks during heavy operations.
                </p>
                <div class="text-caption">
                  <div class="mb-1">
                    <v-icon icon="mdi-check" size="x-small" class="mr-1" color="success" />
                    High cache hit rates
                  </div>
                  <div>
                    <v-icon icon="mdi-check" size="x-small" class="mr-1" color="success" />
                    WebSocket progress tracking (no polling)
                  </div>
                </div>
              </v-card-text>
            </v-card>
          </v-col>

          <!-- Quality Assurance Card -->
          <v-col cols="12" md="6" lg="4">
            <v-card rounded="lg" class="concept-card h-100">
              <div
                class="concept-header pa-4"
                style="background: linear-gradient(135deg, #f59e0b, #d97706)"
              >
                <v-icon color="white" size="large" class="mb-2">mdi-shield-check</v-icon>
                <h3 class="text-h6 font-weight-bold text-white">Quality Assurance</h3>
              </div>
              <v-card-text class="pa-4">
                <p class="text-body-2 text-medium-emphasis mb-3">
                  Comprehensive quality checks at every stage: retry logic prevents transient
                  failures, cache validation ensures data integrity, and audit trails track all
                  normalization attempts in the gene staging table.
                </p>
                <div class="text-caption">
                  <div class="mb-1">
                    <v-icon icon="mdi-arrow-right" size="x-small" class="mr-1" />
                    Automatic retry with exponential backoff
                  </div>
                  <div>
                    <v-icon icon="mdi-arrow-right" size="x-small" class="mr-1" />
                    Cache validation (no empty responses)
                  </div>
                </div>
              </v-card-text>
            </v-card>
          </v-col>

          <!-- Real-Time Updates Card -->
          <v-col cols="12" md="6" lg="4">
            <v-card rounded="lg" class="concept-card h-100">
              <div
                class="concept-header pa-4"
                style="background: linear-gradient(135deg, #ef4444, #dc2626)"
              >
                <v-icon color="white" size="large" class="mb-2">mdi-update</v-icon>
                <h3 class="text-h6 font-weight-bold text-white">Real-Time Progress Tracking</h3>
              </div>
              <v-card-text class="pa-4">
                <p class="text-body-2 text-medium-emphasis mb-3">
                  WebSocket connections provide <strong>real-time updates</strong> during pipeline
                  operations without page refresh or polling. Watch genes flow from staging to
                  curation with live progress bars and status updates.
                </p>
                <div class="text-caption">
                  <div class="mb-1">
                    <v-icon icon="mdi-check" size="x-small" class="mr-1" color="success" />
                    Stable WebSocket connections during processing
                  </div>
                  <div>
                    <v-icon icon="mdi-check" size="x-small" class="mr-1" color="success" />
                    No blocking, no polling required
                  </div>
                </div>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>
      </v-col>
    </v-row>

    <!-- Open Source & Documentation -->
    <v-row class="mb-8">
      <v-col cols="12">
        <div class="d-flex align-center mb-4">
          <v-icon icon="mdi-code-tags" size="small" class="mr-2" color="primary" />
          <h2 class="text-h4 font-weight-medium">Open Source & Documentation</h2>
        </div>

        <v-row>
          <v-col cols="12" md="6">
            <v-card rounded="lg" class="h-100">
              <v-card-item>
                <template #prepend>
                  <v-avatar color="primary" size="40">
                    <v-icon icon="mdi-github" color="white" size="small" />
                  </v-avatar>
                </template>
                <v-card-title class="text-subtitle-1 font-weight-medium">
                  Source Code & Issues
                </v-card-title>
              </v-card-item>
              <v-card-text class="pt-0">
                <p class="text-body-2 mb-4">
                  This project is open source (MIT License). View source code, report issues, or
                  contribute on GitHub.
                </p>
                <v-btn
                  color="primary"
                  href="https://github.com/bernt-popp/kidney-genetics-db"
                  target="_blank"
                  prepend-icon="mdi-github"
                  size="small"
                >
                  View on GitHub
                </v-btn>
              </v-card-text>
            </v-card>
          </v-col>

          <v-col cols="12" md="6">
            <v-card rounded="lg" class="h-100">
              <v-card-item>
                <template #prepend>
                  <v-avatar color="info" size="40">
                    <v-icon icon="mdi-book-open" color="white" size="small" />
                  </v-avatar>
                </template>
                <v-card-title class="text-subtitle-1 font-weight-medium">
                  Technical Documentation
                </v-card-title>
              </v-card-item>
              <v-card-text class="pt-0">
                <p class="text-body-2 mb-4">
                  Comprehensive technical documentation covering architecture, API reference,
                  development guides, and troubleshooting.
                </p>
                <v-btn
                  color="info"
                  href="https://github.com/bernt-popp/kidney-genetics-db/tree/main/docs"
                  target="_blank"
                  prepend-icon="mdi-book-open"
                  size="small"
                >
                  View Documentation
                </v-btn>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
// No reactive data needed - all content is static
</script>

<style scoped>
/* Concept cards with gradient headers */
.concept-card {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
}

.concept-card:hover {
  transform: translateY(-2px);
}

.concept-header {
  border-radius: inherit;
}

/* Card height consistency */
.h-100 {
  height: 100%;
}

/* Smooth transitions */
.v-card {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

/* Motion preferences - Following Style Guide */
@media (prefers-reduced-motion: reduce) {
  .concept-card,
  .v-card {
    transition-duration: 0.01ms !important;
  }

  .concept-card:hover {
    transform: none;
  }
}
</style>
