<template>
  <div class="container mx-auto px-4 py-16 text-center">
    <h1 class="text-6xl font-bold text-muted-foreground mb-4">404</h1>
    <p class="text-xl text-muted-foreground mb-8">Page not found</p>
    <p class="text-base text-muted-foreground mb-8 max-w-md mx-auto">
      The page you are looking for does not exist or has been moved.
    </p>
    <div class="flex items-center justify-center gap-4">
      <Button as-child>
        <RouterLink to="/">Go Home</RouterLink>
      </Button>
      <Button variant="outline" as-child>
        <RouterLink to="/genes">Browse Genes</RouterLink>
      </Button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { Button } from '@/components/ui/button'
import { useSeoMeta } from '@/composables/useSeoMeta'

useSeoMeta({
  title: 'Page Not Found',
  description: 'The requested page was not found.',
  noindex: true
})
</script>
