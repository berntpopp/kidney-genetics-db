<script setup lang="ts">
import { ref, useTemplateRef, watch } from 'vue'
import { z } from 'zod/v3'
import { toTypedSchema } from '@vee-validate/zod'
import { useForm } from 'vee-validate'
import { useAuthStore } from '@/stores/auth'
import ForgotPasswordModal from './ForgotPasswordModal.vue'
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
import PasswordInput from './PasswordInput.vue'
import { focusFirstInvalid } from './focusFirstInvalid'

const props = defineProps<{
  open: boolean
}>()

const emit = defineEmits<{
  'update:open': [value: boolean]
  'login-success': [username: string]
}>()

const authStore = useAuthStore()

// Static Zod schema -- NOT inside computed (preserves type inference)
const loginSchema = toTypedSchema(
  z.object({
    username: z.string().min(1, 'Username or email is required'),
    password: z.string().min(1, 'Password is required')
  })
)

const { handleSubmit, resetForm } = useForm({
  validationSchema: loginSchema,
  initialValues: { username: '', password: '' }
})

const formRef = useTemplateRef('form')
const forgotPasswordOpen = ref(false)

const onSubmit = handleSubmit(
  async values => {
    const success = await authStore.login(values.username, values.password)
    if (success) {
      emit('login-success', authStore.user?.username ?? values.username)
      // Parent (AppHeader) handles closing the modal and showing toast
    }
  },
  () => focusFirstInvalid(formRef.value)
)

const closeDialog = () => {
  emit('update:open', false)
}

const openForgotPassword = () => {
  emit('update:open', false)
  forgotPasswordOpen.value = true
}

// Clear form and errors when dialog opens
watch(
  () => props.open,
  isOpen => {
    if (isOpen) {
      resetForm()
      authStore.clearError()
    }
  }
)
</script>

<template>
  <Dialog :open="open" @update:open="emit('update:open', $event)">
    <DialogContent class="sm:max-w-[400px]">
      <DialogHeader>
        <DialogTitle>Sign in</DialogTitle>
        <DialogDescription>Sign in with your username or email.</DialogDescription>
      </DialogHeader>

      <form ref="form" class="space-y-4" novalidate @submit.prevent="onSubmit">
        <FormField v-slot="{ componentField }" name="username">
          <FormItem>
            <FormLabel>Username or email</FormLabel>
            <FormControl>
              <Input
                v-bind="componentField"
                type="text"
                autocomplete="username"
                :disabled="authStore.isLoading"
              />
            </FormControl>
            <FormMessage />
          </FormItem>
        </FormField>

        <FormField v-slot="{ componentField }" name="password">
          <FormItem>
            <div class="flex items-center justify-between">
              <FormLabel>Password</FormLabel>
              <Button
                type="button"
                variant="link"
                size="sm"
                class="h-auto px-0"
                :disabled="authStore.isLoading"
                @click="openForgotPassword"
              >
                Forgot password?
              </Button>
            </div>
            <FormControl>
              <PasswordInput
                v-bind="componentField"
                autocomplete="current-password"
                :disabled="authStore.isLoading"
              />
            </FormControl>
            <FormMessage />
          </FormItem>
        </FormField>

        <FormAlert v-if="authStore.error">{{ authStore.error }}</FormAlert>

        <DialogFooter class="gap-2 sm:gap-2">
          <Button
            type="button"
            variant="outline"
            :disabled="authStore.isLoading"
            @click="closeDialog"
          >
            Cancel
          </Button>
          <Button type="submit" :disabled="authStore.isLoading">
            {{ authStore.isLoading ? 'Signing in…' : 'Sign in' }}
          </Button>
        </DialogFooter>
      </form>
    </DialogContent>
  </Dialog>

  <ForgotPasswordModal v-model:open="forgotPasswordOpen" />
</template>
