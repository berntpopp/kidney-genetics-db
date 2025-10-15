<template>
  <div class="mb-6">
    <!-- Breadcrumbs navigation (if provided) -->
    <v-breadcrumbs
      v-if="breadcrumbs && breadcrumbs.length > 0"
      :items="breadcrumbs"
      density="compact"
      class="pa-0 mb-2"
    >
      <template #divider>
        <v-icon size="small">mdi-chevron-right</v-icon>
      </template>
    </v-breadcrumbs>

    <div class="d-flex align-center">
      <!-- Icon - matches public view pattern -->
      <v-icon v-if="icon" :color="iconColor" size="large" class="mr-3">
        {{ icon }}
      </v-icon>

      <!-- Title and subtitle -->
      <div class="flex-grow-1">
        <h1 class="text-h4 font-weight-bold">{{ title }}</h1>
        <p class="text-body-2 text-medium-emphasis ma-0">
          {{ subtitle }}
        </p>
      </div>

      <!-- Optional action slot -->
      <div v-if="$slots.actions" class="ml-4">
        <slot name="actions"></slot>
      </div>
    </div>

    <!-- Optional divider (default: hidden to match public views) -->
    <v-divider v-if="showDivider" class="mt-4" />
  </div>
</template>

<script setup>
/**
 * Unified admin header component
 *
 * Features:
 * - Breadcrumb navigation for hierarchical context
 * - Icon + Title alignment (horizontal)
 * - Consistent spacing (mb-6)
 * - Material Design 3 typography
 * - Action slot for primary actions
 *
 * Usage:
 * <AdminHeader
 *   title="User Management"
 *   subtitle="Manage user accounts and permissions"
 *   icon="mdi-account-group"
 *   icon-color="primary"
 *   :breadcrumbs="[
 *     { title: 'Admin', to: '/admin' },
 *     { title: 'User Management', disabled: true }
 *   ]"
 * />
 */

defineProps({
  title: {
    type: String,
    required: true
  },
  subtitle: {
    type: String,
    default: ''
  },
  icon: {
    type: String,
    default: ''
  },
  iconColor: {
    type: String,
    default: 'primary'
  },
  showDivider: {
    type: Boolean,
    default: false
  },
  breadcrumbs: {
    type: Array,
    default: () => []
  }
})
</script>
