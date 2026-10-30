<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useCurationStore } from '@/stores/curation'
import {
  MOI_TERMS,
  RELATIONSHIP_LABELS,
  RELATIONSHIP_TYPES,
  type Association,
  type AssociationInput,
  type WorkflowAction
} from '@/api/curation'
import AssociationDiagnostics from '@/components/curation/AssociationDiagnostics.vue'
import AssociationForm from '@/components/curation/AssociationForm.vue'
import AssociationProvenance from '@/components/curation/AssociationProvenance.vue'
import { Button } from '@/components/ui/button'
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator
} from '@/components/ui/breadcrumb'
import { TooltipProvider } from '@/components/ui/tooltip'
import {
  Chip,
  DataState,
  OntologyTerm,
  OntologyTermList,
  PageHeader,
  PAGE_CONTAINER,
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

const citationTerms = (r: Association) => r.citations.map(id => ({ id }))
/** Below lg each table row is a stacked card: a 6-column table cannot fit a phone */
const STACK = 'max-lg:block max-lg:min-w-0 max-lg:max-w-none max-lg:px-0 max-lg:py-1'
const moiText = (r: Association) =>
  r.moi ? (r.moi_label ?? MOI_TERMS[r.moi] ?? r.moi) : 'Not specified'
/** Records of one gene-disease pair under one header (one record per MOI / relationship) */
function byPair(records: Association[]) {
  const pairs = new Map<
    string,
    { key: string; gene: string; diseaseId: string; diseaseName: string; records: Association[] }
  >()
  for (const r of records) {
    const key = `${r.gene_symbol}|${r.disease_id}`
    if (!pairs.has(key))
      pairs.set(key, {
        key,
        gene: r.gene_symbol,
        diseaseId: r.disease_id,
        diseaseName: r.disease_name,
        records: []
      })
    pairs.get(key)!.records.push(r)
  }
  return [...pairs.values()]
}
const isSusceptibility = (r: Association) => r.relationship_type === 'susceptibility'

const auth = useAuthStore()
const store = useCurationStore()

const geneFilter = ref('')
const editing = ref<Association | null>(null)
const formKey = ref(0)

const canCurate = computed(() => auth.isCurator)

/** Susceptibility gets its own table so it is never read as a Mendelian class (#437) */
const publishedGroups = computed(() =>
  RELATIONSHIP_TYPES.map(type => ({
    type,
    records: store.published.filter(r => (r.relationship_type ?? 'mendelian') === type)
  })).filter(g => g.type === 'mendelian' || g.records.length)
)

/** Which workflow buttons the server will accept for this user (author vs. reviewer) */
function actionsFor(r: Association): { action: WorkflowAction | 'edit'; label: string }[] {
  const mine = r.curator_id === auth.user?.id
  if (r.status === 'draft')
    return mine
      ? [
          { action: 'edit', label: 'Edit' },
          { action: 'submit', label: 'Submit for review' }
        ]
      : []
  if (mine) return []
  return r.status === 'in_review'
    ? [
        { action: 'publish', label: 'Publish' },
        { action: 'return-to-draft', label: 'Return to draft' }
      ]
    : [{ action: 'return-to-draft', label: 'Return to draft' }]
}

async function onAction(r: Association, action: WorkflowAction | 'edit') {
  if (action === 'edit') editing.value = r
  else await store.transition(r, action)
}

async function onSave(input: AssociationInput) {
  const saved = editing.value
    ? await store.update(editing.value.id, input)
    : await store.create(input)
  if (saved) {
    editing.value = null
    formKey.value++
  }
}

const loadAll = () => {
  store.loadPublished(geneFilter.value.trim())
  if (canCurate.value) store.loadWorkflow()
}

onMounted(loadAll)
watch(canCurate, loadAll)

const fmtDate = (d: string | null) => (d ? new Date(d).toLocaleDateString() : '—')
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
          <CardHeader>
            <CardTitle tag="h2" class="text-xl">Published associations</CardTitle>
          </CardHeader>
          <CardContent class="space-y-4">
            <form
              class="flex items-end gap-2"
              @submit.prevent="store.loadPublished(geneFilter.trim())"
            >
              <div class="space-y-1">
                <Label for="gda-filter">Gene symbol</Label>
                <Input id="gda-filter" v-model="geneFilter" placeholder="e.g. PKD1" />
              </div>
              <Button type="submit" variant="outline">Filter</Button>
            </form>
            <section
              v-for="group in publishedGroups"
              :key="group.type"
              :data-testid="`published-${group.type}`"
              class="space-y-2"
            >
              <h3 class="text-sm font-medium">{{ RELATIONSHIP_LABELS[group.type] }}</h3>
              <div class="overflow-x-auto">
                <Table class="max-lg:block">
                  <TableHeader class="max-lg:sr-only">
                    <TableRow>
                      <TableHead>Inheritance</TableHead>
                      <TableHead>{{
                        group.type === 'mendelian' ? 'Strength' : 'Risk association'
                      }}</TableHead>
                      <TableHead>Details</TableHead>
                      <TableHead>Citations</TableHead>
                      <TableHead>Published</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody class="max-lg:block" :aria-busy="store.loading">
                    <template v-for="pair in byPair(group.records)" :key="pair.key">
                      <!-- One header per gene-disease pair, as ClinGen's "group by gene-disease pair" -->
                      <TableRow
                        data-testid="gda-pair"
                        class="bg-muted/40 hover:bg-muted/40 max-lg:block"
                      >
                        <TableCell
                          colspan="5"
                          class="whitespace-normal [overflow-wrap:anywhere] max-lg:block max-lg:px-2"
                        >
                          <RouterLink
                            :to="`/genes/${pair.gene}`"
                            class="mr-2 font-medium underline-offset-4 hover:underline"
                          >
                            {{ pair.gene }}
                          </RouterLink>
                          <OntologyTerm :id="pair.diseaseId" :name="pair.diseaseName" />
                        </TableCell>
                      </TableRow>
                      <TableRow
                        v-for="r in pair.records"
                        :key="r.id"
                        data-testid="gda-row"
                        class="max-lg:block max-lg:py-2"
                      >
                        <TableCell :class="[STACK, 'min-w-40 whitespace-normal']">{{
                          moiText(r)
                        }}</TableCell>
                        <TableCell :class="STACK">
                          <Chip
                            v-if="isSusceptibility(r)"
                            kind="neutral"
                            :label="r.evidence_strength"
                          />
                          <Chip v-else :classification="r.evidence_strength" />
                        </TableCell>
                        <TableCell
                          :class="[
                            STACK,
                            'max-w-md min-w-64 space-y-2 whitespace-normal [overflow-wrap:anywhere]'
                          ]"
                        >
                          <AssociationProvenance :record="r" :show-moi="false" />
                          <AssociationDiagnostics :diagnostics="r.diagnostics" />
                        </TableCell>
                        <TableCell :class="[STACK, 'min-w-32 whitespace-normal']">
                          <OntologyTermList :terms="citationTerms(r)" source="PubMed" />
                        </TableCell>
                        <TableCell :class="[STACK, 'whitespace-nowrap tabular-nums']">
                          <span class="lg:hidden">Published </span>{{ fmtDate(r.published_at) }}
                        </TableCell>
                      </TableRow>
                    </template>
                    <template v-if="group.type === 'mendelian'">
                      <template v-if="store.loading && !store.published.length">
                        <TableRow v-for="n in 3" :key="`skeleton-${n}`" aria-hidden="true">
                          <TableCell v-for="c in 5" :key="c">
                            <div class="h-4 rounded-md bg-muted motion-safe:animate-pulse" />
                          </TableCell>
                        </TableRow>
                      </template>
                      <TableRow v-else-if="!group.records.length">
                        <TableCell colspan="5" class="py-8 text-center text-muted-foreground">
                          No published associations yet.
                        </TableCell>
                      </TableRow>
                    </template>
                  </TableBody>
                </Table>
              </div>
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
            <CardHeader>
              <CardTitle tag="h2" class="text-xl">{{
                editing ? `Edit draft #${editing.id}` : 'New draft'
              }}</CardTitle>
            </CardHeader>
            <CardContent>
              <AssociationForm
                :key="formKey"
                :record="editing"
                :busy="store.loading"
                @save="onSave"
                @cancel="editing = null"
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle tag="h2" class="text-xl">Curation workflow</CardTitle>
            </CardHeader>
            <CardContent>
              <div class="overflow-x-auto">
                <Table class="max-lg:block">
                  <TableHeader class="max-lg:sr-only">
                    <TableRow>
                      <TableHead>Inheritance</TableHead>
                      <TableHead>Evidence</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Updated</TableHead>
                      <TableHead>Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody class="max-lg:block">
                    <template v-for="pair in byPair(store.workflow)" :key="pair.key">
                      <!-- One header per gene-disease pair, as ClinGen's "group by gene-disease pair" -->
                      <TableRow
                        data-testid="gda-pair"
                        class="bg-muted/40 hover:bg-muted/40 max-lg:block"
                      >
                        <TableCell
                          colspan="5"
                          class="whitespace-normal [overflow-wrap:anywhere] max-lg:block max-lg:px-2"
                        >
                          <RouterLink
                            :to="`/genes/${pair.gene}`"
                            class="mr-2 font-medium underline-offset-4 hover:underline"
                          >
                            {{ pair.gene }}
                          </RouterLink>
                          <OntologyTerm :id="pair.diseaseId" :name="pair.diseaseName" />
                        </TableCell>
                      </TableRow>
                      <TableRow
                        v-for="r in pair.records"
                        :key="r.id"
                        class="max-lg:block max-lg:py-2"
                        :data-testid="`wf-${r.id}`"
                      >
                        <TableCell :class="[STACK, 'min-w-40 whitespace-normal']">{{
                          moiText(r)
                        }}</TableCell>
                        <!-- What the reviewer approves: strength, citations and summary (issue 376) -->
                        <TableCell
                          :class="[
                            STACK,
                            'max-w-md min-w-64 space-y-1 whitespace-normal [overflow-wrap:anywhere]'
                          ]"
                        >
                          <Chip
                            v-if="isSusceptibility(r)"
                            kind="neutral"
                            :label="r.evidence_strength"
                          />
                          <Chip v-else :classification="r.evidence_strength" />
                          <OntologyTermList :terms="citationTerms(r)" source="PubMed" />
                          <p v-if="r.evidence_summary" class="text-xs text-muted-foreground">
                            {{ r.evidence_summary }}
                          </p>
                          <AssociationProvenance :record="r" :show-moi="false" />
                          <AssociationDiagnostics :diagnostics="r.diagnostics" />
                        </TableCell>
                        <TableCell :class="[STACK, 'space-y-1']">
                          <StatusBadge
                            :status="STATUS_KEYS[r.status] ?? r.status"
                            :label="STATUS_LABELS[r.status] ?? r.status"
                          />
                          <!-- Imported records still need a KGDB curator other than the author -->
                          <Chip
                            v-if="r.source === 'gene_curator'"
                            kind="neutral"
                            label="Gene Curator import"
                            tooltip="Curated in Gene Curator; publishing needs a KGDB curator other than the author"
                          />
                        </TableCell>
                        <TableCell :class="[STACK, 'whitespace-nowrap tabular-nums']">
                          <span class="lg:hidden">Updated </span>{{ fmtDate(r.updated_at) }}
                        </TableCell>
                        <TableCell :class="[STACK, 'whitespace-normal']">
                          <div class="flex min-w-36 flex-wrap gap-2">
                            <Button
                              v-for="a in actionsFor(r)"
                              :key="a.action"
                              size="sm"
                              variant="outline"
                              :disabled="store.loading"
                              @click="onAction(r, a.action)"
                            >
                              {{ a.label }}
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    </template>
                    <TableRow v-if="!store.workflow.length && !store.loading">
                      <TableCell colspan="5" class="py-8 text-center text-muted-foreground">
                        No associations in the workflow.
                      </TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </div>
              <p
                v-if="store.workflowTotal > store.workflow.length"
                class="text-sm text-muted-foreground"
              >
                Showing {{ store.workflow.length }} of {{ store.workflowTotal }}
              </p>
            </CardContent>
          </Card>
        </template>
      </div>
    </div>
  </TooltipProvider>
</template>
