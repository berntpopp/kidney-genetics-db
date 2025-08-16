<template>
  <v-container fluid>
    <v-row>
      <v-col cols="12">
        <h1 class="text-h4 mb-4">Gene Browser</h1>
        <DataSourceProgress />
        <GeneTable />
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import GeneTable from '../components/GeneTable.vue'
import DataSourceProgress from '../components/DataSourceProgress.vue'
</script>
