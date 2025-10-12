<template>
  <v-dialog
    :model-value="modelValue"
    max-width="500"
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon class="mr-2" color="error">mdi-delete</v-icon>
        Delete Backup
      </v-card-title>

      <v-card-text>
        <v-alert type="error" variant="tonal" class="mb-4" density="compact">
          This will permanently delete the backup file. This action cannot be undone.
        </v-alert>

        <div v-if="backup" class="text-body-2">
          <strong>Filename:</strong> {{ backup.filename }}
        </div>
        <div v-if="backup?.file_size_mb" class="text-body-2 mt-1">
          <strong>Size:</strong> {{ formatSize(backup.file_size_mb) }}
        </div>
      </v-card-text>

      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" @click="$emit('update:modelValue', false)">Cancel</v-btn>
        <v-btn color="error" variant="elevated" :loading="loading" @click="$emit('delete')">
          Delete
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { useBackupFormatters } from '@/composables/useBackupFormatters'

const { formatSize } = useBackupFormatters()

defineProps({
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

defineEmits(['update:modelValue', 'delete'])
</script>
