<template>
  <v-dialog
    :model-value="modelValue"
    max-width="600"
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <v-card>
      <v-card-title class="d-flex align-center">
        <DatabaseZap class="mr-2 size-5 text-primary" />
        Create Database Backup
      </v-card-title>

      <v-card-text>
        <v-alert type="info" variant="tonal" class="mb-4" density="compact">
          This will create a complete backup of the database. The process may take several minutes
          depending on database size.
        </v-alert>

        <v-text-field
          v-model="form.description"
          label="Description (optional)"
          density="compact"
          variant="outlined"
          placeholder="e.g., Before major update"
          class="mb-3"
        />

        <v-select
          v-model="form.compressionLevel"
          label="Compression Level"
          :items="compressionLevels"
          density="compact"
          variant="outlined"
          hint="Higher = better compression but slower"
          persistent-hint
          class="mb-3"
        />

        <v-select
          v-model="form.parallelJobs"
          label="Parallel Jobs"
          :items="parallelJobOptions"
          density="compact"
          variant="outlined"
          hint="More jobs = faster backup on multi-core systems"
          persistent-hint
          class="mb-3"
        />

        <v-switch
          v-model="form.includeLogs"
          label="Include system logs"
          density="compact"
          color="warning"
          hide-details
          class="mb-2"
        />

        <v-switch
          v-model="form.includeCache"
          label="Include cache tables"
          density="compact"
          color="warning"
          hide-details
        />
      </v-card-text>

      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" @click="handleCancel">Cancel</v-btn>
        <v-btn color="primary" variant="elevated" :loading="loading" @click="handleCreate">
          Create Backup
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, watch } from 'vue'
import { DatabaseZap } from 'lucide-vue-next'

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
