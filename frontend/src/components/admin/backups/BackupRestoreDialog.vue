<template>
  <Dialog :open="modelValue" @update:open="$emit('update:modelValue', $event)">
    <DialogContent class="max-w-[600px]">
      <DialogHeader>
        <DialogTitle class="flex items-center gap-2">
          <AlertTriangle class="size-5 text-yellow-600 dark:text-yellow-400" />
          Restore Database Backup
        </DialogTitle>
        <DialogDescription>
          Replace the current database with data from the selected backup.
        </DialogDescription>
      </DialogHeader>

      <Alert variant="destructive">
        <AlertTriangle class="size-4" />
        <AlertDescription>
          <strong>Warning:</strong> This will replace the current database with data from the
          selected backup. This action cannot be undone.
        </AlertDescription>
      </Alert>

      <div v-if="backup" class="space-y-3">
        <p class="text-sm font-medium">Selected Backup:</p>
        <div class="rounded-md border p-3 text-sm space-y-1">
          <div><span class="font-medium">Filename:</span> {{ backup.filename }}</div>
          <div><span class="font-medium">Created:</span> {{ formatDate(backup.created_at) }}</div>
          <div><span class="font-medium">Size:</span> {{ formatSize(backup.file_size_mb) }}</div>
        </div>
      </div>

      <div class="space-y-3">
        <div class="flex items-center justify-between">
          <Label for="safety-backup" class="cursor-pointer"
            >Create safety backup before restore (recommended)</Label
          >
          <Switch
            id="safety-backup"
            :checked="form.createSafetyBackup"
            @update:checked="form.createSafetyBackup = $event"
          />
        </div>

        <div class="flex items-center justify-between">
          <Label for="run-analyze" class="cursor-pointer"
            >Run ANALYZE after restore (recommended)</Label
          >
          <Switch
            id="run-analyze"
            :checked="form.runAnalyze"
            @update:checked="form.runAnalyze = $event"
          />
        </div>
      </div>

      <DialogFooter>
        <Button variant="outline" @click="handleCancel">Cancel</Button>
        <Button variant="destructive" :disabled="loading" @click="handleRestore">
          <span
            v-if="loading"
            class="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent"
          />
          Restore Database
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>

<script setup>
import { ref, watch } from 'vue'
import { AlertTriangle } from 'lucide-vue-next'
import { useBackupFormatters } from '@/composables/useBackupFormatters'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Alert, AlertDescription } from '@/components/ui/alert'

const { formatDate, formatSize } = useBackupFormatters()

const props = defineProps({
  modelValue: {
    type: Boolean,
    required: true
  },
  backup: {
    type: Object,
    default: null
  },
  loading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue', 'restore'])

// Form state
const form = ref({
  createSafetyBackup: true,
  runAnalyze: true
})

// Methods
const handleRestore = () => {
  emit('restore', { ...form.value })
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
        createSafetyBackup: true,
        runAnalyze: true
      }
    }
  }
)
</script>
