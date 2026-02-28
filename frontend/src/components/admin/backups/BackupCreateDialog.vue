<template>
  <Dialog :open="modelValue" @update:open="$emit('update:modelValue', $event)">
    <DialogContent class="max-w-[600px]">
      <DialogHeader>
        <DialogTitle class="flex items-center gap-2">
          <DatabaseZap class="size-5 text-primary" />
          Create Database Backup
        </DialogTitle>
        <DialogDescription>
          Create a complete backup of the database. The process may take several minutes depending
          on database size.
        </DialogDescription>
      </DialogHeader>

      <Alert>
        <AlertDescription>
          This will create a complete backup of the database. The process may take several minutes
          depending on database size.
        </AlertDescription>
      </Alert>

      <div class="space-y-4">
        <div class="space-y-2">
          <Label for="backup-description">Description (optional)</Label>
          <Input
            id="backup-description"
            v-model="form.description"
            placeholder="e.g., Before major update"
          />
        </div>

        <div class="space-y-2">
          <Label for="compression-level">Compression Level</Label>
          <Select v-model="form.compressionLevel">
            <SelectTrigger id="compression-level">
              <SelectValue placeholder="Select compression level" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem
                v-for="option in compressionLevels"
                :key="option.value"
                :value="option.value"
              >
                {{ option.title }}
              </SelectItem>
            </SelectContent>
          </Select>
          <p class="text-xs text-muted-foreground">Higher = better compression but slower</p>
        </div>

        <div class="space-y-2">
          <Label for="parallel-jobs">Parallel Jobs</Label>
          <Select v-model="form.parallelJobs">
            <SelectTrigger id="parallel-jobs">
              <SelectValue placeholder="Select parallel jobs" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem
                v-for="option in parallelJobOptions"
                :key="option.value"
                :value="option.value"
              >
                {{ option.title }}
              </SelectItem>
            </SelectContent>
          </Select>
          <p class="text-xs text-muted-foreground">
            More jobs = faster backup on multi-core systems
          </p>
        </div>

        <div class="flex items-center justify-between">
          <Label for="include-logs" class="cursor-pointer">Include system logs</Label>
          <Switch
            id="include-logs"
            :checked="form.includeLogs"
            @update:checked="form.includeLogs = $event"
          />
        </div>

        <div class="flex items-center justify-between">
          <Label for="include-cache" class="cursor-pointer">Include cache tables</Label>
          <Switch
            id="include-cache"
            :checked="form.includeCache"
            @update:checked="form.includeCache = $event"
          />
        </div>
      </div>

      <DialogFooter>
        <Button variant="outline" @click="handleCancel">Cancel</Button>
        <Button :disabled="loading" @click="handleCreate">
          <span
            v-if="loading"
            class="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent"
          />
          Create Backup
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>

<script setup>
import { ref, watch } from 'vue'
import { DatabaseZap } from 'lucide-vue-next'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { Alert, AlertDescription } from '@/components/ui/alert'

const props = defineProps({
  modelValue: {
    type: Boolean,
    required: true
  },
  loading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue', 'create'])

// Form state
const form = ref({
  description: '',
  includeLogs: false,
  includeCache: false,
  compressionLevel: 6,
  parallelJobs: 2
})

// Options
const compressionLevels = [
  { title: '0 - No compression (fastest)', value: 0 },
  { title: '1 - Minimal compression', value: 1 },
  { title: '3 - Light compression', value: 3 },
  { title: '6 - Balanced (default)', value: 6 },
  { title: '9 - Maximum compression (slowest)', value: 9 }
]

const parallelJobOptions = [
  { title: '1 - Single thread', value: 1 },
  { title: '2 - Two threads (default)', value: 2 },
  { title: '4 - Four threads', value: 4 },
  { title: '8 - Eight threads', value: 8 }
]

// Methods
const handleCreate = () => {
  emit('create', { ...form.value })
}

const handleCancel = () => {
  emit('update:modelValue', false)
}

// Reset form when dialog closes
watch(
  () => props.modelValue,
  newValue => {
    if (!newValue) {
      form.value = {
        description: '',
        includeLogs: false,
        includeCache: false,
        compressionLevel: 6,
        parallelJobs: 2
      }
    }
  }
)
</script>
