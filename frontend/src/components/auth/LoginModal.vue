<template>
  <v-dialog v-model="dialog" max-width="400" persistent>
    <template #activator="{ props }">
      <v-btn v-bind="props" color="primary" size="small" variant="tonal">
        <v-icon start>mdi-login</v-icon>
        Login
      </v-btn>
    </template>

    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon color="primary" class="mr-2">mdi-account-circle</v-icon>
        <span>Login</span>
      </v-card-title>

      <v-card-text>
        <v-form ref="form" v-model="valid" @submit.prevent="handleLogin">
          <v-text-field
            v-model="username"
            label="Username or Email"
            density="compact"
            variant="outlined"
            prepend-inner-icon="mdi-account"
            :rules="[rules.required]"
            :disabled="authStore.isLoading"
            class="mb-3"
          />

          <v-text-field
            v-model="password"
            label="Password"
            density="compact"
            variant="outlined"
            prepend-inner-icon="mdi-lock"
            :type="showPassword ? 'text' : 'password'"
            :append-inner-icon="showPassword ? 'mdi-eye' : 'mdi-eye-off'"
            :rules="[rules.required]"
            :disabled="authStore.isLoading"
            class="mb-1"
            @click:append-inner="showPassword = !showPassword"
          />

          <div class="text-right mb-4">
            <v-btn
              variant="text"
              size="small"
              color="primary"
              :disabled="authStore.isLoading"
              @click="showForgotPassword"
            >
              Forgot Password?
            </v-btn>
          </div>

          <v-alert
            v-if="authStore.error"
            type="error"
            density="compact"
            variant="tonal"
            closable
            class="mb-4"
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
          :disabled="!valid"
          @click="handleLogin"
        >
          Login
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>

  <ForgotPasswordModal v-if="forgotPasswordDialog" v-model="forgotPasswordDialog" />
</template>

<script setup>
import { ref, watch } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'
import ForgotPasswordModal from './ForgotPasswordModal.vue'

const authStore = useAuthStore()
const router = useRouter()

const dialog = ref(false)
const valid = ref(false)
const form = ref(null)
const username = ref('')
const password = ref('')
const showPassword = ref(false)
const forgotPasswordDialog = ref(false)

const rules = {
  required: value => !!value || 'Required'
}

const handleLogin = async () => {
  if (!valid.value) return

  const success = await authStore.login(username.value, password.value)

  if (success) {
    closeDialog()
    // Optionally redirect to dashboard or refresh current page
    router.go(0)
  }
}

const closeDialog = () => {
  dialog.value = false
  username.value = ''
  password.value = ''
  authStore.clearError()
  form.value?.reset()
}

const showForgotPassword = () => {
  dialog.value = false
  forgotPasswordDialog.value = true
}

// Clear form when dialog opens
watch(dialog, newVal => {
  if (newVal) {
    username.value = ''
    password.value = ''
    authStore.clearError()
    form.value?.reset()
  }
})
</script>
