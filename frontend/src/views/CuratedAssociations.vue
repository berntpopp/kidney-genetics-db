<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useCurationStore } from '@/stores/curation'
import {
  diseaseUrl,
  pubmedUrl,
  type Association,
  type AssociationInput,
  type WorkflowAction
} from '@/api/curation'
import AssociationForm from '@/components/curation/AssociationForm.vue'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
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
  else await store.transition(r.id, action)
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
  <div class="container mx-auto max-w-6xl space-y-6 px-4 py-6">
    <header class="space-y-2">
      <h1 class="text-2xl font-bold">Expert-reviewed gene–disease associations</h1>
      <p class="text-sm text-muted-foreground">
        Associations curated by experts and published after review by a second curator. Diseases are
        identified by MONDO or OMIM IDs only; HPO terms describe phenotypes and are not used as
        disease identifiers.
      </p>
    </header>

    <div
      v-if="store.error"
      role="alert"
      class="rounded-md border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive"
    >
      {{ store.error }}
    </div>

    <Card>
      <CardHeader>
        <CardTitle>Published associations</CardTitle>
      </CardHeader>
      <CardContent class="space-y-4">
        <form class="flex items-end gap-2" @submit.prevent="store.loadPublished(geneFilter.trim())">
          <div class="space-y-1">
            <Label for="gda-filter">Gene symbol</Label>
            <Input id="gda-filter" v-model="geneFilter" placeholder="e.g. PKD1" />
          </div>
          <Button type="submit" variant="outline">Filter</Button>
        </form>
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
          <TableBody>
            <TableRow v-for="r in store.published" :key="r.id">
              <TableCell>
                <RouterLink :to="`/genes/${r.gene_symbol}`" class="font-medium underline">
                  {{ r.gene_symbol }}
                </RouterLink>
              </TableCell>
              <TableCell>
                {{ r.disease_name }}
                <a
                  :href="diseaseUrl(r.disease_id)"
                  target="_blank"
                  rel="noopener"
                  class="underline"
                >
                  {{ r.disease_id }}
                </a>
              </TableCell>
              <TableCell
                ><Badge variant="secondary">{{ r.evidence_strength }}</Badge></TableCell
              >
              <TableCell>
                <a
                  v-for="c in r.citations"
                  :key="c"
                  :href="pubmedUrl(c)"
                  target="_blank"
                  rel="noopener"
                  class="mr-2 underline"
                  >{{ c }}</a
                >
              </TableCell>
              <TableCell>{{ fmtDate(r.published_at) }}</TableCell>
            </TableRow>
            <TableRow v-if="!store.published.length">
              <TableCell colspan="5" class="text-center text-muted-foreground">
                {{ store.loading ? 'Loading…' : 'No published associations yet.' }}
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
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
          <CardTitle>{{ editing ? `Edit draft #${editing.id}` : 'New draft' }}</CardTitle>
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
          <CardTitle>Curation workflow</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Gene</TableHead>
                <TableHead>Disease</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Updated</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow v-for="r in store.workflow" :key="r.id" :data-testid="`wf-${r.id}`">
                <TableCell>{{ r.gene_symbol }}</TableCell>
                <TableCell>{{ r.disease_id }} — {{ r.disease_name }}</TableCell>
                <TableCell
                  ><Badge variant="outline">{{ r.status }}</Badge></TableCell
                >
                <TableCell>{{ fmtDate(r.updated_at) }}</TableCell>
                <TableCell class="space-x-2">
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
    </template>
  </div>
</template>
