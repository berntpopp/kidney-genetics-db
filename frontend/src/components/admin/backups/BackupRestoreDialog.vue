<template>
  <v-dialog
    :model-value="modelValue"
    max-width="600"
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon class="mr-2" color="warning">mdi-alert</v-icon>
        Restore Database Backup
      </v-card-title>

      <v-card-text>
        <v-alert type="warning" variant="tonal" prominent class="mb-4">
          <div class="text-body-2">
            <strong>⚠️ Warning:</strong> This will replace the current database with data from the
            selected backup. This action cannot be undone.
          </div>
        </v-alert>

        <div v-if="backup" class="mb-4">
          <div class="text-subtitle-2 mb-2">Selected Backup:</div>
          <v-card variant="outlined" color="info">
            <v-card-text class="pa-3">
              <div class="text-body-2"><strong>Filename:</strong> {{ backup.filename }}</div>
              <div class="text-body-2">
                <strong>Created:</strong> {{ formatDate(backup.created_at) }}
              </div>
              <div class="text-body-2">
                <strong>Size:</strong> {{ formatSize(backup.file_size_mb) }}
              </div>
            </v-card-text>
          </v-card>
        </div>

        <v-switch
          v-model="form.createSafetyBackup"
          label="Create safety backup before restore (recommended)"
          density="compact"
          color="success"
          hide-details
          class="mb-2"
        />

        <v-switch
          v-model="form.runAnalyze"
          label="Run ANALYZE after restore (recommended)"
          density="compact"
          color="success"
          hide-details
        />
      </v-card-text>

      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" @click="handleCancel">Cancel</v-btn>
        <v-btn color="warning" variant="elevated" :loading="loading" @click="handleRestore">
          Restore Database
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useBackupFormatters } from '@/composables/useBackupFormatters'

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
