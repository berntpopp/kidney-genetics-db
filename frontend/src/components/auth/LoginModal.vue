<script setup lang="ts">
import { ref, watch } from 'vue'
import { z } from 'zod'
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
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { Eye, EyeOff, CircleUser } from 'lucide-vue-next'

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

const { handleSubmit, defineField, errors, resetForm } = useForm({
  validationSchema: loginSchema
})

const [username, usernameAttrs] = defineField('username', {
  validateOnBlur: true,
  validateOnInput: true
})
const [password, passwordAttrs] = defineField('password', {
  validateOnBlur: true,
  validateOnInput: true
})

const showPassword = ref(false)
const forgotPasswordOpen = ref(false)

const onSubmit = handleSubmit(async values => {
  const success = await authStore.login(values.username, values.password)
  if (success) {
    emit('login-success', authStore.user?.username ?? values.username)
    // Parent (AppHeader) handles closing the modal and showing toast
  }
})

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
      showPassword.value = false
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
          <CircleUser class="size-5 text-primary" />
          <DialogTitle>Login</DialogTitle>
        </div>
        <DialogDescription> Sign in with your username or email </DialogDescription>
      </DialogHeader>

      <form class="space-y-4" @submit.prevent="onSubmit">
        <div class="space-y-2">
          <Label for="login-username">Username or Email</Label>
          <Input
            id="login-username"
            v-model="username"
            v-bind="usernameAttrs"
            type="text"
            placeholder="Enter username or email"
            :disabled="authStore.isLoading"
            :class="{ 'border-destructive': errors.username }"
          />
          <p v-if="errors.username" class="text-sm text-destructive">
            {{ errors.username }}
          </p>
        </div>

        <div class="space-y-2">
          <Label for="login-password">Password</Label>
          <div class="relative">
            <Input
              id="login-password"
              v-model="password"
              v-bind="passwordAttrs"
              :type="showPassword ? 'text' : 'password'"
              placeholder="Enter password"
              :disabled="authStore.isLoading"
              class="pr-10"
              :class="{ 'border-destructive': errors.password }"
            />
            <Button
              type="button"
              variant="ghost"
              size="icon"
              class="absolute right-0 top-0 h-full px-3 hover:bg-transparent"
              :disabled="authStore.isLoading"
              @click="showPassword = !showPassword"
            >
              <EyeOff v-if="showPassword" class="size-4 text-muted-foreground" />
              <Eye v-else class="size-4 text-muted-foreground" />
            </Button>
          </div>
          <p v-if="errors.password" class="text-sm text-destructive">
            {{ errors.password }}
          </p>
        </div>

        <div class="flex justify-end">
          <Button
            type="button"
            variant="link"
            size="sm"
            class="px-0 text-primary"
            :disabled="authStore.isLoading"
            @click="openForgotPassword"
          >
            Forgot Password?
          </Button>
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
          <Button type="submit" :disabled="authStore.isLoading">
            <span v-if="authStore.isLoading" class="flex items-center gap-2">
              <span
                class="size-4 animate-spin rounded-full border-2 border-current border-t-transparent"
              />
              Signing in...
            </span>
            <span v-else>Login</span>
          </Button>
        </DialogFooter>
      </form>
    </DialogContent>
  </Dialog>

  <ForgotPasswordModal v-model:open="forgotPasswordOpen" />
</template>
