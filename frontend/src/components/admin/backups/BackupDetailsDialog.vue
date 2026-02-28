<template>
  <Dialog :open="modelValue" @update:open="$emit('update:modelValue', $event)">
    <DialogContent class="max-w-[700px]">
      <DialogHeader>
        <DialogTitle class="flex items-center gap-2">
          <Info class="size-5 text-blue-500" />
          Backup Details
        </DialogTitle>
        <DialogDescription> Detailed information about the selected backup. </DialogDescription>
      </DialogHeader>

      <div v-if="backup" class="space-y-3 text-sm">
        <div class="grid grid-cols-[140px_1fr] gap-y-2">
          <span class="font-medium text-muted-foreground">Filename</span>
          <span>{{ backup.filename }}</span>

          <span class="font-medium text-muted-foreground">Status</span>
          <span>
            <Badge :variant="getStatusVariant(backup.status)">
              {{ backup.status }}
            </Badge>
          </span>

          <span class="font-medium text-muted-foreground">File Size</span>
          <span>{{ formatSize(backup.file_size_mb) }}</span>

          <span class="font-medium text-muted-foreground">Created</span>
          <span>{{ formatDate(backup.created_at) }}</span>

          <template v-if="backup.completed_at">
            <span class="font-medium text-muted-foreground">Completed</span>
            <span>{{ formatDate(backup.completed_at) }}</span>
          </template>

          <template v-if="backup.duration_seconds">
            <span class="font-medium text-muted-foreground">Duration</span>
            <span>{{ formatDuration(backup.duration_seconds) }}</span>
          </template>

          <span class="font-medium text-muted-foreground">Trigger Source</span>
          <span>
            <Badge variant="outline">{{ backup.trigger_source }}</Badge>
          </span>

          <template v-if="backup.description">
            <span class="font-medium text-muted-foreground">Description</span>
            <span>{{ backup.description }}</span>
          </template>

          <template v-if="backup.checksum_sha256">
            <span class="font-medium text-muted-foreground">SHA256 Checksum</span>
            <span class="font-mono text-xs break-all">{{ backup.checksum_sha256 }}</span>
          </template>
        </div>

        <div class="border-t pt-3">
          <div class="grid grid-cols-[140px_1fr] gap-y-2">
            <template v-if="backup.compression_level !== undefined">
              <span class="font-medium text-muted-foreground">Compression Level</span>
              <span>{{ backup.compression_level }}</span>
            </template>

            <template v-if="backup.parallel_jobs">
              <span class="font-medium text-muted-foreground">Parallel Jobs</span>
              <span>{{ backup.parallel_jobs }}</span>
            </template>

            <span class="font-medium text-muted-foreground">Include Logs</span>
            <span><component :is="backup.include_logs ? Check : X" class="size-4" /></span>

            <span class="font-medium text-muted-foreground">Include Cache</span>
            <span><component :is="backup.include_cache ? Check : X" class="size-4" /></span>
          </div>
        </div>
      </div>

      <div v-else class="py-4 text-center text-sm text-muted-foreground">No backup selected</div>

      <DialogFooter>
        <Button variant="outline" @click="$emit('update:modelValue', false)">Close</Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>

<script setup>
import { useBackupFormatters } from '@/composables/useBackupFormatters'
import { Info, Check, X } from 'lucide-vue-next'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'

const { getStatusColor, formatSize, formatDate, formatDuration } = useBackupFormatters()

const getStatusVariant = status => {
  const variants = {
    completed: 'default',
    running: 'secondary',
    failed: 'destructive',
    pending: 'outline'
  }
  return variants[status] || 'secondary'
}

defineProps({
  modelValue: {
    type: Boolean,
    required: true
  },
  backup: {
    type: Object,
    default: null
  }
})

defineEmits(['update:modelValue'])
</script>
