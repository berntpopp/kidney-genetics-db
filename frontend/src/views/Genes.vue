<template>
  <v-container>
    <v-row>
      <v-col cols="12">
        <div class="d-flex align-center mb-6">
          <v-icon color="primary" size="large" class="mr-3">mdi-dna</v-icon>
          <div>
            <h1 class="text-h4 font-weight-bold">Gene Browser</h1>
            <p class="text-body-2 text-medium-emphasis ma-0">
              Search and explore curated kidney disease gene-disease associations with evidence
              scores
            </p>
          </div>
        </div>
        <GeneTable />
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import GeneTable from '../components/GeneTable.vue'
</script>
