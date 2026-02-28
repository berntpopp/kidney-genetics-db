<template>
  <Dialog :open="modelValue" @update:open="$emit('update:modelValue', $event)">
    <DialogContent class="max-w-[600px]">
      <DialogHeader>
        <DialogTitle class="flex items-center gap-2">
          <Pencil class="size-5" />
          Edit Setting
        </DialogTitle>
        <DialogDescription> Modify the value of this configuration setting. </DialogDescription>
      </DialogHeader>

      <div class="space-y-4">
        <Alert v-if="setting?.is_sensitive" variant="destructive">
          <AlertTriangle class="size-4" />
          <AlertDescription>
            This is a sensitive setting. Value will be masked in logs.
          </AlertDescription>
        </Alert>

        <div v-if="setting" class="space-y-2">
          <Label :for="'setting-' + setting.key">{{ setting.key }}</Label>
          <Input
            :id="'setting-' + setting.key"
            v-model="editValue"
            :type="getInputType(setting.value_type)"
            :disabled="setting.is_readonly"
          />
          <p v-if="setting.description" class="text-xs text-muted-foreground">
            {{ setting.description }}
          </p>
        </div>

        <div class="space-y-2">
          <Label for="change-reason">Change Reason (Optional)</Label>
          <textarea
            id="change-reason"
            v-model="changeReason"
            rows="3"
            class="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            placeholder="Document why this change was made"
          />
        </div>

        <Alert v-if="setting?.requires_restart">
          <RotateCw class="size-4" />
          <AlertDescription>
            This change requires a server restart to take effect.
          </AlertDescription>
        </Alert>
      </div>

      <DialogFooter>
        <Button variant="outline" @click="$emit('update:modelValue', false)">Cancel</Button>
        <Button :disabled="!hasChanges || loading" @click="handleSave">
          <span
            v-if="loading"
            class="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent"
          />
          Save Changes
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import { Pencil, AlertTriangle, RotateCw } from 'lucide-vue-next'
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
import { Alert, AlertDescription } from '@/components/ui/alert'

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
