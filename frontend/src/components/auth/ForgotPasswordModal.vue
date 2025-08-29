<template>
  <v-dialog v-model="dialog" max-width="400" persistent>
    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon color="primary" class="mr-2">mdi-lock-reset</v-icon>
        <span>Reset Password</span>
      </v-card-title>

      <v-card-text>
        <p class="text-body-2 mb-4">
          Enter your email address and we'll send you instructions to reset your password.
        </p>

        <v-form ref="form" v-model="valid" @submit.prevent="handleSubmit">
          <v-text-field
            v-model="email"
            label="Email Address"
            density="compact"
            variant="outlined"
            prepend-inner-icon="mdi-email"
            :rules="[rules.required, rules.email]"
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
          Send Reset Email
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
const email = ref('')
const successMessage = ref('')

const rules = {
  required: value => !!value || 'Required',
  email: value => {
    const pattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    return pattern.test(value) || 'Invalid email address'
  }
}

const handleSubmit = async () => {
  if (!valid.value) return

  const success = await authStore.requestPasswordReset(email.value)

  if (success) {
    successMessage.value = 'Password reset instructions have been sent to your email.'
    setTimeout(() => {
      closeDialog()
    }, 3000)
  }
}

const closeDialog = () => {
  dialog.value = false
  email.value = ''
  successMessage.value = ''
  authStore.clearError()
  form.value?.reset()
}

// Clear form when dialog opens
watch(dialog, newVal => {
  if (newVal) {
    email.value = ''
    successMessage.value = ''
    authStore.clearError()
    form.value?.reset()
  }
})
</script>
