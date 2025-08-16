<template>
  <v-container>
    <v-row>
      <v-col cols="12">
        <h1 class="text-h3 mb-4">Kidney Genetics Database</h1>
        <p class="text-subtitle-1 mb-6">
          A comprehensive platform for exploring kidney disease-related genes
        </p>
      </v-col>
    </v-row>

    <!-- Statistics Cards -->
    <v-row>
      <v-col v-for="stat in stats" :key="stat.title" cols="12" md="3">
        <v-card>
          <v-card-text class="text-center">
            <div class="text-h2 mb-2" :class="`text-${stat.color}`">
              {{ stat.value }}
            </div>
            <div class="text-subtitle-1">{{ stat.title }}</div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Quick Actions -->
    <v-row class="mt-6">
      <v-col cols="12">
        <h2 class="text-h5 mb-4">Quick Actions</h2>
      </v-col>
      <v-col cols="12" md="4">
        <v-card>
          <v-card-title>
            <v-icon start>mdi-dna</v-icon>
            Browse Genes
          </v-card-title>
          <v-card-text>
            Explore the complete list of kidney disease-related genes with evidence
          </v-card-text>
          <v-card-actions>
            <v-btn color="primary" to="/genes"> View Genes </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
      <v-col cols="12" md="4">
        <v-card>
          <v-card-title>
            <v-icon start>mdi-magnify</v-icon>
            Search Database
          </v-card-title>
          <v-card-text>
            Search for specific genes by symbol, HGNC ID, or evidence score
          </v-card-text>
          <v-card-actions>
            <v-btn color="primary" to="/genes"> Search Now </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
      <v-col cols="12" md="4">
        <v-card>
          <v-card-title>
            <v-icon start>mdi-information</v-icon>
            About Project
          </v-card-title>
          <v-card-text>
            Learn more about the kidney genetics database and data sources
          </v-card-text>
          <v-card-actions>
            <v-btn color="primary" to="/about"> Learn More </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>

    <!-- Recent Updates -->
    <v-row class="mt-6">
      <v-col cols="12">
        <h2 class="text-h5 mb-4">Data Sources</h2>
        <v-list>
          <v-list-item v-for="source in dataSources" :key="source.name">
            <template #prepend>
              <v-icon :color="source.status === 'active' ? 'success' : 'warning'">
                {{ source.status === 'active' ? 'mdi-check-circle' : 'mdi-alert-circle' }}
              </v-icon>
            </template>
            <v-list-item-title>{{ source.name }}</v-list-item-title>
            <v-list-item-subtitle>{{ source.description }}</v-list-item-subtitle>
          </v-list-item>
        </v-list>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { geneApi } from '../api/genes'

const stats = ref([
  { title: 'Total Genes', value: 0, color: 'primary' },
  { title: 'Data Sources', value: 5, color: 'secondary' },
  { title: 'Gene Panels', value: 19, color: 'info' },
  { title: 'Last Update', value: 'Today', color: 'success' }
])

const dataSources = ref([
  {
    name: 'PanelApp UK',
    description: 'Gene panels from Genomics England',
    status: 'active'
  },
  {
    name: 'PanelApp Australia',
    description: 'Gene panels from Australian Genomics',
    status: 'pending'
  },
  {
    name: 'HPO',
    description: 'Human Phenotype Ontology associations',
    status: 'pending'
  },
  {
    name: 'PubTator',
    description: 'Automated literature mining',
    status: 'pending'
  },
  {
    name: 'Literature',
    description: 'Manual curation from research papers',
    status: 'pending'
  }
])

onMounted(async () => {
  try {
    const response = await geneApi.getGenes({ perPage: 1 })
    stats.value[0].value = response.total
  } catch (error) {
    console.error('Error fetching stats:', error)
  }
})
</script>
