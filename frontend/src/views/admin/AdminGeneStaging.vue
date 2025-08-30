<template>
  <v-container fluid class="pa-4">
    <AdminHeader
      title="Gene Staging"
      subtitle="Review and approve gene normalization attempts"
      back-route="/admin"
    />

    <!-- Coming Soon -->
    <v-card>
      <v-card-text class="text-center py-12">
        <v-icon size="x-large" color="grey">mdi-dna</v-icon>
        <h3 class="text-h5 mt-4 mb-2">Gene Staging</h3>
        <p class="text-medium-emphasis">This feature is under development</p>
      </v-card-text>
    </v-card>
  </v-container>
</template>

<script setup>
import AdminHeader from '@/components/admin/AdminHeader.vue'
</script>
