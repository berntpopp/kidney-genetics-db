<template>
  <!-- Curator inbox for public problem/suggestion reports -->
  <div :class="PAGE_CONTAINER">
    <PageHeader
      title="Curation reports"
      description="Problems and suggestions sent from the public curated-gene pages."
    />
    <div class="mb-4 flex flex-wrap items-center gap-2">
      <Button
        v-for="f in FILTERS"
        :key="f.value"
        size="sm"
        :variant="filter === f.value ? 'default' : 'outline'"
        @click="filter = f.value"
      >
        {{ f.label }}<template v-if="f.value === 'open' && openCount"> ({{ openCount }})</template>
      </Button>
    </div>

    <DataState
      :loading="loading"
      :error="error"
      error-title="Could not load the reports"
      :empty="!reports.length"
      empty-message="No reports."
      @retry="load"
    >
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Gene</TableHead>
            <TableHead>Type</TableHead>
            <TableHead>Message</TableHead>
            <TableHead>Reporter</TableHead>
            <TableHead>Date</TableHead>
            <TableHead>Status</TableHead>
            <TableHead><span class="sr-only">Actions</span></TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow v-for="r in reports" :key="r.id">
            <TableCell class="font-medium">
              <RouterLink :to="`/curation/associations/${r.gene_symbol}`" :class="LINK">{{
                r.gene_symbol
              }}</RouterLink>
            </TableCell>
            <TableCell class="capitalize">{{ r.kind }}</TableCell>
            <TableCell class="max-w-md whitespace-pre-wrap break-words">{{ r.message }}</TableCell>
            <TableCell class="break-all">
              {{ r.reporter_name || 'Anonymous' }}
              <a v-if="r.reporter_email" :href="`mailto:${r.reporter_email}`" :class="LINK">{{
                r.reporter_email
              }}</a>
            </TableCell>
            <TableCell class="tabular-nums">{{ r.created_at.slice(0, 10) }}</TableCell>
            <TableCell class="capitalize">{{ r.status }}</TableCell>
            <TableCell class="space-x-2 whitespace-nowrap">
              <template v-if="r.status === 'open'">
                <Button size="sm" @click="setStatus(r, 'resolved')">Resolve</Button>
                <Button size="sm" variant="outline" @click="setStatus(r, 'dismissed')"
                  >Dismiss</Button
                >
              </template>
              <Button v-else size="sm" variant="outline" @click="setStatus(r, 'open')"
                >Reopen</Button
              >
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>
    </DataState>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import {
  curationReportsApi,
  type Report,
  type ReportStatus
} from '@/api/curationReports'
import { DataState, PageHeader, PAGE_CONTAINER } from '@/components/shared'
import { Button } from '@/components/ui/button'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from '@/components/ui/table'

const LINK = 'text-primary underline-offset-4 hover:underline'

const FILTERS: { value: ReportStatus | undefined; label: string }[] = [
  { value: 'open', label: 'Open' },
  { value: 'resolved', label: 'Resolved' },
  { value: 'dismissed', label: 'Dismissed' },
  { value: undefined, label: 'All' }
]

const reports = ref<Report[]>([])
const openCount = ref(0)
const filter = ref<ReportStatus | undefined>('open')
const loading = ref(true)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await curationReportsApi.list({ status: filter.value })
    reports.value = res.data
    openCount.value = res.meta.open_count
  } catch {
    error.value = 'Could not load the reports.'
  } finally {
    loading.value = false
  }
}

async function setStatus(report: Report, status: ReportStatus) {
  try {
    await curationReportsApi.setStatus(report.id, status)
    await load()
  } catch {
    error.value = 'Could not update the report.'
  }
}

onMounted(load)
watch(filter, load)
</script>
