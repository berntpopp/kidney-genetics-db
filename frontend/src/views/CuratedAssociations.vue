<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch, type ComponentPublicInstance } from 'vue'
import { RouterLink } from 'vue-router'
import {
  Check,
  Download,
  FileJson,
  FileSpreadsheet,
  FileText,
  Plus,
  Share2,
  X
} from 'lucide-vue-next'
import { useAuthStore } from '@/stores/auth'
import { useCurationStore } from '@/stores/curation'
import {
  RELATIONSHIP_LABELS,
  RELATIONSHIP_TYPES,
  type Association,
  type AssociationInput,
  type WorkflowAction
} from '@/api/curation'
import AssociationForm from '@/components/curation/AssociationForm.vue'
import AssociationRows from '@/components/curation/AssociationRows.vue'
import { Button } from '@/components/ui/button'
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator
} from '@/components/ui/breadcrumb'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger
} from '@/components/ui/dropdown-menu'
import { associationsCsv, today, useShareExport } from '@/composables/useShareExport'
import { TooltipProvider } from '@/components/ui/tooltip'
import { Chip, DataState, PageHeader, PAGE_CONTAINER, StatusBadge } from '@/components/shared'
import { getPublicBreadcrumbs } from '@/utils/publicBreadcrumbs'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from '@/components/ui/table'

const breadcrumbs = getPublicBreadcrumbs('Curated Associations', '/curation/associations')

/** Workflow status -> shared status vocabulary and its label */
const STATUS_KEYS: Record<string, string> = { in_review: 'pending' }
const STATUS_LABELS: Record<string, string> = {
  draft: 'Draft',
  in_review: 'In review',
  published: 'Published'
}
const STACK = 'max-lg:block max-lg:min-w-0 max-lg:max-w-none max-lg:px-0 max-lg:py-1'

const auth = useAuthStore()
const store = useCurationStore()

const { copied, copy, download, printPdf } = useShareExport()
// The address bar as-is, so any query-string filters travel with the link
const shareUrl = () => window.location.href
const exportName = () => `curated-associations-${geneFilter.value.trim() || 'all'}-${today()}`
const exportAs = (kind: 'json' | 'csv') => {
  const name = exportName()
  if (kind === 'json')
    download(JSON.stringify(store.published, null, 2), 'application/json', `${name}.json`)
  else download(associationsCsv(store.published), 'text/csv', `${name}.csv`)
}

const geneFilter = ref('')
const editing = ref<Association | null>(null)
const formKey = ref(0)
const formOpen = ref(false)
const formCard = ref<ComponentPublicInstance | null>(null)

const canCurate = computed(() => auth.isCurator)

/** Susceptibility gets its own table so it is never read as a Mendelian class (#437) */
const publishedGroups = computed(() =>
  RELATIONSHIP_TYPES.map(type => ({
    type,
    records: store.published.filter(r => (r.relationship_type ?? 'mendelian') === type)
  })).filter(g => g.type === 'mendelian' || g.records.length)
)

/** Published on import because only an AI approved it in Gene Curator (#639) */
const pendingHuman = (r: Association) =>
  r.status === 'published' && r.approval_kind === 'ai' && !r.human_reviewed_at
const pendingOnly = ref(false)
const pendingCount = computed(() => store.workflow.filter(pendingHuman).length)
const workflowRecords = computed(() =>
  pendingOnly.value ? store.workflow.filter(pendingHuman) : store.workflow
)

type Action = { action: WorkflowAction | 'edit'; label: string; primary?: boolean }
/** Which workflow buttons the server will accept for this user (author vs. reviewer) */
function actionsFor(r: Association): Action[] {
  const mine = r.curator_id === auth.user?.id
  if (r.status === 'draft')
    // An unedited Gene Curator import is any curator's to take over (#448)
    return mine || r.imported_unclaimed
      ? [
          { action: 'edit', label: 'Edit' },
          { action: 'submit', label: 'Submit for review', primary: true }
        ]
      : []
  if (mine) return []
  return r.status === 'in_review'
    ? [
        { action: 'publish', label: 'Publish', primary: true },
        { action: 'return-to-draft', label: 'Return to draft' }
      ]
    : [
        ...(pendingHuman(r)
          ? [{ action: 'human-review' as const, label: 'Mark human-reviewed', primary: true }]
          : []),
        { action: 'return-to-draft', label: 'Return to draft' }
      ]
}

async function openForm(record: Association | null) {
  editing.value = record
  formOpen.value = true
  await nextTick()
  formCard.value?.$el.scrollIntoView({ block: 'start' })
  // the gene is fixed once a draft exists, so editing starts at the disease
  document.getElementById(record ? 'gda-disease_id' : 'gda-gene_symbol')?.focus()
}

function closeForm() {
  editing.value = null
  formOpen.value = false
}

async function onAction(r: Association, action: WorkflowAction | 'edit') {
  if (action === 'edit') await openForm(r)
  else await store.transition(r, action)
}

async function onSave(input: AssociationInput) {
  const saved = editing.value
    ? await store.update(editing.value.id, input)
    : await store.create(input)
  if (saved) {
    closeForm()
    formKey.value++
  }
}

const loadAll = () => {
  store.loadPublished(geneFilter.value.trim())
  if (canCurate.value) store.loadWorkflow()
}

onMounted(loadAll)
// Auth resolves after mount: only the workflow list depends on it, so don't refetch the public one
watch(canCurate, curator => curator && store.loadWorkflow())

/** An unedited Gene Curator import draft any curator may take over (#448) */
const unclaimed = (r: Association) => r.status === 'draft' && !!r.imported_unclaimed

/** ISO dates, like the verification dates of resources */
const fmtDate = (d: string | null) => (d ? d.slice(0, 10) : '—')
</script>

<template>
  <TooltipProvider>
    <div :class="PAGE_CONTAINER">
      <PageHeader title="Expert-reviewed gene–disease associations">
        <template #breadcrumb>
          <Breadcrumb>
            <BreadcrumbList>
              <BreadcrumbItem v-for="(crumb, index) in breadcrumbs" :key="index">
                <BreadcrumbLink v-if="!crumb.disabled && crumb.to" as-child>
                  <RouterLink :to="crumb.to">{{ crumb.title }}</RouterLink>
                </BreadcrumbLink>
                <BreadcrumbPage v-else>{{ crumb.title }}</BreadcrumbPage>
                <BreadcrumbSeparator v-if="index < breadcrumbs.length - 1" />
              </BreadcrumbItem>
            </BreadcrumbList>
          </Breadcrumb>
        </template>
        <template #description>
          Associations curated by experts and published after review by a second curator. Diseases
          are identified by MONDO or OMIM IDs only; HPO terms describe phenotypes and are not used
          as disease identifiers.
        </template>
      </PageHeader>

      <div class="space-y-6">
        <DataState :error="store.error" error-title="Request failed" @retry="loadAll" />

        <Card>
          <CardHeader class="flex flex-row flex-wrap items-end justify-between gap-3">
            <CardTitle tag="h2" class="text-xl">Published associations</CardTitle>
            <div class="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                :aria-label="copied === 'link' ? 'Link copied' : 'Copy link to this page'"
                @click="copy(shareUrl(), 'link', 'Link copied')"
              >
                <Check v-if="copied === 'link'" aria-hidden="true" />
                <Share2 v-else aria-hidden="true" />
                <span class="hidden sm:inline">{{ copied === 'link' ? 'Copied' : 'Share' }}</span>
              </Button>
              <DropdownMenu>
                <DropdownMenuTrigger as-child>
                  <Button
                    variant="outline"
                    size="sm"
                    :disabled="!store.published.length"
                    aria-label="Export published associations"
                  >
                    <Download aria-hidden="true" />
                    <span class="hidden sm:inline">Export</span>
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem @click="exportAs('json')">
                    <FileJson aria-hidden="true" />
                    Export as JSON
                  </DropdownMenuItem>
                  <DropdownMenuItem @click="exportAs('csv')">
                    <FileSpreadsheet aria-hidden="true" />
                    Export as CSV
                  </DropdownMenuItem>
                  <DropdownMenuItem @click="printPdf(exportName())">
                    <FileText aria-hidden="true" />
                    Export as PDF
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
            <form
              class="flex items-end gap-2"
              @submit.prevent="store.loadPublished(geneFilter.trim())"
            >
              <div class="space-y-1">
                <Label for="gda-filter">Gene symbol</Label>
                <Input id="gda-filter" v-model="geneFilter" placeholder="e.g. PKD1" class="w-36" />
              </div>
              <Button type="submit" variant="outline">Filter</Button>
            </form>
          </CardHeader>
          <CardContent class="space-y-6">
            <section
              v-for="group in publishedGroups"
              :key="group.type"
              :data-testid="`published-${group.type}`"
              class="space-y-2"
            >
              <h3 class="text-sm font-medium text-muted-foreground">
                {{ RELATIONSHIP_LABELS[group.type] }}
              </h3>
              <Table class="max-lg:block">
                <TableHeader class="max-lg:sr-only">
                  <TableRow>
                    <TableHead class="w-16">MOI</TableHead>
                    <!-- Fixed widths keep the Mendelian and susceptibility columns aligned -->
                    <TableHead class="w-56">{{
                      group.type === 'mendelian' ? 'Classification' : 'Risk association'
                    }}</TableHead>
                    <TableHead>Evidence</TableHead>
                    <TableHead class="w-28 text-right">Published</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody class="max-lg:block" :aria-busy="store.loading">
                  <AssociationRows
                    :records="group.records"
                    :trailing="1"
                    :row-test-id="() => 'gda-row'"
                  >
                    <template #trailing="{ record }">
                      <TableCell
                        :class="[
                          STACK,
                          'text-right align-top text-xs text-muted-foreground tabular-nums max-lg:text-left'
                        ]"
                      >
                        <span class="lg:hidden">Published </span>{{ fmtDate(record.published_at) }}
                      </TableCell>
                    </template>
                  </AssociationRows>
                  <template v-if="group.type === 'mendelian'">
                    <template v-if="store.loading && !store.published.length">
                      <TableRow v-for="n in 3" :key="`skeleton-${n}`" aria-hidden="true">
                        <TableCell v-for="c in 4" :key="c">
                          <div class="h-4 rounded-md bg-muted motion-safe:animate-pulse" />
                        </TableCell>
                      </TableRow>
                    </template>
                    <TableRow v-else-if="!group.records.length">
                      <TableCell colspan="4" class="py-8 text-center text-muted-foreground">
                        {{
                          geneFilter.trim()
                            ? `No published associations for ${geneFilter.trim()}.`
                            : 'No published associations yet.'
                        }}
                      </TableCell>
                    </TableRow>
                  </template>
                </TableBody>
              </Table>
            </section>
            <p
              v-if="store.publishedTotal > store.published.length"
              class="text-sm text-muted-foreground"
            >
              Showing {{ store.published.length }} of {{ store.publishedTotal }}
            </p>
          </CardContent>
        </Card>

        <template v-if="canCurate">
          <Card>
            <CardHeader class="flex flex-row flex-wrap items-center justify-between gap-3">
              <CardTitle tag="h2" class="text-xl">Curation workflow</CardTitle>
              <div class="flex flex-wrap gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  :aria-pressed="pendingOnly"
                  data-testid="wf-pending-human"
                  @click="pendingOnly = !pendingOnly"
                >
                  Pending human review ({{ pendingCount }})
                </Button>
                <Button v-if="!formOpen" size="sm" @click="openForm(null)">
                  <Plus aria-hidden="true" />New draft
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <Table class="max-lg:block">
                <TableHeader class="max-lg:sr-only">
                  <TableRow>
                    <TableHead class="w-16">MOI</TableHead>
                    <TableHead class="w-56">Classification</TableHead>
                    <TableHead>Evidence</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead class="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody class="max-lg:block">
                  <AssociationRows
                    :records="workflowRecords"
                    :trailing="2"
                    :row-test-id="r => `wf-${r.id}`"
                  >
                    <template #trailing="{ record }">
                      <TableCell :class="[STACK, 'align-top']">
                        <div class="flex flex-wrap items-center gap-1.5">
                          <StatusBadge
                            :status="STATUS_KEYS[record.status] ?? record.status"
                            :label="STATUS_LABELS[record.status] ?? record.status"
                          />
                          <!-- Imported records still need a KGDB curator other than the author -->
                          <Chip
                            v-if="record.source === 'gene_curator'"
                            kind="neutral"
                            :label="
                              unclaimed(record)
                                ? 'Gene Curator import, unclaimed'
                                : 'Gene Curator import'
                            "
                            :tooltip="
                              unclaimed(record)
                                ? 'Imported from Gene Curator and not yet edited in KGDB: any curator may edit or submit it'
                                : 'Curated in Gene Curator; publishing needs a KGDB curator other than the author'
                            "
                          />
                        </div>
                        <p
                          v-if="
                            record.status === 'in_review' && record.curator_id === auth.user?.id
                          "
                          class="mt-1 text-xs text-muted-foreground"
                        >
                          Awaiting review by another curator
                        </p>
                        <p class="mt-1 text-xs text-muted-foreground tabular-nums">
                          Updated {{ fmtDate(record.updated_at) }}
                        </p>
                      </TableCell>
                      <TableCell :class="[STACK, 'align-top whitespace-normal']">
                        <div
                          data-testid="wf-actions"
                          class="flex flex-wrap justify-end gap-2 max-lg:justify-start"
                        >
                          <Button
                            v-for="a in actionsFor(record)"
                            :key="a.action"
                            size="sm"
                            :variant="a.primary ? 'default' : 'ghost'"
                            :disabled="store.loading"
                            @click="onAction(record, a.action)"
                          >
                            {{ a.label }}
                          </Button>
                        </div>
                      </TableCell>
                    </template>
                  </AssociationRows>
                  <TableRow v-if="!workflowRecords.length && !store.loading">
                    <TableCell colspan="5" class="py-8 text-center text-muted-foreground">
                      {{
                        pendingOnly
                          ? 'No records pending human review.'
                          : 'No associations in the workflow.'
                      }}
                    </TableCell>
                  </TableRow>
                </TableBody>
              </Table>
              <p
                v-if="store.workflowTotal > store.workflow.length"
                class="text-sm text-muted-foreground"
              >
                Showing {{ store.workflow.length }} of {{ store.workflowTotal }}
              </p>
            </CardContent>
          </Card>

          <Card v-if="formOpen" ref="formCard" class="scroll-mt-20">
            <CardHeader class="flex flex-row items-center justify-between gap-3">
              <CardTitle tag="h2" class="text-xl">{{
                editing ? `Edit draft #${editing.id}` : 'New draft'
              }}</CardTitle>
              <Button variant="ghost" size="icon" aria-label="Close the editor" @click="closeForm">
                <X aria-hidden="true" />
              </Button>
            </CardHeader>
            <CardContent>
              <AssociationForm
                :key="formKey"
                :record="editing"
                :busy="store.loading"
                @save="onSave"
                @cancel="closeForm"
              />
            </CardContent>
          </Card>
        </template>
      </div>
    </div>
  </TooltipProvider>
</template>
