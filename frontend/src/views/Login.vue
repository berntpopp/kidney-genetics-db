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
            <h1 class="text-h4 font-weight-medium mb-2">Welcome Back</h1>
            <p class="text-body-2 text-medium-emphasis">
              Sign in to access curator and admin features
            </p>
          </v-card-text>

          <!-- Login Form -->
          <v-card-text class="px-6 pb-2">
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
                autofocus
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
                @click:append-inner="showPassword = !showPassword"
                @keyup.enter="handleLogin"
              />

              <div class="d-flex align-center justify-space-between mb-4">
                <v-checkbox
                  v-model="rememberMe"
                  label="Remember me"
                  density="compact"
                  hide-details
                  class="flex-grow-0"
                />
                <v-btn
                  variant="text"
                  size="small"
                  color="primary"
                  :to="'/forgot-password'"
                  :disabled="authStore.isLoading"
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

              <v-btn
                block
                color="primary"
                size="large"
                variant="flat"
                :loading="authStore.isLoading"
                :disabled="!valid"
                class="mb-2"
                @click="handleLogin"
              >
                Sign In
              </v-btn>
            </v-form>
          </v-card-text>

          <!-- Footer -->
          <v-card-text class="text-center pb-6 pt-0">
            <v-btn variant="text" size="small" :to="'/'" prepend-icon="mdi-arrow-left">
              Back to Home
            </v-btn>
          </v-card-text>
        </v-card>

        <!-- Additional Info -->
        <div class="text-center mt-6">
          <p class="text-caption text-medium-emphasis">
            This is a public database. Authentication is only required for data curation and
            administration.
          </p>
        </div>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useRouter, useRoute } from 'vue-router'
import KidneyGeneticsLogo from '@/components/KidneyGeneticsLogo.vue'

const authStore = useAuthStore()
const router = useRouter()
const route = useRoute()

const form = ref(null)
const valid = ref(false)
const username = ref('')
const password = ref('')
const showPassword = ref(false)
const rememberMe = ref(false)

const rules = {
  required: value => !!value || 'Required'
}

const handleLogin = async () => {
  if (!valid.value) return

  const success = await authStore.login(username.value, password.value)

  if (success) {
    // Redirect to the page they came from, or home
    const redirectTo = route.query.redirect || '/'
    router.push(redirectTo)
  }
}

// Check if already logged in
onMounted(() => {
  if (authStore.isAuthenticated) {
    router.push('/')
  }
})
</script>

<style scoped>
.fill-height {
  min-height: calc(100vh - 64px - 100px);
}
</style>
