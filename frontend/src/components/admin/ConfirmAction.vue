<script setup lang="ts">
/**
 * The one admin confirmation for destructive or heavy actions (AlertDialog). The description
 * names the scope and what cannot be undone; `danger` styles the confirm button with the
 * danger token. Escape and Cancel close without emitting `confirm`.
 */
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle
} from '@/components/ui/alert-dialog'
import { buttonVariants } from '@/components/ui/button'

const open = defineModel<boolean>('open', { default: false })

withDefaults(
  defineProps<{
    title: string
    description?: string
    confirmLabel: string
    danger?: boolean
    disabled?: boolean
  }>(),
  { description: '', danger: false, disabled: false }
)

defineEmits<{ confirm: [] }>()
</script>

<template>
  <AlertDialog v-model:open="open">
    <AlertDialogContent>
      <AlertDialogHeader>
        <AlertDialogTitle>{{ title }}</AlertDialogTitle>
        <AlertDialogDescription as-child>
          <div class="space-y-2 text-sm text-muted-foreground">
            <slot>
              <p>{{ description }}</p>
            </slot>
          </div>
        </AlertDialogDescription>
      </AlertDialogHeader>
      <AlertDialogFooter>
        <AlertDialogCancel>Cancel</AlertDialogCancel>
        <AlertDialogAction
          :class="danger ? buttonVariants({ variant: 'destructive' }) : undefined"
          :disabled="disabled"
          @click="$emit('confirm')"
        >
          {{ confirmLabel }}
        </AlertDialogAction>
      </AlertDialogFooter>
    </AlertDialogContent>
  </AlertDialog>
</template>
