<script setup lang="ts">
import { ref, watch } from 'vue'
import { z } from 'zod'
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
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { KeyRound } from 'lucide-vue-next'

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
    email: z.string().min(1, 'Email is required').email('Invalid email address')
  })
)

const { handleSubmit, defineField, errors, resetForm } = useForm({
  validationSchema: forgotPasswordSchema
})

const [email, emailAttrs] = defineField('email', {
  validateOnBlur: true,
  validateOnInput: true
})

const submitted = ref(false)

const onSubmit = handleSubmit(async values => {
  const success = await authStore.requestPasswordReset(values.email)

  if (success) {
    submitted.value = true
    toast.success('Password reset instructions have been sent to your email.', {
      duration: 5000
    })
    setTimeout(() => {
      closeDialog()
    }, 3000)
  }
})

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
        <div class="flex items-center gap-2">
          <KeyRound class="size-5 text-primary" />
          <DialogTitle>Reset Password</DialogTitle>
        </div>
        <DialogDescription>
          Enter your email address and we'll send you instructions to reset your password.
        </DialogDescription>
      </DialogHeader>

      <form class="space-y-4" @submit.prevent="onSubmit">
        <div class="space-y-2">
          <Label for="forgot-email">Email Address</Label>
          <Input
            id="forgot-email"
            v-model="email"
            v-bind="emailAttrs"
            type="email"
            placeholder="Enter your email"
            :disabled="authStore.isLoading || submitted"
            :class="{ 'border-destructive': errors.email }"
          />
          <p v-if="errors.email" class="text-sm text-destructive">
            {{ errors.email }}
          </p>
        </div>

        <div
          v-if="submitted"
          class="rounded-md border border-green-500/50 bg-green-500/10 p-3 text-sm text-green-700 dark:text-green-400"
        >
          Password reset instructions have been sent to your email.
        </div>

        <div
          v-if="authStore.error"
          class="rounded-md border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive"
        >
          {{ authStore.error }}
        </div>

        <DialogFooter class="gap-2 sm:gap-0">
          <Button
            type="button"
            variant="outline"
            :disabled="authStore.isLoading"
            @click="closeDialog"
          >
            Cancel
          </Button>
          <Button type="submit" :disabled="authStore.isLoading || submitted">
            <span v-if="authStore.isLoading" class="flex items-center gap-2">
              <span
                class="size-4 animate-spin rounded-full border-2 border-current border-t-transparent"
              />
              Sending...
            </span>
            <span v-else>Send Reset Email</span>
          </Button>
        </DialogFooter>
      </form>
    </DialogContent>
  </Dialog>
</template>
