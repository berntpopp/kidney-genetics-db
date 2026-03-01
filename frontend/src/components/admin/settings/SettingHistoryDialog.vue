<template>
  <Dialog :open="modelValue" @update:open="$emit('update:modelValue', $event)">
    <DialogContent class="max-w-[800px]">
      <DialogHeader>
        <DialogTitle class="flex items-center gap-2">
          <History class="size-5" />
          Change History: {{ setting?.key }}
        </DialogTitle>
        <DialogDescription> View the history of changes made to this setting. </DialogDescription>
      </DialogHeader>

      <ScrollArea class="max-h-[400px]">
        <div v-if="history.length > 0" class="space-y-4">
          <div
            v-for="entry in history"
            :key="entry.id"
            class="relative pl-6 border-l-2 border-border"
          >
            <div class="absolute -left-[5px] top-1 h-2 w-2 rounded-full bg-primary" />
            <div class="rounded-md border p-3">
              <div class="flex items-center justify-between mb-1">
                <span class="text-xs text-muted-foreground">{{
                  formatDate(entry.changed_at)
                }}</span>
                <Badge variant="secondary" class="text-[10px]">
                  User #{{ entry.changed_by_id }}
                </Badge>
              </div>
              <div v-if="entry.ip_address" class="mb-1">
                <Badge variant="outline" class="text-[10px]">{{ entry.ip_address }}</Badge>
              </div>
              <div class="text-xs space-y-1">
                <div>
                  <span class="text-muted-foreground">Old:</span>
                  <code class="ml-1 rounded bg-muted px-1 py-0.5">{{
                    formatValue(entry.old_value)
                  }}</code>
                </div>
                <div>
                  <span class="text-muted-foreground">New:</span>
                  <code class="ml-1 rounded bg-muted px-1 py-0.5">{{
                    formatValue(entry.new_value)
                  }}</code>
                </div>
                <div v-if="entry.change_reason">
                  <span class="text-muted-foreground">Reason:</span> {{ entry.change_reason }}
                </div>
              </div>
            </div>
          </div>
        </div>

        <div v-if="loading" class="flex justify-center py-8">
          <div
            class="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent"
          />
        </div>

        <div
          v-if="!loading && history.length === 0"
          class="py-8 text-center text-sm text-muted-foreground"
        >
          No change history available
        </div>
      </ScrollArea>

      <DialogFooter>
        <Button variant="outline" @click="$emit('update:modelValue', false)">Close</Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>

<script setup>
import { ref, watch } from 'vue'
import { History } from 'lucide-vue-next'
import { useSettingsApi } from '@/composables/useSettingsApi'
import { formatDate } from '@/utils/formatters'
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
import { ScrollArea } from '@/components/ui/scroll-area'

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
