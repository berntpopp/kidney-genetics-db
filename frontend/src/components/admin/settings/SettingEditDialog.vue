<template>
  <v-dialog
    :model-value="modelValue"
    max-width="600"
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <v-card>
      <v-card-title class="d-flex align-center">
        <Pencil class="size-5 mr-2" />
        Edit Setting
      </v-card-title>

      <v-card-text>
        <v-alert v-if="setting?.is_sensitive" type="warning" density="compact" class="mb-4">
          <AlertTriangle class="size-5 mr-2 inline-block" />
          This is a sensitive setting. Value will be masked in logs.
        </v-alert>

        <v-text-field
          v-if="setting"
          v-model="editValue"
          :label="setting.key"
          :type="getInputType(setting.value_type)"
          :disabled="setting.is_readonly"
          :hint="setting.description"
          persistent-hint
          variant="outlined"
          class="mb-4"
        />

        <v-textarea
          v-model="changeReason"
          label="Change Reason (Optional)"
          rows="3"
          variant="outlined"
          hint="Document why this change was made"
          persistent-hint
        />

        <v-alert v-if="setting?.requires_restart" type="warning" class="mt-4">
          <RotateCw class="size-5 mr-2 inline-block" />
          This change requires a server restart to take effect.
        </v-alert>
      </v-card-text>

      <v-card-actions>
        <v-spacer />
        <v-btn @click="$emit('update:modelValue', false)">Cancel</v-btn>
        <v-btn color="primary" :loading="loading" :disabled="!hasChanges" @click="handleSave">
          Save Changes
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import { Pencil, AlertTriangle, RotateCw } from 'lucide-vue-next'

const props = defineProps({
  modelValue: Boolean,
  setting: Object,
  loading: Boolean
})

const emit = defineEmits(['update:modelValue', 'save'])

const editValue = ref(null)
const changeReason = ref('')
const originalValue = ref(null)

watch(
  () => props.setting,
  newSetting => {
    if (newSetting) {
      editValue.value = newSetting.value
      originalValue.value = newSetting.value
    }
  },
  { immediate: true }
)

const hasChanges = computed(() => {
  return editValue.value !== originalValue.value
})

const getInputType = valueType => {
  if (valueType === 'number') return 'number'
  if (valueType === 'boolean') return 'checkbox'
  return 'text'
}

const handleSave = () => {
  emit('save', {
    value: editValue.value,
    reason: changeReason.value
  })
  changeReason.value = ''
}
</script>
