<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { z } from 'zod'
import { toTypedSchema } from '@vee-validate/zod'
import { useForm } from 'vee-validate'
import { useAuthStore } from '@/stores/auth'
import { useRouter, useRoute, RouterLink } from 'vue-router'
import KidneyGeneticsLogo from '@/components/KidneyGeneticsLogo.vue'
import { Card, CardContent, CardFooter } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { Eye, EyeOff, ArrowLeft } from 'lucide-vue-next'

const authStore = useAuthStore()
const router = useRouter()
const route = useRoute()

// Same Zod schema as LoginModal
const loginSchema = toTypedSchema(
  z.object({
    username: z.string().min(1, 'Username or email is required'),
    password: z.string().min(1, 'Password is required')
  })
)

const { handleSubmit, defineField, errors } = useForm({
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
const rememberMe = ref(false)

const onSubmit = handleSubmit(async values => {
  const success = await authStore.login(values.username, values.password)

  if (success) {
    const redirectTo = (route.query.redirect as string) || '/'
    router.push(redirectTo)
  }
})

// If already authenticated, redirect home
onMounted(() => {
  if (authStore.isAuthenticated) {
    router.push('/')
  }
})
</script>

<template>
  <div class="flex min-h-[calc(100vh-8rem)] items-center justify-center px-4">
    <div class="w-full max-w-sm">
      <Card>
        <!-- Logo and Title -->
        <CardContent class="pt-8 pb-4 text-center">
          <div class="mb-4 flex items-center justify-center">
            <KidneyGeneticsLogo :size="64" variant="kidneys" :animated="false" />
          </div>
          <h1 class="mb-2 text-2xl font-medium">Welcome Back</h1>
          <p class="text-sm text-muted-foreground">Sign in to access curator and admin features</p>
        </CardContent>

        <!-- Login Form -->
        <CardContent class="px-6 pb-2">
          <form class="space-y-4" @submit.prevent="onSubmit">
            <div class="space-y-2">
              <Label for="page-login-username">Username or Email</Label>
              <Input
                id="page-login-username"
                v-model="username"
                v-bind="usernameAttrs"
                type="text"
                placeholder="Enter username or email"
                :disabled="authStore.isLoading"
                autofocus
                :class="{ 'border-destructive': errors.username }"
              />
              <p v-if="errors.username" class="text-sm text-destructive">
                {{ errors.username }}
              </p>
            </div>

            <div class="space-y-2">
              <Label for="page-login-password">Password</Label>
              <div class="relative">
                <Input
                  id="page-login-password"
                  v-model="password"
                  v-bind="passwordAttrs"
                  :type="showPassword ? 'text' : 'password'"
                  placeholder="Enter password"
                  :disabled="authStore.isLoading"
                  class="pr-10"
                  :class="{ 'border-destructive': errors.password }"
                  @keyup.enter="onSubmit"
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

            <div class="flex items-center justify-between">
              <label class="flex items-center gap-2 text-sm">
                <input v-model="rememberMe" type="checkbox" class="size-4 rounded border-input" />
                Remember me
              </label>
              <RouterLink to="/forgot-password" class="text-sm text-primary hover:underline">
                Forgot Password?
              </RouterLink>
            </div>

            <div
              v-if="authStore.error"
              class="rounded-md border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive"
            >
              {{ authStore.error }}
            </div>

            <Button type="submit" class="w-full" size="lg" :disabled="authStore.isLoading">
              <span v-if="authStore.isLoading" class="flex items-center gap-2">
                <span
                  class="size-4 animate-spin rounded-full border-2 border-current border-t-transparent"
                />
                Signing in...
              </span>
              <span v-else>Sign In</span>
            </Button>
          </form>
        </CardContent>

        <!-- Footer -->
        <CardFooter class="justify-center pb-6 pt-0">
          <RouterLink
            to="/"
            class="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft class="size-4" />
            Back to Home
          </RouterLink>
        </CardFooter>
      </Card>

      <!-- Info text -->
      <p class="mt-6 text-center text-xs text-muted-foreground">
        This is a public database. Authentication is only required for data curation and
        administration.
      </p>
    </div>
  </div>
</template>
