<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch, type ComponentPublicInstance } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useDebounceFn } from '@vueuse/core'
import {
  Check,
  Download,
  FileJson,
  FileSpreadsheet,
  FileText,
  FilterX,
  Plus,
  RefreshCw,
  Search,
  Share2,
  X
} from 'lucide-vue-next'
import { useAuthStore } from '@/stores/auth'
import { defaultQuery, PAGE_SIZES, useCurationStore, type PageQuery } from '@/stores/curation'
import {
  MENDELIAN_STRENGTHS,
  RELATIONSHIP_LABELS,
  RELATIONSHIP_TYPES,
  SORT_KEYS,
  SUSCEPTIBILITY_STRENGTHS,
  type Association,
  type SortKey,
  type AssociationInput,
  type WorkflowAction
} from '@/api/curation'
import AssociationForm from '@/components/curation/AssociationForm.vue'
import AssociationRows from '@/components/curation/AssociationRows.vue'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { DataTableColumnHeader } from '@/components/ui/data-table'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@/components/ui/select'
import { Separator } from '@/components/ui/separator'
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
import {
  Chip,
  DataState,
  PageHeader,
  PAGE_CONTAINER,
  PaginationBar,
  StatusBadge
} from '@/components/shared'
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
const route = useRoute()
const router = useRouter()

const { copied, copy, download, printPdf } = useShareExport()
// The address bar as-is, so the search and page travel with the link
const shareUrl = () => window.location.href
const exportName = () => `curated-associations-${store.publishedQuery.q.trim() || 'all'}-${today()}`
/** Exports every record matching the search, not only the visible page */
async function exportAs(kind: 'json' | 'csv') {
  const rows = await store.fetchAllPublished()
  if (!rows) return
  const name = exportName()
  if (kind === 'json') download(JSON.stringify(rows, null, 2), 'application/json', `${name}.json`)
  else download(associationsCsv(rows), 'text/csv', `${name}.csv`)
}

const STRENGTHS: readonly string[] = [...MENDELIAN_STRENGTHS, ...SUSCEPTIBILITY_STRENGTHS]
const DEFAULT = defaultQuery()

/** Published-list state from the URL (?q=&strength=&sort_by=&sort_order=&page=&size=) */
function routeQuery(): PageQuery {
  const { q, page, size, sort_by, sort_order, strength } = route.query
  return {
    q: typeof q === 'string' ? q : '',
    page: Math.max(0, Math.floor(Number(page) || 1) - 1), // one-based in the URL
    size: PAGE_SIZES.includes(Number(size)) ? Number(size) : DEFAULT.size,
    strengths: [strength].flat().filter((v): v is string => STRENGTHS.includes(v as string)),
    sortBy: SORT_KEYS.includes(sort_by as SortKey) ? (sort_by as SortKey) : DEFAULT.sortBy,
    sortOrder: sort_order === 'desc' ? 'desc' : 'asc'
  }
}

async function setPublished(query: Partial<PageQuery>) {
  await store.loadPublished(query)
  const { q, page, size, strengths, sortBy, sortOrder } = store.publishedQuery
  const sorted = sortBy !== DEFAULT.sortBy || sortOrder !== DEFAULT.sortOrder
  router.replace({
    query: {
      ...route.query,
      q: q.trim() || undefined,
      strength: strengths.length ? strengths : undefined,
      sort_by: sorted ? sortBy : undefined,
      sort_order: sorted ? sortOrder : undefined,
      page: page ? String(page + 1) : undefined,
      size: size === DEFAULT.size ? undefined : String(size)
    }
  })
}

/** The genes table's sort menu, as server sort key and order */
const SORT_OPTIONS = [
  { value: 'gene_asc', title: 'Gene (A–Z)' },
  { value: 'gene_desc', title: 'Gene (Z–A)' },
  { value: 'disease_asc', title: 'Disease (A–Z)' },
  { value: 'classification_desc', title: 'Strongest classification' },
  { value: 'classification_asc', title: 'Weakest classification' },
  { value: 'points_desc', title: 'Most points' },
  { value: 'published_desc', title: 'Newest published' },
  { value: 'published_asc', title: 'Oldest published' }
]
const sortOption = computed(
  () => `${store.publishedQuery.sortBy}_${store.publishedQuery.sortOrder}`
)
function applySort(value: unknown) {
  const [sortBy, sortOrder] = String(value).split('_') as [SortKey, 'asc' | 'desc']
  setPublished({ sortBy, sortOrder, page: 0 })
}

/** A column header the shared sort menu drives; the server sorts, so this only sets the key */
function sortColumn(list: 'published' | 'workflow', key: SortKey) {
  const query = () => (list === 'published' ? store.publishedQuery : store.workflowQuery)
  return {
    getCanSort: () => true,
    getIsSorted: () => (query().sortBy === key ? query().sortOrder : false),
    toggleSorting: (desc?: boolean) => {
      const next = { sortBy: key, sortOrder: desc ? 'desc' : 'asc', page: 0 } as const
      return list === 'published' ? setPublished(next) : store.loadWorkflow(next)
    },
    toggleVisibility: () => {}
  }
}

function toggleStrength(strength: string) {
  const current = store.publishedQuery.strengths
  const strengths = current.includes(strength)
    ? current.filter(s => s !== strength)
    : [...current, strength]
  setPublished({ strengths, page: 0 })
}

const hasActiveFilters = computed(() => {
  const { q, strengths, sortBy, sortOrder } = store.publishedQuery
  return !!(
    q.trim() ||
    strengths.length ||
    sortBy !== DEFAULT.sortBy ||
    sortOrder !== DEFAULT.sortOrder
  )
})
function clearAllFilters() {
  search.value = ''
  setPublished({ ...DEFAULT, size: store.publishedQuery.size })
}

const search = ref(routeQuery().q)
const searched = computed(() => store.publishedQuery.q.trim())
const searchPublished = () =>
  search.value.trim() !== searched.value && setPublished({ q: search.value, page: 0 })
const searchPublishedSoon = useDebounceFn(searchPublished, 300)

const wfSearch = ref('')
const searchWorkflow = () =>
  wfSearch.value.trim() !== store.workflowQuery.q.trim() &&
  store.loadWorkflow({ q: wfSearch.value, page: 0 })
const searchWorkflowSoon = useDebounceFn(searchWorkflow, 300)

/** A new page starts at its list's heading, not at the pager below the old one */
const toHeading = (id: string) => document.getElementById(id)?.scrollIntoView({ block: 'start' })
async function publishedPage(query: Partial<PageQuery>) {
  await setPublished(query)
  toHeading('gda-published-heading')
}
async function workflowPage(query: Partial<PageQuery>) {
  await store.loadWorkflow(query)
  toHeading('gda-workflow-heading')
}

const editing = ref<Association | null>(null)
const formKey = ref(0)
const formOpen = ref(false)
const formCard = ref<ComponentPublicInstance | null>(null)

const canCurate = computed(() => auth.isCurator)

/**
 * Susceptibility gets its own table so it is never read as a Mendelian class (#437).
 * The server sorts Mendelian first, so a page holds one or both tables; the Mendelian
 * one stays for the loading and empty rows of an empty page.
 */
const publishedGroups = computed(() =>
  RELATIONSHIP_TYPES.map(type => ({
    type,
    records: store.published.filter(r => (r.relationship_type ?? 'mendelian') === type)
  })).filter(g => g.records.length || (g.type === 'mendelian' && !store.published.length))
)

/** Published on import because only an AI approved it in Gene Curator (#639) */
const pendingHuman = (r: Association) =>
  r.status === 'published' && r.approval_kind === 'ai' && !r.human_reviewed_at

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
  setPublished(routeQuery())
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

        <!-- Search & filter bar, as on the genes table -->
        <Card class="gap-0 py-0">
          <CardContent class="px-4 py-3">
            <div class="flex flex-col gap-2 sm:flex-row">
              <form class="relative flex-1" role="search" @submit.prevent="searchPublished">
                <Search
                  :size="16"
                  aria-hidden="true"
                  class="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
                />
                <Input
                  id="gda-filter"
                  v-model="search"
                  type="search"
                  aria-label="Search published associations by gene, disease or MONDO/OMIM ID"
                  placeholder="Gene, disease or MONDO/OMIM ID, e.g. PKD1"
                  class="h-9 pl-9"
                  @input="searchPublishedSoon"
                />
              </form>
              <div class="flex flex-wrap gap-2">
                <Select :model-value="sortOption" @update:model-value="applySort">
                  <SelectTrigger aria-label="Sort by" class="h-9 w-[200px]">
                    <SelectValue placeholder="Sort by..." />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem v-for="opt in SORT_OPTIONS" :key="opt.value" :value="opt.value">
                      {{ opt.title }}
                    </SelectItem>
                  </SelectContent>
                </Select>

                <Popover>
                  <PopoverTrigger as-child>
                    <Button variant="outline" size="sm" class="h-9">
                      Classification
                      <Badge
                        v-if="store.publishedQuery.strengths.length"
                        variant="secondary"
                        class="ml-1 rounded-sm px-1 text-xs"
                      >
                        {{ store.publishedQuery.strengths.length }}
                      </Badge>
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent class="w-[280px] p-3" align="start">
                    <div class="space-y-2">
                      <template
                        v-for="(group, gi) in [
                          { type: 'mendelian', strengths: MENDELIAN_STRENGTHS },
                          { type: 'susceptibility', strengths: SUSCEPTIBILITY_STRENGTHS }
                        ] as const"
                        :key="group.type"
                      >
                        <Separator v-if="gi" />
                        <p class="text-sm font-medium">{{ RELATIONSHIP_LABELS[group.type] }}</p>
                        <div
                          v-for="strength in group.strengths"
                          :key="strength"
                          class="flex items-center gap-2"
                        >
                          <Checkbox
                            :id="`strength-${strength}`"
                            :model-value="store.publishedQuery.strengths.includes(strength)"
                            @update:model-value="toggleStrength(strength)"
                          />
                          <Label :for="`strength-${strength}`" class="text-sm">
                            {{ strength }}
                          </Label>
                        </div>
                      </template>
                      <Button
                        v-if="store.publishedQuery.strengths.length"
                        variant="ghost"
                        size="sm"
                        class="w-full"
                        @click="setPublished({ strengths: [], page: 0 })"
                      >
                        Clear
                      </Button>
                    </div>
                  </PopoverContent>
                </Popover>

                <Button
                  variant="outline"
                  size="icon-sm"
                  class="h-9 w-9"
                  :disabled="!hasActiveFilters"
                  aria-label="Clear all filters"
                  @click="clearAllFilters"
                >
                  <FilterX class="h-4 w-4" />
                </Button>
                <Button
                  variant="outline"
                  size="icon-sm"
                  class="h-9 w-9"
                  aria-label="Refresh data"
                  @click="store.loadPublished()"
                >
                  <RefreshCw class="h-4 w-4" :class="{ 'animate-spin': store.loading }" />
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader class="flex flex-row flex-wrap items-center justify-between gap-3">
            <CardTitle id="gda-published-heading" tag="h2" class="scroll-mt-20 text-xl">
              Published associations
            </CardTitle>
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
                    :disabled="!store.publishedTotal || store.loading"
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
                    Export this page as PDF
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </CardHeader>
          <CardContent class="space-y-6">
            <!-- Kept in the DOM while loading so the table does not shift (as on the genes table) -->
            <PaginationBar
              :class="['px-0', { invisible: !store.publishedTotal }]"
              :page="store.publishedQuery.page"
              :page-size="store.publishedQuery.size"
              :total="store.publishedTotal"
              :page-size-options="PAGE_SIZES"
              noun="association"
              @update:page="page => publishedPage({ page })"
              @update:page-size="size => publishedPage({ size, page: 0 })"
            />
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
                    <TableHead class="w-56">
                      <DataTableColumnHeader
                        :column="sortColumn('published', 'classification')"
                        :title="group.type === 'mendelian' ? 'Classification' : 'Risk association'"
                        :hideable="false"
                      />
                    </TableHead>
                    <TableHead>Evidence</TableHead>
                    <TableHead class="w-32 text-right">
                      <DataTableColumnHeader
                        :column="sortColumn('published', 'published')"
                        title="Published"
                        :hideable="false"
                      />
                    </TableHead>
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
                          searched
                            ? `No published associations match “${searched}”.`
                            : hasActiveFilters
                              ? 'No published associations match these filters.'
                              : 'No published associations yet.'
                        }}
                      </TableCell>
                    </TableRow>
                  </template>
                </TableBody>
              </Table>
            </section>
            <PaginationBar
              v-if="store.publishedTotal"
              class="px-0"
              :page="store.publishedQuery.page"
              :page-size="store.publishedQuery.size"
              :total="store.publishedTotal"
              :page-size-options="PAGE_SIZES"
              noun="association"
              @update:page="page => publishedPage({ page })"
              @update:page-size="size => publishedPage({ size, page: 0 })"
            />
          </CardContent>
        </Card>

        <template v-if="canCurate">
          <Card>
            <CardHeader class="flex flex-row flex-wrap items-center justify-between gap-3">
              <CardTitle id="gda-workflow-heading" tag="h2" class="scroll-mt-20 text-xl">
                Curation workflow
              </CardTitle>
              <div class="flex flex-wrap items-center gap-2">
                <form role="search" @submit.prevent="searchWorkflow">
                  <Input
                    v-model="wfSearch"
                    type="search"
                    aria-label="Search the curation workflow"
                    placeholder="Gene, disease or ID"
                    class="h-8 w-56"
                    @input="searchWorkflowSoon"
                  />
                </form>
                <Button
                  size="sm"
                  variant="outline"
                  :aria-pressed="store.workflowQuery.pendingHuman"
                  data-testid="wf-pending-human"
                  @click="
                    store.loadWorkflow({ pendingHuman: !store.workflowQuery.pendingHuman, page: 0 })
                  "
                >
                  Pending human review ({{ store.pendingHumanTotal }})
                </Button>
                <Button v-if="!formOpen" size="sm" @click="openForm(null)">
                  <Plus aria-hidden="true" />New draft
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <PaginationBar
                :class="['px-0', { invisible: !store.workflowTotal }]"
                :page="store.workflowQuery.page"
                :page-size="store.workflowQuery.size"
                :total="store.workflowTotal"
                :page-size-options="PAGE_SIZES"
                noun="record"
                @update:page="page => workflowPage({ page })"
                @update:page-size="size => workflowPage({ size, page: 0 })"
              />
              <Table class="max-lg:block">
                <TableHeader class="max-lg:sr-only">
                  <TableRow>
                    <TableHead class="w-16">MOI</TableHead>
                    <TableHead class="w-56">
                      <DataTableColumnHeader
                        :column="sortColumn('workflow', 'classification')"
                        title="Classification"
                        :hideable="false"
                      />
                    </TableHead>
                    <TableHead>Evidence</TableHead>
                    <TableHead>
                      <DataTableColumnHeader
                        :column="sortColumn('workflow', 'updated')"
                        title="Status · updated"
                        :hideable="false"
                      />
                    </TableHead>
                    <TableHead class="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody class="max-lg:block">
                  <AssociationRows
                    :records="store.workflow"
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
                  <TableRow v-if="!store.workflow.length && !store.loading">
                    <TableCell colspan="5" class="py-8 text-center text-muted-foreground">
                      {{
                        store.workflowQuery.pendingHuman
                          ? 'No records pending human review.'
                          : store.workflowQuery.q.trim()
                            ? `No workflow records match “${store.workflowQuery.q.trim()}”.`
                            : 'No associations in the workflow.'
                      }}
                    </TableCell>
                  </TableRow>
                </TableBody>
              </Table>
              <PaginationBar
                v-if="store.workflowTotal"
                class="px-0"
                :page="store.workflowQuery.page"
                :page-size="store.workflowQuery.size"
                :total="store.workflowTotal"
                :page-size-options="PAGE_SIZES"
                noun="record"
                @update:page="page => workflowPage({ page })"
                @update:page-size="size => workflowPage({ size, page: 0 })"
              />
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
