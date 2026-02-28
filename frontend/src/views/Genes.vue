<template>
  <v-container>
    <v-row>
      <v-col cols="12">
        <!-- Breadcrumbs -->
        <v-breadcrumbs :items="breadcrumbs" density="compact" class="pa-0 mb-2">
          <template #divider>
            <ChevronRight class="size-4" />
          </template>
        </v-breadcrumbs>

        <!-- Header -->
        <div class="d-flex align-center mb-6">
          <Dna class="size-6 text-primary mr-3" />
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
import { ChevronRight, Dna } from 'lucide-vue-next'
import GeneTable from '../components/GeneTable.vue'
import { PUBLIC_BREADCRUMBS } from '@/utils/publicBreadcrumbs'

const breadcrumbs = PUBLIC_BREADCRUMBS.genes
</script>
