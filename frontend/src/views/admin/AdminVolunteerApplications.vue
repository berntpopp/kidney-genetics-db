<template>
  <!-- Admin review of public volunteer-curator applications -->
  <div :class="PAGE_CONTAINER">
    <AdminHeader
      title="Volunteer Applications"
      subtitle="Approval creates (or upgrades) the account and emails an invite."
    />
    <div class="mb-4 flex flex-wrap items-center gap-2">
      <Button
        v-for="f in FILTERS"
        :key="f.label"
        size="sm"
        :variant="filter === f.value ? 'default' : 'outline'"
        @click="filter = f.value"
      >
        {{ f.label
        }}<template v-if="f.value === 'pending' && pendingCount"> ({{ pendingCount }})</template>
      </Button>
    </div>

    <DataState
      :loading="loading"
      :error="error"
      error-title="Could not load the applications"
      :empty="!applications.length"
      empty-message="No applications."
      @retry="load"
    >
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Gene</TableHead>
            <TableHead>Applicant</TableHead>
            <TableHead>Affiliation</TableHead>
            <TableHead>ORCID</TableHead>
            <TableHead>Motivation</TableHead>
            <TableHead>Date</TableHead>
            <TableHead>Status</TableHead>
            <TableHead><span class="sr-only">Actions</span></TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow v-for="a in applications" :key="a.id">
            <TableCell class="font-medium">
              <RouterLink :to="`/genes/${a.gene_symbol}`" :class="LINK">{{
                a.gene_symbol
              }}</RouterLink>
            </TableCell>
            <TableCell class="break-all">
              {{ a.name }}
              <a :href="`mailto:${a.email}`" :class="LINK">{{ a.email }}</a>
            </TableCell>
            <TableCell>{{ a.affiliation || '—' }}</TableCell>
            <TableCell>
              <a
                v-if="a.orcid"
                :href="`https://orcid.org/${a.orcid}`"
                target="_blank"
                rel="noopener noreferrer"
                :class="LINK"
                >{{ a.orcid }}</a
              >
              <span v-else>—</span>
            </TableCell>
            <TableCell class="max-w-md whitespace-pre-wrap break-words">
              <span v-if="expanded.has(a.id) || a.motivation.length <= 140">{{
                a.motivation
              }}</span>
              <span v-else>{{ a.motivation.slice(0, 140) }}…</span>
              <button
                v-if="a.motivation.length > 140"
                type="button"
                :class="['ml-1', LINK]"
                :aria-expanded="expanded.has(a.id)"
                @click="toggle(a.id)"
              >
                {{ expanded.has(a.id) ? 'Show less' : 'Show more' }}
              </button>
            </TableCell>
            <TableCell class="tabular-nums">{{ a.created_at.slice(0, 10) }}</TableCell>
            <TableCell class="capitalize">{{ a.status }}</TableCell>
            <TableCell class="space-x-2 whitespace-nowrap">
              <template v-if="a.status === 'pending'">
                <Button size="sm" @click="ask(a, 'approved')">Approve</Button>
                <Button size="sm" variant="outline" @click="ask(a, 'rejected')">Reject</Button>
              </template>
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>
    </DataState>

    <AlertDialog v-model:open="showDialog">
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>
            {{ decision === 'approved' ? 'Approve' : 'Reject' }} {{ target?.name }} for
            {{ target?.gene_symbol }}?
          </AlertDialogTitle>
          <AlertDialogDescription>
            <template v-if="decision === 'approved'"
              >An account is created if none exists for {{ target?.email }}, and an email is
              sent.</template
            >
            <template v-else>A short polite email is sent to {{ target?.email }}.</template>
          </AlertDialogDescription>
        </AlertDialogHeader>
        <div v-if="decision === 'approved'" class="space-y-1.5">
          <Label for="decision-role">Role</Label>
          <Select v-model="role">
            <SelectTrigger id="decision-role" class="w-full"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="curator">Curator</SelectItem>
              <SelectItem value="viewer">Viewer</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div class="space-y-1.5">
          <Label for="decision-note">Note to the applicant (optional)</Label>
          <textarea
            id="decision-note"
            v-model="note"
            maxlength="2000"
            rows="3"
            class="border-input w-full rounded-md border bg-transparent px-3 py-2 text-sm shadow-xs outline-none focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50"
          />
        </div>
        <p v-if="decideError" role="alert" class="text-sm text-destructive">{{ decideError }}</p>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction
            :class="decision === 'rejected' ? buttonVariants({ variant: 'destructive' }) : ''"
            :disabled="deciding"
            @click.prevent="confirm"
          >
            {{ decision === 'approved' ? 'Approve' : 'Reject' }}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import {
  volunteerApplicationsApi,
  type Application,
  type ApplicationStatus
} from '@/api/volunteerApplications'
import AdminHeader from '@/components/admin/AdminHeader.vue'
import { DataState, PAGE_CONTAINER } from '@/components/shared'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle
} from '@/components/ui/alert-dialog'
import { Button, buttonVariants } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@/components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from '@/components/ui/table'

const LINK = 'text-primary underline-offset-4 hover:underline'

const FILTERS: { value: ApplicationStatus | undefined; label: string }[] = [
  { value: 'pending', label: 'Pending' },
  { value: 'approved', label: 'Approved' },
  { value: 'rejected', label: 'Rejected' },
  { value: undefined, label: 'All' }
]

const applications = ref<Application[]>([])
const pendingCount = ref(0)
const filter = ref<ApplicationStatus | undefined>('pending')
const loading = ref(true)
const error = ref('')
const expanded = ref(new Set<number>())

// `target` outlives the dialog: Radix closes it on the action click, before confirm() runs
const showDialog = ref(false)
const target = ref<Application | null>(null)
const decision = ref<'approved' | 'rejected'>('approved')
const role = ref<'viewer' | 'curator'>('curator')
const note = ref('')
const deciding = ref(false)
const decideError = ref('')

function toggle(id: number) {
  const next = new Set(expanded.value)
  if (!next.delete(id)) next.add(id)
  expanded.value = next
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await volunteerApplicationsApi.list({ status: filter.value })
    applications.value = res.data
    pendingCount.value = res.meta.pending_count
  } catch {
    error.value = 'Could not load the applications.'
  } finally {
    loading.value = false
  }
}

function ask(application: Application, value: 'approved' | 'rejected') {
  target.value = application
  showDialog.value = true
  decision.value = value
  role.value = 'curator'
  note.value = ''
  decideError.value = ''
}

async function confirm() {
  if (!target.value) return
  deciding.value = true
  decideError.value = ''
  try {
    await volunteerApplicationsApi.decide(target.value.id, {
      decision: decision.value,
      note: note.value.trim() || undefined,
      role: decision.value === 'approved' ? role.value : undefined
    })
    showDialog.value = false
    await load()
  } catch {
    decideError.value = 'Could not save the decision (it may already be decided).'
  } finally {
    deciding.value = false
  }
}

onMounted(load)
watch(filter, load)
</script>
