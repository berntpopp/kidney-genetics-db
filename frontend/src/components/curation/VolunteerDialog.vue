<script setup lang="ts">
/** Public form: apply to curate a gene (an admin reviews it; approval creates the account). */
import { ref } from 'vue'
import { isAxiosError } from 'axios'
import { HandHelping } from 'lucide-vue-next'
import { volunteerApplicationsApi } from '@/api/volunteerApplications'
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

const props = defineProps<{ symbol: string }>()

const open = ref(false)
const name = ref('')
const email = ref('')
const affiliation = ref('')
const orcid = ref('')
const motivation = ref('')
const consent = ref(false)
const website = ref('')
const sending = ref(false)
const sent = ref(false)
const error = ref('')

async function submit() {
  error.value = ''
  sending.value = true
  try {
    await volunteerApplicationsApi.submit({
      gene_symbol: props.symbol,
      name: name.value.trim(),
      email: email.value.trim(),
      affiliation: affiliation.value.trim() || undefined,
      orcid: orcid.value.trim() || undefined,
      motivation: motivation.value.trim(),
      website: website.value
    })
    sent.value = true
  } catch (e) {
    const status = isAxiosError(e) ? e.response?.status : undefined
    error.value =
      status === 429
        ? 'Too many applications, try later'
        : status === 400 || status === 422
          ? 'Please check the email address and the ORCID iD (0000-0000-0000-000X).'
          : 'Could not send the application. Please try again later.'
  } finally {
    sending.value = false
  }
}

function onOpenChange(value: boolean) {
  open.value = value
  if (value) {
    sent.value = false
    consent.value = false
    error.value = ''
  }
}
</script>

<template>
  <Dialog :open="open" @update:open="onOpenChange">
    <DialogTrigger as-child>
      <Button variant="outline" size="sm" aria-label="Volunteer to curate this gene">
        <HandHelping class="size-4" aria-hidden="true" />
        <span class="hidden sm:inline">Volunteer to curate</span>
      </Button>
    </DialogTrigger>
    <DialogContent class="sm:max-w-lg">
      <DialogHeader>
        <DialogTitle>Volunteer to curate {{ symbol }}</DialogTitle>
        <DialogDescription>
          An administrator reviews every application. Your details are shown only to administrators.
        </DialogDescription>
      </DialogHeader>

      <p v-if="sent" role="status" data-testid="volunteer-sent">
        Thanks — an admin will review your application and email you.
      </p>
      <form v-else class="space-y-4" @submit.prevent="submit">
        <div class="grid gap-4 sm:grid-cols-2">
          <div class="space-y-1.5">
            <Label for="vol-name">Name</Label>
            <Input id="vol-name" v-model="name" required maxlength="200" autocomplete="name" />
          </div>
          <div class="space-y-1.5">
            <Label for="vol-email">Email</Label>
            <Input
              id="vol-email"
              v-model="email"
              type="email"
              required
              maxlength="320"
              autocomplete="email"
            />
          </div>
        </div>
        <div class="grid gap-4 sm:grid-cols-2">
          <div class="space-y-1.5">
            <Label for="vol-affiliation">Affiliation (optional)</Label>
            <Input id="vol-affiliation" v-model="affiliation" maxlength="300" />
          </div>
          <div class="space-y-1.5">
            <Label for="vol-orcid">ORCID iD (optional)</Label>
            <Input
              id="vol-orcid"
              v-model="orcid"
              maxlength="19"
              placeholder="0000-0000-0000-000X"
              pattern="\d{4}-\d{4}-\d{4}-\d{3}[\dX]"
            />
          </div>
        </div>
        <div class="space-y-1.5">
          <Label for="vol-motivation">
            Why do you want to curate this gene? Relevant expertise, publications
          </Label>
          <textarea
            id="vol-motivation"
            v-model="motivation"
            required
            maxlength="4000"
            rows="5"
            class="border-input w-full rounded-md border bg-transparent px-3 py-2 text-sm shadow-xs outline-none focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50"
          />
        </div>
        <div class="flex items-start gap-2">
          <input id="vol-consent" v-model="consent" type="checkbox" class="mt-1 size-4" required />
          <Label for="vol-consent" class="font-normal">
            I agree that KGDB stores these details to review my application
          </Label>
        </div>
        <!-- Honeypot: invisible to people and assistive tech; bots fill it -->
        <div class="hidden" aria-hidden="true">
          <input v-model="website" name="website" tabindex="-1" autocomplete="off" />
        </div>
        <p v-if="error" role="alert" class="text-sm text-destructive">{{ error }}</p>
        <DialogFooter>
          <Button
            type="submit"
            :disabled="sending || !consent || !name.trim() || !email.trim() || !motivation.trim()"
          >
            {{ sending ? 'Sending…' : 'Send application' }}
          </Button>
        </DialogFooter>
      </form>
    </DialogContent>
  </Dialog>
</template>
