<template>
  <v-container class="fill-height" fluid>
    <v-row align="center" justify="center" class="fill-height">
      <v-col cols="12" sm="8" md="4" lg="3">
        <v-card elevation="8" class="mx-auto">
          <!-- Logo and Title -->
          <v-card-text class="text-center pt-8 pb-4">
            <div class="d-flex align-center justify-center mb-4">
              <KidneyGeneticsLogo :size="64" variant="kidneys" :animated="false" />
            </div>
            <h1 class="text-h4 font-weight-medium mb-2">Reset Password</h1>
            <p class="text-body-2 text-medium-emphasis">
              Enter your email address and we'll send you instructions to reset your password
            </p>
          </v-card-text>

          <!-- Reset Form -->
          <v-card-text class="px-6 pb-2">
            <v-form ref="form" v-model="valid" @submit.prevent="handleSubmit">
              <v-text-field
                v-model="email"
                label="Email Address"
                density="compact"
                variant="outlined"
                prepend-inner-icon="mdi-email"
                :rules="[rules.required, rules.email]"
                :disabled="authStore.isLoading || successMessage"
                class="mb-4"
                autofocus
              />

              <v-alert
                v-if="successMessage"
                type="success"
                density="compact"
                variant="tonal"
                class="mb-4"
              >
                {{ successMessage }}
              </v-alert>

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

              <v-btn
                block
                color="primary"
                size="large"
                variant="flat"
                :loading="authStore.isLoading"
                :disabled="!valid || successMessage"
                class="mb-2"
                @click="handleSubmit"
              >
                Send Reset Email
              </v-btn>
            </v-form>
          </v-card-text>

          <!-- Footer -->
          <v-card-text class="text-center pb-6 pt-0">
            <v-btn variant="text" size="small" :to="'/login'" prepend-icon="mdi-arrow-left">
              Back to Login
            </v-btn>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { ref } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'
import KidneyGeneticsLogo from '@/components/KidneyGeneticsLogo.vue'

const authStore = useAuthStore()
const router = useRouter()

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
      router.push('/login')
    }, 3000)
  }
}
</script>

<style scoped>
.fill-height {
  min-height: calc(100vh - 64px - 100px);
}
</style>
