<script setup lang="ts">
/**
 * View header: breadcrumb, one h1, a one-line description and actions (DESIGN.md Layout).
 * Place it first inside the view's PAGE_CONTAINER; it adds no horizontal padding itself.
 */
defineProps<{
  title: string
  description?: string
}>()
</script>

<template>
  <header data-slot="page-header" class="mb-6 space-y-3">
    <slot name="breadcrumb" />
    <div class="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div class="min-w-0 space-y-1">
        <h1 class="text-3xl font-semibold tracking-tight text-balance text-foreground">
          {{ title }}
        </h1>
        <p v-if="description || $slots.description" class="max-w-[70ch] text-muted-foreground">
          <slot name="description">{{ description }}</slot>
        </p>
      </div>
      <div v-if="$slots.actions" class="flex shrink-0 flex-wrap items-center gap-2">
        <slot name="actions" />
      </div>
    </div>
  </header>
</template>
