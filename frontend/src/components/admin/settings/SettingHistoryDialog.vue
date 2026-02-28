<template>
  <v-dialog
    :model-value="modelValue"
    max-width="800"
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <v-card>
      <v-card-title class="d-flex align-center">
        <History class="size-5 mr-2" />
        Change History: {{ setting?.key }}
      </v-card-title>

      <v-card-text>
        <v-timeline density="compact" side="end">
          <v-timeline-item
            v-for="entry in history"
            :key="entry.id"
            dot-color="primary"
            size="small"
          >
            <template #opposite>
              <div class="text-caption">{{ formatDate(entry.changed_at) }}</div>
            </template>

            <v-card>
              <v-card-text>
                <div class="d-flex justify-space-between align-center mb-2">
                  <span class="text-subtitle-2">Changed by User #{{ entry.changed_by_id }}</span>
                  <v-chip size="x-small">{{ entry.ip_address || 'Unknown' }}</v-chip>
                </div>

                <div class="mb-2">
                  <span class="text-caption text-medium-emphasis">Old:</span>
                  <code class="ml-2">{{ formatValue(entry.old_value) }}</code>
                </div>

                <div class="mb-2">
                  <span class="text-caption text-medium-emphasis">New:</span>
                  <code class="ml-2">{{ formatValue(entry.new_value) }}</code>
                </div>

                <div v-if="entry.change_reason" class="text-caption text-medium-emphasis">
                  Reason: {{ entry.change_reason }}
                </div>
              </v-card-text>
            </v-card>
          </v-timeline-item>
        </v-timeline>

        <div v-if="loading" class="text-center py-4">
          <v-progress-circular indeterminate color="primary" />
        </div>

        <div v-if="!loading && history.length === 0" class="text-center py-8 text-medium-emphasis">
          No change history available
        </div>
      </v-card-text>

      <v-card-actions>
        <v-spacer />
        <v-btn @click="$emit('update:modelValue', false)">Close</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, watch } from 'vue'
import { History } from 'lucide-vue-next'
import { useSettingsApi } from '@/composables/useSettingsApi'
import { formatDate } from '@/utils/formatters'

const props = defineProps({
  modelValue: Boolean,
  setting: Object
})

defineEmits(['update:modelValue'])

const { getSettingHistory } = useSettingsApi()
const history = ref([])
const loading = ref(false)

watch(
  () => props.modelValue,
  async isOpen => {
    if (isOpen && props.setting) {
      loading.value = true
      try {
        const data = await getSettingHistory(props.setting.id, 50)
        history.value = data.history || []
      } catch (error) {
        window.logService.error('Failed to load history:', error)
      } finally {
        loading.value = false
      }
    }
  }
)

const formatValue = value => {
  if (typeof value === 'object') {
    return JSON.stringify(value)
  }
  return String(value)
}
</script>
