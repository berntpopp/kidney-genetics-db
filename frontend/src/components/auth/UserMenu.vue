<template>
  <v-menu v-model="menu" :close-on-content-click="false" location="bottom">
    <template #activator="{ props }">
      <v-btn v-bind="props" variant="tonal" size="default" color="primary">
        <v-icon start>mdi-account</v-icon>
        {{ authStore.user?.username }}
        <v-icon end>mdi-chevron-down</v-icon>
      </v-btn>
    </template>

    <v-card min-width="250">
      <v-list density="compact">
        <v-list-item>
          <v-list-item-title class="font-weight-medium">
            {{ authStore.user?.username }}
          </v-list-item-title>
          <v-list-item-subtitle>
            {{ authStore.user?.email }}
          </v-list-item-subtitle>
          <template #append>
            <v-chip :color="roleColor" size="x-small" label>
              {{ authStore.userRole }}
            </v-chip>
          </template>
        </v-list-item>
      </v-list>

      <v-divider />

      <v-list density="compact">
        <v-list-item @click="goToProfile">
          <template #prepend>
            <v-icon size="small">mdi-account-circle</v-icon>
          </template>
          <v-list-item-title>My Profile</v-list-item-title>
        </v-list-item>

        <v-list-item v-if="authStore.isAdmin" @click="goToAdminPanel">
          <template #prepend>
            <v-icon size="small">mdi-shield-crown</v-icon>
          </template>
          <v-list-item-title>Admin Panel</v-list-item-title>
        </v-list-item>

        <v-list-item v-if="authStore.isCurator" @click="goToDataIngestion">
          <template #prepend>
            <v-icon size="small">mdi-database-import</v-icon>
          </template>
          <v-list-item-title>Data Ingestion</v-list-item-title>
        </v-list-item>
      </v-list>

      <v-divider />

      <v-list density="compact">
        <v-list-item @click="handleLogout">
          <template #prepend>
            <v-icon size="small">mdi-logout</v-icon>
          </template>
          <v-list-item-title>Logout</v-list-item-title>
        </v-list-item>
      </v-list>
    </v-card>
  </v-menu>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'

const authStore = useAuthStore()
const router = useRouter()

const menu = ref(false)

const roleColor = computed(() => {
  switch (authStore.userRole) {
    case 'admin':
      return 'error'
    case 'curator':
      return 'warning'
    default:
      return 'primary'
  }
})

const goToProfile = () => {
  menu.value = false
  router.push('/profile')
}

const goToAdminPanel = () => {
  menu.value = false
  router.push('/admin')
}

const goToDataIngestion = () => {
  menu.value = false
  router.push('/ingestion')
}

const handleLogout = async () => {
  menu.value = false
  await authStore.logout()
}
</script>
