<script setup lang="ts">
import { onMounted, useTemplateRef } from 'vue'
import { z } from 'zod/v3'
import { toTypedSchema } from '@vee-validate/zod'
import { useForm } from 'vee-validate'
import { useAuthStore } from '@/stores/auth'
import { useRouter, useRoute, RouterLink } from 'vue-router'
import KidneyGeneticsLogo from '@/components/KidneyGeneticsLogo.vue'
import FormAlert from '@/components/auth/FormAlert.vue'
import PasswordInput from '@/components/auth/PasswordInput.vue'
import { focusFirstInvalid } from '@/components/auth/focusFirstInvalid'
import { Card, CardContent, CardFooter } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form'
import { ArrowLeft } from 'lucide-vue-next'
import { toast } from 'vue-sonner'

const authStore = useAuthStore()
const router = useRouter()
const route = useRoute()
const formRef = useTemplateRef('form')

// Same Zod schema as LoginModal
const loginSchema = toTypedSchema(
  z.object({
    username: z.string().min(1, 'Username or email is required'),
    password: z.string().min(1, 'Password is required')
  })
)

// Empty initial values so an empty submit shows the schema messages, not "Required"
const { handleSubmit } = useForm({
  validationSchema: loginSchema,
  initialValues: { username: '', password: '' }
})

const onSubmit = handleSubmit(
  async values => {
    const success = await authStore.login(values.username, values.password)

    if (success) {
      const redirectTo = (route.query.redirect as string) || '/'
      router.push(redirectTo)
    }
  },
  () => focusFirstInvalid(formRef.value)
)

// If already authenticated, redirect home
onMounted(() => {
  if (route.query.reason === 'password_changed') {
    toast.success('Password changed. Please sign in again.', { duration: 5000 })
  }
  if (authStore.isAuthenticated) {
    router.push('/')
  }
})
</script>

<template>
  <div class="flex min-h-[calc(100vh-8rem)] items-center justify-center px-4 py-8">
    <div class="w-full max-w-sm">
      <Card>
        <CardContent class="pt-2 text-center">
          <div class="mb-4 flex items-center justify-center">
            <KidneyGeneticsLogo :size="64" variant="kidneys" :animated="false" />
          </div>
          <h1 class="mb-2 text-2xl font-semibold tracking-tight">Sign in</h1>
          <p class="text-sm text-muted-foreground">
            Sign in to curate genes or manage the database
          </p>
        </CardContent>

        <CardContent>
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
                    autofocus
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            </FormField>

            <FormField v-slot="{ componentField }" name="password">
              <FormItem>
                <div class="flex items-center justify-between">
                  <FormLabel>Password</FormLabel>
                  <RouterLink
                    to="/forgot-password"
                    class="text-sm text-primary underline-offset-4 hover:underline"
                  >
                    Forgot password?
                  </RouterLink>
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

            <Button type="submit" class="w-full" size="lg" :disabled="authStore.isLoading">
              {{ authStore.isLoading ? 'Signing in…' : 'Sign in' }}
            </Button>
          </form>
        </CardContent>

        <CardFooter class="justify-center">
          <RouterLink
            to="/"
            class="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft class="size-4" aria-hidden="true" />
            Back to home
          </RouterLink>
        </CardFooter>
      </Card>

      <p class="mt-6 text-center text-sm text-muted-foreground">
        The database is public. You only need an account to curate data or administer the site.
      </p>
    </div>
  </div>
</template>
