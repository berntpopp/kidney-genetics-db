<script setup lang="ts">
/** Public form: report a problem or suggestion on a curated gene (reviewed by curators). */
import { ref } from 'vue'
import { isAxiosError } from 'axios'
import { MessageSquareWarning } from 'lucide-vue-next'
import { curationReportsApi, type ReportKind } from '@/api/curationReports'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@/components/ui/select'

const props = defineProps<{ symbol: string }>()

const open = ref(false)
const kind = ref<ReportKind>('problem')
const message = ref('')
const name = ref('')
const email = ref('')
const website = ref('')
const sending = ref(false)
const sent = ref(false)
const error = ref('')

async function submit() {
  error.value = ''
  sending.value = true
  try {
    await curationReportsApi.submit({
      gene_symbol: props.symbol,
      kind: kind.value,
      message: message.value.trim(),
      reporter_name: name.value.trim() || undefined,
      reporter_email: email.value.trim() || undefined,
      website: website.value
    })
    sent.value = true
  } catch (e) {
    const status = isAxiosError(e) ? e.response?.status : undefined
    error.value =
      status === 429
        ? 'Too many reports, try later'
        : status === 422
          ? 'Please check the message and email address.'
          : 'Could not send the report. Please try again later.'
  } finally {
    sending.value = false
  }
}

function onOpenChange(value: boolean) {
  open.value = value
  if (value) {
    sent.value = false
    message.value = ''
    error.value = ''
  }
}
</script>

<template>
  <Dialog :open="open" @update:open="onOpenChange">
    <DialogTrigger as-child>
      <Button variant="outline" size="sm">
        <MessageSquareWarning class="size-4" aria-hidden="true" />
        Report a problem or suggestion
      </Button>
    </DialogTrigger>
    <DialogContent class="sm:max-w-lg">
      <DialogHeader>
        <DialogTitle>Report a problem or suggestion</DialogTitle>
        <DialogDescription>
          About {{ symbol }}. The curators will review it. Name and email are optional; they are
          shown only to curators.
        </DialogDescription>
      </DialogHeader>

      <p v-if="sent" role="status" data-testid="report-sent">
        Thanks — the curators will review it.
      </p>
      <form v-else class="space-y-4" @submit.prevent="submit">
        <div class="space-y-1.5">
          <Label for="report-kind">Type</Label>
          <Select v-model="kind">
            <SelectTrigger id="report-kind" class="w-full"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="problem">Problem</SelectItem>
              <SelectItem value="suggestion">Suggestion</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div class="space-y-1.5">
          <Label for="report-message">Message</Label>
          <textarea
            id="report-message"
            v-model="message"
            required
            maxlength="4000"
            rows="5"
            class="border-input w-full rounded-md border bg-transparent px-3 py-2 text-sm shadow-xs outline-none focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50"
          />
        </div>
        <div class="grid gap-4 sm:grid-cols-2">
          <div class="space-y-1.5">
            <Label for="report-name">Name (optional)</Label>
            <Input id="report-name" v-model="name" maxlength="200" autocomplete="name" />
          </div>
          <div class="space-y-1.5">
            <Label for="report-email">Email (optional)</Label>
            <Input
              id="report-email"
              v-model="email"
              type="email"
              maxlength="320"
              autocomplete="email"
            />
          </div>
        </div>
        <!-- Honeypot: invisible to people and assistive tech; bots fill it -->
        <div class="hidden" aria-hidden="true">
          <input v-model="website" name="website" tabindex="-1" autocomplete="off" />
        </div>
        <p v-if="error" role="alert" class="text-sm text-destructive">{{ error }}</p>
        <DialogFooter>
          <Button type="submit" :disabled="sending || !message.trim()">
            {{ sending ? 'Sending…' : 'Send' }}
          </Button>
        </DialogFooter>
      </form>
    </DialogContent>
  </Dialog>
</template>
