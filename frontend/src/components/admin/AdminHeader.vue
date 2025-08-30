<template>
  <div class="mb-6">
    <div class="d-flex align-center">
      <v-btn
        v-if="backRoute"
        icon="mdi-arrow-left"
        variant="text"
        size="small"
        class="mr-3"
        @click="$router.push(backRoute)"
      />
      <div class="flex-grow-1">
        <h1 class="text-h4 font-weight-medium">{{ title }}</h1>
        <p class="text-body-2 text-medium-emphasis mt-1">{{ subtitle }}</p>
      </div>
      <div v-if="$slots.actions" class="ml-4">
        <slot name="actions"></slot>
      </div>
    </div>
    <v-divider class="mt-4" />
  </div>
</template>

<script setup>
/**
 * Reusable admin header component
 * Provides consistent header with back navigation
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
  backRoute: {
    type: String,
    default: null
  }
})
</script>
