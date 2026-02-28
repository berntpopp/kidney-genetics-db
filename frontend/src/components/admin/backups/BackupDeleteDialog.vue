<template>
  <AlertDialog :open="modelValue" @update:open="$emit('update:modelValue', $event)">
    <AlertDialogContent>
      <AlertDialogHeader>
        <AlertDialogTitle class="flex items-center gap-2">
          <Trash2 class="size-5 text-destructive" />
          Delete Backup
        </AlertDialogTitle>
        <AlertDialogDescription>
          This will permanently delete the backup file. This action cannot be undone.
        </AlertDialogDescription>
      </AlertDialogHeader>

      <div v-if="backup" class="space-y-1 text-sm">
        <div><span class="font-medium">Filename:</span> {{ backup.filename }}</div>
        <div v-if="backup?.file_size_mb">
          <span class="font-medium">Size:</span> {{ formatSize(backup.file_size_mb) }}
        </div>
      </div>

      <AlertDialogFooter>
        <AlertDialogCancel>Cancel</AlertDialogCancel>
        <AlertDialogAction
          class="bg-destructive text-destructive-foreground hover:bg-destructive/90"
          :disabled="loading"
          @click.prevent="$emit('delete')"
        >
          <span
            v-if="loading"
            class="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent"
          />
          Delete
        </AlertDialogAction>
      </AlertDialogFooter>
    </AlertDialogContent>
  </AlertDialog>
</template>

<script setup>
import { Trash2 } from 'lucide-vue-next'
import { useBackupFormatters } from '@/composables/useBackupFormatters'
import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogCancel,
  AlertDialogAction
} from '@/components/ui/alert-dialog'

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
