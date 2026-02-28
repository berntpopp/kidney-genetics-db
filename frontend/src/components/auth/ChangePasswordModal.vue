<script setup lang="ts">
import { ref, computed, watch } from 'vue'
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
import { KeyRound, Eye, EyeOff, Check, Circle } from 'lucide-vue-next'

const props = defineProps<{
  open: boolean
}>()

const emit = defineEmits<{
  'update:open': [value: boolean]
}>()

const authStore = useAuthStore()

// Static Zod schema with all password constraints
const changePasswordSchema = toTypedSchema(
  z
    .object({
      currentPassword: z.string().min(1, 'Current password is required'),
      newPassword: z
        .string()
        .min(8, 'Minimum 8 characters')
        .regex(/[A-Z]/, 'Must contain an uppercase letter')
        .regex(/[a-z]/, 'Must contain a lowercase letter')
        .regex(/[0-9]/, 'Must contain a number')
        .regex(/[!@#$%^&*(),.?":{}|<>]/, 'Must contain a special character'),
      confirmPassword: z.string().min(1, 'Please confirm your new password')
    })
    .refine(data => data.newPassword === data.confirmPassword, {
      message: 'Passwords must match',
      path: ['confirmPassword']
    })
)

const { handleSubmit, defineField, errors, resetForm } = useForm({
  validationSchema: changePasswordSchema
})

const [currentPassword, currentPasswordAttrs] = defineField('currentPassword', {
  validateOnBlur: true,
  validateOnInput: true
})
const [newPassword, newPasswordAttrs] = defineField('newPassword', {
  validateOnBlur: true,
  validateOnInput: true
})
const [confirmPassword, confirmPasswordAttrs] = defineField('confirmPassword', {
  validateOnBlur: true,
  validateOnInput: true
})

const showNewPassword = ref(false)

// Live password complexity checklist
const passwordRequirements = computed(() => [
  { label: 'At least 8 characters', met: (newPassword.value?.length ?? 0) >= 8 },
  { label: 'Uppercase letter (A\u2013Z)', met: /[A-Z]/.test(newPassword.value ?? '') },
  { label: 'Lowercase letter (a\u2013z)', met: /[a-z]/.test(newPassword.value ?? '') },
  { label: 'Number (0\u20139)', met: /[0-9]/.test(newPassword.value ?? '') },
  {
    label: 'Special character (!@#$%...)',
    met: /[!@#$%^&*(),.?":{}|<>]/.test(newPassword.value ?? '')
  }
])

const onSubmit = handleSubmit(async values => {
  const success = await authStore.changePassword(values.currentPassword, values.newPassword)

  if (success) {
    toast.success('Password changed successfully!', { duration: 5000 })
    setTimeout(() => {
      closeDialog()
    }, 2000)
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
      showNewPassword.value = false
      authStore.clearError()
    }
  }
)
</script>

<template>
  <Dialog :open="open" @update:open="emit('update:open', $event)">
    <DialogContent class="sm:max-w-[425px]">
      <DialogHeader>
        <div class="flex items-center gap-2">
          <KeyRound class="size-5 text-primary" />
          <DialogTitle>Change Password</DialogTitle>
        </div>
        <DialogDescription> Update your account password </DialogDescription>
      </DialogHeader>

      <form class="space-y-4" @submit.prevent="onSubmit">
        <!-- Current Password -->
        <div class="space-y-2">
          <Label for="change-current-password">Current Password</Label>
          <Input
            id="change-current-password"
            v-model="currentPassword"
            v-bind="currentPasswordAttrs"
            type="password"
            placeholder="Enter current password"
            :disabled="authStore.isLoading"
            :class="{ 'border-destructive': errors.currentPassword }"
          />
          <p v-if="errors.currentPassword" class="text-sm text-destructive">
            {{ errors.currentPassword }}
          </p>
        </div>

        <!-- New Password + complexity checklist -->
        <div class="space-y-2">
          <Label for="change-new-password">New Password</Label>
          <div class="relative">
            <Input
              id="change-new-password"
              v-model="newPassword"
              v-bind="newPasswordAttrs"
              :type="showNewPassword ? 'text' : 'password'"
              placeholder="Enter new password"
              :disabled="authStore.isLoading"
              class="pr-10"
              :class="{ 'border-destructive': errors.newPassword }"
            />
            <Button
              type="button"
              variant="ghost"
              size="icon"
              class="absolute right-0 top-0 h-full px-3 hover:bg-transparent"
              :disabled="authStore.isLoading"
              @click="showNewPassword = !showNewPassword"
            >
              <EyeOff v-if="showNewPassword" class="size-4 text-muted-foreground" />
              <Eye v-else class="size-4 text-muted-foreground" />
            </Button>
          </div>
          <p v-if="errors.newPassword" class="text-sm text-destructive">
            {{ errors.newPassword }}
          </p>

          <!-- Password complexity checklist -->
          <ul class="mt-2 space-y-1 text-xs">
            <li
              v-for="req in passwordRequirements"
              :key="req.label"
              class="flex items-center gap-2"
              :class="req.met ? 'text-green-600 dark:text-green-400' : 'text-muted-foreground'"
            >
              <Check v-if="req.met" class="size-3" />
              <Circle v-else class="size-3" />
              {{ req.label }}
            </li>
          </ul>
        </div>

        <!-- Confirm Password -->
        <div class="space-y-2">
          <Label for="change-confirm-password">Confirm New Password</Label>
          <Input
            id="change-confirm-password"
            v-model="confirmPassword"
            v-bind="confirmPasswordAttrs"
            type="password"
            placeholder="Re-enter new password"
            :disabled="authStore.isLoading"
            :class="{ 'border-destructive': errors.confirmPassword }"
          />
          <p v-if="errors.confirmPassword" class="text-sm text-destructive">
            {{ errors.confirmPassword }}
          </p>
        </div>

        <!-- Error display -->
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
              Changing...
            </span>
            <span v-else>Change Password</span>
          </Button>
        </DialogFooter>
      </form>
    </DialogContent>
  </Dialog>
</template>
