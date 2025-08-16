<template>
  <v-container>
    <v-row>
      <v-col cols="12" md="8" class="mx-auto">
        <h1 class="text-h3 mb-4">About Kidney Genetics Database</h1>

        <v-card class="mb-4">
          <v-card-title>Project Overview</v-card-title>
          <v-card-text>
            <p>
              The Kidney Genetics Database is a comprehensive platform for curating and exploring
              kidney disease-related genes. This modern web application replaces the original
              R-based pipeline with a scalable Python/FastAPI + Vue.js architecture.
            </p>
            <p class="mt-3">
              Our goal is to provide researchers and clinicians with easy access to curated genetic
              information relevant to kidney diseases, integrating data from multiple trusted
              sources.
            </p>
          </v-card-text>
        </v-card>

        <v-card class="mb-4">
          <v-card-title>Data Sources</v-card-title>
          <v-list>
            <v-list-item>
              <template #prepend>
                <v-icon color="primary">mdi-dna</v-icon>
              </template>
              <v-list-item-title>PanelApp (UK & Australia)</v-list-item-title>
              <v-list-item-subtitle>
                Gene panels from Genomics England and Australian Genomics
              </v-list-item-subtitle>
            </v-list-item>
            <v-list-item>
              <template #prepend>
                <v-icon color="secondary">mdi-book-open-variant</v-icon>
              </template>
              <v-list-item-title>HPO (Human Phenotype Ontology)</v-list-item-title>
              <v-list-item-subtitle>
                Phenotype-gene associations for kidney diseases
              </v-list-item-subtitle>
            </v-list-item>
            <v-list-item>
              <template #prepend>
                <v-icon color="info">mdi-text-search</v-icon>
              </template>
              <v-list-item-title>PubTator</v-list-item-title>
              <v-list-item-subtitle>
                Automated literature mining for gene-disease associations
              </v-list-item-subtitle>
            </v-list-item>
            <v-list-item>
              <template #prepend>
                <v-icon color="success">mdi-file-document</v-icon>
              </template>
              <v-list-item-title>Literature Curation</v-list-item-title>
              <v-list-item-subtitle>
                Manual curation from peer-reviewed research papers
              </v-list-item-subtitle>
            </v-list-item>
            <v-list-item>
              <template #prepend>
                <v-icon color="warning">mdi-test-tube</v-icon>
              </template>
              <v-list-item-title>Diagnostic Panels</v-list-item-title>
              <v-list-item-subtitle>
                Commercial diagnostic panel data from various providers
              </v-list-item-subtitle>
            </v-list-item>
          </v-list>
        </v-card>

        <v-card class="mb-4">
          <v-card-title>Technology Stack</v-card-title>
          <v-card-text>
            <v-row>
              <v-col cols="12" md="6">
                <h4 class="text-subtitle-1 mb-2">Backend</h4>
                <v-list density="compact">
                  <v-list-item>FastAPI (Python)</v-list-item>
                  <v-list-item>PostgreSQL Database</v-list-item>
                  <v-list-item>SQLAlchemy ORM</v-list-item>
                  <v-list-item>Alembic Migrations</v-list-item>
                </v-list>
              </v-col>
              <v-col cols="12" md="6">
                <h4 class="text-subtitle-1 mb-2">Frontend</h4>
                <v-list density="compact">
                  <v-list-item>Vue 3</v-list-item>
                  <v-list-item>Vuetify 3</v-list-item>
                  <v-list-item>Vite</v-list-item>
                  <v-list-item>Vue Router</v-list-item>
                </v-list>
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>

        <v-card>
          <v-card-title>Contact & Resources</v-card-title>
          <v-card-text>
            <p>
              For more information about this project or to report issues, please visit our GitHub
              repository or contact the development team.
            </p>
            <v-btn
              color="primary"
              class="mt-3"
              href="https://github.com/kidney-genetics/kidney-genetics-db"
              target="_blank"
              prepend-icon="mdi-github"
            >
              View on GitHub
            </v-btn>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
// No additional logic needed for static about page
</script>
