<template>
  <div :class="PAGE_CONTAINER">
    <PageHeader
      title="Page not found"
      description="Error 404: this address does not exist or has moved. Search for a gene or go back to a main page."
    />

    <form role="search" class="mb-6 flex max-w-xl gap-2" @submit.prevent="searchGenes">
      <Input
        v-model="query"
        type="search"
        placeholder="Gene symbol or HGNC ID"
        aria-label="Search genes"
      />
      <Button type="submit">
        <Search aria-hidden="true" />
        Search
      </Button>
    </form>
    <div class="flex flex-wrap items-center gap-3">
      <Button variant="outline" as-child>
        <RouterLink to="/genes">Browse all genes</RouterLink>
      </Button>
      <Button variant="ghost" as-child>
        <RouterLink to="/">Go to home page</RouterLink>
      </Button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { Search } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { PageHeader, PAGE_CONTAINER } from '@/components/shared'
import { useSeoMeta } from '@/composables/useSeoMeta'

useSeoMeta({
  title: 'Page Not Found',
  description: 'The requested page was not found.',
  noindex: true
})

const router = useRouter()
const query = ref('')

// Same hand-off as the Home search: GeneTable reads ?search=; an empty query opens the browser
const searchGenes = () => {
  const q = query.value.trim()
  router.push(q ? { path: '/genes', query: { search: q } } : '/genes')
}
</script>
