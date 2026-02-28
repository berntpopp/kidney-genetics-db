<template>
  <v-dialog
    :model-value="modelValue"
    max-width="700"
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <v-card>
      <v-card-title class="d-flex align-center">
        <Info class="mr-2 size-5 text-blue-500" />
        Backup Details
      </v-card-title>

      <v-card-text>
        <v-list v-if="backup" density="compact">
          <v-list-item>
            <v-list-item-title>Filename</v-list-item-title>
            <v-list-item-subtitle>{{ backup.filename }}</v-list-item-subtitle>
          </v-list-item>

          <v-list-item>
            <v-list-item-title>Status</v-list-item-title>
            <v-list-item-subtitle>
              <v-chip :color="getStatusColor(backup.status)" size="small" class="mt-1">
                <component :is="resolveMdiIcon(getStatusIcon(backup.status))" class="size-3 mr-1" />
                {{ backup.status }}
              </v-chip>
            </v-list-item-subtitle>
          </v-list-item>

          <v-list-item>
            <v-list-item-title>File Size</v-list-item-title>
            <v-list-item-subtitle>{{ formatSize(backup.file_size_mb) }}</v-list-item-subtitle>
          </v-list-item>

          <v-list-item>
            <v-list-item-title>Created</v-list-item-title>
            <v-list-item-subtitle>{{ formatDate(backup.created_at) }}</v-list-item-subtitle>
          </v-list-item>

          <v-list-item v-if="backup.completed_at">
            <v-list-item-title>Completed</v-list-item-title>
            <v-list-item-subtitle>{{ formatDate(backup.completed_at) }}</v-list-item-subtitle>
          </v-list-item>

          <v-list-item v-if="backup.duration_seconds">
            <v-list-item-title>Duration</v-list-item-title>
            <v-list-item-subtitle>{{
              formatDuration(backup.duration_seconds)
            }}</v-list-item-subtitle>
          </v-list-item>

          <v-list-item>
            <v-list-item-title>Trigger Source</v-list-item-title>
            <v-list-item-subtitle>
              <v-chip size="x-small" variant="outlined" class="mt-1">
                {{ backup.trigger_source }}
              </v-chip>
            </v-list-item-subtitle>
          </v-list-item>

          <v-list-item v-if="backup.description">
            <v-list-item-title>Description</v-list-item-title>
            <v-list-item-subtitle>{{ backup.description }}</v-list-item-subtitle>
          </v-list-item>

          <v-list-item v-if="backup.checksum_sha256">
            <v-list-item-title>SHA256 Checksum</v-list-item-title>
            <v-list-item-subtitle class="text-caption font-mono">
              {{ backup.checksum_sha256 }}
            </v-list-item-subtitle>
          </v-list-item>

          <v-divider class="my-2" />

          <v-list-item v-if="backup.compression_level !== undefined">
            <v-list-item-title>Compression Level</v-list-item-title>
            <v-list-item-subtitle>{{ backup.compression_level }}</v-list-item-subtitle>
          </v-list-item>

          <v-list-item v-if="backup.parallel_jobs">
            <v-list-item-title>Parallel Jobs</v-list-item-title>
            <v-list-item-subtitle>{{ backup.parallel_jobs }}</v-list-item-subtitle>
          </v-list-item>

          <v-list-item>
            <v-list-item-title>Include Logs</v-list-item-title>
            <v-list-item-subtitle>
              <component :is="backup.include_logs ? Check : X" class="size-4" />
            </v-list-item-subtitle>
          </v-list-item>

          <v-list-item>
            <v-list-item-title>Include Cache</v-list-item-title>
            <v-list-item-subtitle>
              <component :is="backup.include_cache ? Check : X" class="size-4" />
            </v-list-item-subtitle>
          </v-list-item>
        </v-list>

        <v-alert v-else type="info" variant="tonal" density="compact"> No backup selected </v-alert>
      </v-card-text>

      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" @click="$emit('update:modelValue', false)">Close</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { useBackupFormatters } from '@/composables/useBackupFormatters'
import { Info, Check, X } from 'lucide-vue-next'
import { resolveMdiIcon } from '@/utils/icons'

const { getStatusColor, getStatusIcon, formatSize, formatDate, formatDuration } =
  useBackupFormatters()

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

<style scoped>
.font-mono {
  font-family: 'Courier New', monospace;
}
</style>
