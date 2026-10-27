<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useCurationStore } from '@/stores/curation'
import { type Association, type AssociationInput, type WorkflowAction } from '@/api/curation'
import AssociationForm from '@/components/curation/AssociationForm.vue'
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

const auth = useAuthStore()
const store = useCurationStore()

const geneFilter = ref('')
const editing = ref<Association | null>(null)
const formKey = ref(0)

const canCurate = computed(() => auth.isCurator)

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
            <div class="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Gene</TableHead>
                    <TableHead>Disease</TableHead>
                    <TableHead>Strength</TableHead>
                    <TableHead>Citations</TableHead>
                    <TableHead>Published</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody :aria-busy="store.loading">
                  <TableRow v-for="r in store.published" :key="r.id">
                    <TableCell>
                      <RouterLink
                        :to="`/genes/${r.gene_symbol}`"
                        class="font-medium underline-offset-4 hover:underline"
                      >
                        {{ r.gene_symbol }}
                      </RouterLink>
                    </TableCell>
                    <TableCell>
                      <OntologyTerm :id="r.disease_id" :name="r.disease_name" />
                    </TableCell>
                    <TableCell><Chip :classification="r.evidence_strength" /></TableCell>
                    <TableCell>
                      <OntologyTermList :terms="citationTerms(r)" source="PubMed" />
                    </TableCell>
                    <TableCell class="whitespace-nowrap tabular-nums">
                      {{ fmtDate(r.published_at) }}
                    </TableCell>
                  </TableRow>
                  <template v-if="store.loading && !store.published.length">
                    <TableRow v-for="n in 3" :key="`skeleton-${n}`" aria-hidden="true">
                      <TableCell v-for="c in 5" :key="c">
                        <div class="h-4 rounded-md bg-muted motion-safe:animate-pulse" />
                      </TableCell>
                    </TableRow>
                  </template>
                  <TableRow v-else-if="!store.published.length">
                    <TableCell colspan="5" class="py-8 text-center text-muted-foreground">
                      No published associations yet.
                    </TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </div>
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
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Gene</TableHead>
                      <TableHead>Disease</TableHead>
                      <TableHead>Evidence</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Updated</TableHead>
                      <TableHead>Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    <TableRow v-for="r in store.workflow" :key="r.id" :data-testid="`wf-${r.id}`">
                      <TableCell class="font-medium">{{ r.gene_symbol }}</TableCell>
                      <TableCell>
                        <OntologyTerm :id="r.disease_id" :name="r.disease_name" />
                      </TableCell>
                      <!-- What the reviewer approves: strength, citations and summary (issue 376) -->
                      <TableCell class="max-w-sm space-y-1">
                        <Chip :classification="r.evidence_strength" />
                        <OntologyTermList :terms="citationTerms(r)" source="PubMed" />
                        <p v-if="r.evidence_summary" class="text-xs text-muted-foreground">
                          {{ r.evidence_summary }}
                        </p>
                      </TableCell>
                      <TableCell>
                        <StatusBadge
                          :status="STATUS_KEYS[r.status] ?? r.status"
                          :label="STATUS_LABELS[r.status] ?? r.status"
                        />
                      </TableCell>
                      <TableCell class="whitespace-nowrap tabular-nums">
                        {{ fmtDate(r.updated_at) }}
                      </TableCell>
                      <TableCell class="space-x-2 whitespace-nowrap">
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
                      </TableCell>
                    </TableRow>
                    <TableRow v-if="!store.workflow.length && !store.loading">
                      <TableCell colspan="6" class="py-8 text-center text-muted-foreground">
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
