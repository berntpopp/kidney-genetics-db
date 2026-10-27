<script setup lang="ts">
import { ref, useTemplateRef, watch } from 'vue'
import { z } from 'zod/v3'
import { toTypedSchema } from '@vee-validate/zod'
import { useForm } from 'vee-validate'
import { useAuthStore } from '@/stores/auth'
import { toast } from 'vue-sonner'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form'
import FormAlert from './FormAlert.vue'
import { focusFirstInvalid } from './focusFirstInvalid'

const props = defineProps<{
  open: boolean
}>()

const emit = defineEmits<{
  'update:open': [value: boolean]
}>()

const authStore = useAuthStore()

// Static Zod schema
const forgotPasswordSchema = toTypedSchema(
  z.object({
    email: z.string().min(1, 'Email is required').email('Enter a valid email address')
  })
)

const { handleSubmit, resetForm } = useForm({
  validationSchema: forgotPasswordSchema,
  initialValues: { email: '' }
})

const formRef = useTemplateRef('form')

const submitted = ref(false)

const onSubmit = handleSubmit(
  async values => {
    const success = await authStore.requestPasswordReset(values.email)

    if (success) {
      submitted.value = true
      toast.success(
        'If an account uses this address, a reset link is on its way. It is valid for one hour.',
        {
          duration: 5000
        }
      )
      setTimeout(() => {
        closeDialog()
      }, 3000)
    }
  },
  () => focusFirstInvalid(formRef.value)
)

const closeDialog = () => {
  emit('update:open', false)
}

// Clear form and errors when dialog opens
watch(
  () => props.open,
  isOpen => {
    if (isOpen) {
      resetForm()
      submitted.value = false
      authStore.clearError()
    }
  }
)
</script>

<template>
  <Dialog :open="open" @update:open="emit('update:open', $event)">
    <DialogContent class="sm:max-w-[400px]">
      <DialogHeader>
        <DialogTitle>Forgot your password?</DialogTitle>
        <DialogDescription>
          Enter your account email. Where reset by email is available, we send you a link; otherwise
          an administrator can reset your password.
        </DialogDescription>
      </DialogHeader>

      <form ref="form" class="space-y-4" novalidate @submit.prevent="onSubmit">
        <FormField v-slot="{ componentField }" name="email">
          <FormItem>
            <FormLabel>Email</FormLabel>
            <FormControl>
              <Input
                v-bind="componentField"
                type="email"
                autocomplete="email"
                :disabled="authStore.isLoading || submitted"
              />
            </FormControl>
            <FormMessage />
          </FormItem>
        </FormField>

        <FormAlert v-if="submitted" tone="success">
          If an account uses this address, a reset link is on its way. It is valid for one hour.
        </FormAlert>

        <FormAlert v-if="authStore.error">{{ authStore.error }}</FormAlert>

        <DialogFooter class="gap-2 sm:gap-2">
          <Button
            type="button"
            variant="outline"
            :disabled="authStore.isLoading"
            @click="closeDialog"
          >
            {{ submitted ? 'Close' : 'Cancel' }}
          </Button>
          <Button type="submit" :disabled="authStore.isLoading || submitted">
            {{ authStore.isLoading ? 'Sending…' : 'Send reset link' }}
          </Button>
        </DialogFooter>
      </form>
    </DialogContent>
  </Dialog>
</template>
