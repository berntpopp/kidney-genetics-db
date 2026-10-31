<script setup lang="ts">
/**
 * One-shot upload of a Gene Curator export (#448): every new curation becomes a KGDB draft
 * owned by the gene-curator-import account, then lives and is edited only in KGDB.
 */
import { computed, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { toast } from 'vue-sonner'
import { AlertTriangle, Loader2, Upload } from 'lucide-vue-next'
import AdminHeader from '@/components/admin/AdminHeader.vue'
import { PAGE_CONTAINER } from '@/components/shared'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { importGeneCuratorExport, type ImportReport, type ImportRow } from '@/api/admin/geneCurator'
import { errorMessage } from '@/stores/curation'

const SCHEMA_ERROR = 'not a Gene Curator export v1: '
const WORKFLOW = '/curation/associations'

type GroupKey = Exclude<keyof ImportReport, 'rows'>
const GROUPS: { key: GroupKey; title: string; detail: (_r: ImportRow) => string }[] = [
  { key: 'created', title: 'Created as drafts', detail: () => '' },
  { key: 'already_imported', title: 'Already imported (skipped)', detail: () => '' },
  { key: 'conflicts', title: 'Conflicts (skipped)', detail: r => r.reason ?? '' },
  { key: 'genes_not_in_kgdb', title: 'Genes not in KGDB', detail: r => r.hgnc_id },
  { key: 'rejected', title: 'Rejected', detail: r => r.reason ?? '' },
  {
    key: 'dropped_fields',
    title: 'Fields not imported',
    detail: r => (r.fields ?? []).join(', ')
  }
]

const file = ref<File | null>(null)
const uploading = ref(false)
const report = ref<ImportReport | null>(null)
const failure = ref<{ title: string; lines: string[] } | null>(null)

const groups = computed(() =>
  GROUPS.map(g => ({ ...g, rows: report.value?.[g.key] ?? [] })).filter(g => g.rows.length)
)
/** The record a row points to: the new draft, the earlier import, or the existing record */
const recordOf = (r: ImportRow) => r.record_id ?? r.existing_record_id

function onFile(event: Event) {
  file.value = (event.target as HTMLInputElement).files?.[0] ?? null
  failure.value = null
}

async function upload() {
  report.value = null
  if (!file.value) {
    failure.value = {
      title: 'Choose a file first',
      lines: ['Select a Gene Curator export (.json).']
    }
    return
  }
  uploading.value = true
  failure.value = null
  try {
    report.value = (await importGeneCuratorExport(file.value)).data
    toast.success(`Imported ${report.value.created.length} of ${report.value.rows} curations`)
  } catch (err) {
    const message = (err as { response?: unknown }).response
      ? errorMessage(err)
      : 'Could not reach the server. Check your connection and try again.'
    const at = message.indexOf(SCHEMA_ERROR)
    failure.value =
      at >= 0
        ? {
            title: 'Not a Gene Curator export v1',
            lines: message.slice(at + SCHEMA_ERROR.length).split('; ')
          }
        : { title: 'Import failed', lines: [message] }
    toast.error(failure.value.title)
  } finally {
    uploading.value = false
  }
}
</script>

<template>
  <div :class="PAGE_CONTAINER">
    <AdminHeader
      title="Gene Curator Import"
      subtitle="Import finished Gene Curator curations once, as drafts"
    />

    <Card class="py-0">
      <CardContent class="space-y-4 p-6">
        <p class="text-sm text-muted-foreground">
          Upload the JSON from Gene Curator's export (one page or a list of pages, up to 20 MB).
          Each new curation becomes a draft owned by the
          <code class="text-foreground">gene-curator-import</code> account; review it under
          <RouterLink :to="WORKFLOW" class="underline">Curated associations</RouterLink>. Curations
          imported before are skipped.
        </p>
        <form class="flex flex-col gap-3 sm:flex-row sm:items-end" @submit.prevent="upload">
          <div class="min-w-0 flex-1 space-y-1">
            <Label for="gc-export-file">Export file (.json)</Label>
            <input
              id="gc-export-file"
              type="file"
              accept=".json,application/json"
              :disabled="uploading"
              class="block w-full min-w-0 rounded-md border border-input bg-transparent px-3 py-1.5 text-sm file:mr-3 file:border-0 file:bg-transparent file:text-sm file:font-medium focus-visible:ring-[3px] focus-visible:ring-ring/50 focus-visible:outline-none disabled:opacity-50"
              @change="onFile"
            />
          </div>
          <Button type="submit" :disabled="uploading">
            <Loader2 v-if="uploading" class="size-4 motion-safe:animate-spin" aria-hidden="true" />
            <Upload v-else class="size-4" aria-hidden="true" />
            {{ uploading ? 'Importing…' : 'Import' }}
          </Button>
        </form>
      </CardContent>
    </Card>

    <section aria-live="polite" class="mt-6 space-y-4">
      <Alert v-if="failure" variant="destructive" data-testid="gc-failure">
        <AlertTriangle class="size-4" aria-hidden="true" />
        <AlertTitle>{{ failure.title }}</AlertTitle>
        <AlertDescription>
          <ul class="list-disc space-y-0.5 pl-4 break-words">
            <li v-for="line in failure.lines" :key="line">
              <code>{{ line }}</code>
            </li>
          </ul>
        </AlertDescription>
      </Alert>

      <template v-if="report">
        <h2 class="text-lg font-semibold">
          {{ report.rows }} curations in the file, {{ report.created.length }} imported
        </h2>
        <p v-if="!groups.length" class="text-sm text-muted-foreground">The file had no rows.</p>
        <Card v-for="g in groups" :key="g.key" class="py-0" :data-testid="`gc-${g.key}`">
          <CardContent class="p-4">
            <h3 class="mb-2 font-medium">
              {{ g.title }}
              <span class="tabular-nums text-muted-foreground">{{ g.rows.length }}</span>
            </h3>
            <ul class="divide-y text-sm">
              <li
                v-for="r in g.rows"
                :key="r.curation_id"
                class="flex flex-wrap items-baseline gap-x-3 gap-y-0.5 py-1.5"
              >
                <span class="font-medium">{{ r.gene_symbol }}</span>
                <span class="text-xs text-muted-foreground break-all">{{ r.entity_key }}</span>
                <RouterLink
                  v-if="recordOf(r)"
                  :to="WORKFLOW"
                  class="text-xs underline"
                  :aria-label="`Record ${recordOf(r)} in the curation workflow`"
                >
                  Record #{{ recordOf(r) }}
                </RouterLink>
                <span v-if="g.detail(r)" class="w-full text-muted-foreground break-words">{{
                  g.detail(r)
                }}</span>
              </li>
            </ul>
          </CardContent>
        </Card>
      </template>
    </section>
  </div>
</template>
