<template>
  <v-container fluid class="pa-4">
    <AdminHeader
      title="Annotations Management"
      subtitle="Manage gene annotation sources and updates"
      back-route="/admin"
    />

    <!-- Coming Soon -->
    <v-card>
      <v-card-text class="text-center py-12">
        <v-icon size="x-large" color="grey">mdi-tag-multiple</v-icon>
        <h3 class="text-h5 mt-4 mb-2">Annotations Management</h3>
        <p class="text-medium-emphasis">This feature is under development</p>
      </v-card-text>
    </v-card>
  </v-container>
</template>

<script setup>
import AdminHeader from '@/components/admin/AdminHeader.vue'
</script>
