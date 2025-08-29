<template>
  <v-dialog v-model="dialog" max-width="400" persistent>
    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon color="primary" class="mr-2">mdi-lock-reset</v-icon>
        <span>Change Password</span>
      </v-card-title>

      <v-card-text>
        <v-form ref="form" v-model="valid" @submit.prevent="handleSubmit">
          <v-text-field
            v-model="currentPassword"
            label="Current Password"
            density="compact"
            variant="outlined"
            prepend-inner-icon="mdi-lock"
            type="password"
            :rules="[rules.required]"
            :disabled="authStore.isLoading"
            class="mb-3"
          />

          <v-text-field
            v-model="newPassword"
            label="New Password"
            density="compact"
            variant="outlined"
            prepend-inner-icon="mdi-lock-plus"
            :type="showPassword ? 'text' : 'password'"
            :append-inner-icon="showPassword ? 'mdi-eye' : 'mdi-eye-off'"
            :rules="[rules.required, rules.minLength, rules.complexity]"
            :disabled="authStore.isLoading"
            class="mb-3"
            @click:append-inner="showPassword = !showPassword"
          />

          <v-text-field
            v-model="confirmPassword"
            label="Confirm New Password"
            density="compact"
            variant="outlined"
            prepend-inner-icon="mdi-lock-check"
            type="password"
            :rules="[rules.required, rules.passwordMatch]"
            :disabled="authStore.isLoading"
          />

          <v-alert
            v-if="successMessage"
            type="success"
            density="compact"
            variant="tonal"
            class="mt-4"
          >
            {{ successMessage }}
          </v-alert>

          <v-alert
            v-if="authStore.error"
            type="error"
            density="compact"
            variant="tonal"
            closable
            class="mt-4"
            @click:close="authStore.clearError()"
          >
            {{ authStore.error }}
          </v-alert>
        </v-form>
      </v-card-text>

      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" :disabled="authStore.isLoading" @click="closeDialog"> Cancel </v-btn>
        <v-btn
          color="primary"
          variant="flat"
          :loading="authStore.isLoading"
          :disabled="!valid || successMessage"
          @click="handleSubmit"
        >
          Change Password
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useAuthStore } from '@/stores/auth'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue'])

const authStore = useAuthStore()

const dialog = computed({
  get: () => props.modelValue,
  set: value => emit('update:modelValue', value)
})

const form = ref(null)
const valid = ref(false)
const currentPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const showPassword = ref(false)
const successMessage = ref('')

const rules = {
  required: value => !!value || 'Required',
  minLength: value => value.length >= 8 || 'Minimum 8 characters',
  complexity: value => {
    const hasUpper = /[A-Z]/.test(value)
    const hasLower = /[a-z]/.test(value)
    const hasNumber = /[0-9]/.test(value)
    const hasSpecial = /[!@#$%^&*(),.?":{}|<>]/.test(value)

    return (
      (hasUpper && hasLower && hasNumber && hasSpecial) ||
      'Password must contain uppercase, lowercase, number, and special character'
    )
  },
  passwordMatch: value => value === newPassword.value || 'Passwords must match'
}

const handleSubmit = async () => {
  if (!valid.value) return

  const success = await authStore.changePassword(currentPassword.value, newPassword.value)

  if (success) {
    successMessage.value = 'Password changed successfully!'
    setTimeout(() => {
      closeDialog()
    }, 2000)
  }
}

const closeDialog = () => {
  dialog.value = false
  currentPassword.value = ''
  newPassword.value = ''
  confirmPassword.value = ''
  successMessage.value = ''
  showPassword.value = false
  authStore.clearError()
  form.value?.reset()
}

// Clear form when dialog opens
watch(dialog, newVal => {
  if (newVal) {
    currentPassword.value = ''
    newPassword.value = ''
    confirmPassword.value = ''
    successMessage.value = ''
    showPassword.value = false
    authStore.clearError()
    form.value?.reset()
  }
})
</script>
