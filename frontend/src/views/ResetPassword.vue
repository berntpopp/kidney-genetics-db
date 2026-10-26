<script setup lang="ts">
import { ref } from 'vue'
import { z } from 'zod/v3'
import { toTypedSchema } from '@vee-validate/zod'
import { useForm } from 'vee-validate'
import { useAuthStore } from '@/stores/auth'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import KidneyGeneticsLogo from '@/components/KidneyGeneticsLogo.vue'
import { Card, CardContent, CardFooter } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { ArrowLeft } from 'lucide-vue-next'

const authStore = useAuthStore()
const route = useRoute()
const router = useRouter()

// The emailed link carries the token: /reset-password?token=...
const token = typeof route.query.token === 'string' ? route.query.token : ''

const resetPasswordSchema = toTypedSchema(
  z.object({
    password: z.string().min(8, 'Password must be at least 8 characters'),
    confirm: z.string().min(1, 'Please repeat the password')
  })
)

const { handleSubmit, defineField, errors, setFieldError } = useForm({
  validationSchema: resetPasswordSchema
})
const [password, passwordAttrs] = defineField('password', { validateOnBlur: true })
const [confirm, confirmAttrs] = defineField('confirm', { validateOnBlur: true })

const done = ref(false)

const onSubmit = handleSubmit(
  async values => {
    if (values.password !== values.confirm) {
      setFieldError('confirm', 'Passwords do not match')
      document.getElementById('reset-confirm')?.focus()
      return
    }
    if (await authStore.resetPassword(token, values.password)) {
      done.value = true
      setTimeout(() => router.push('/login'), 3000)
    }
  },
  // Move focus to the first invalid field so screen readers announce its error (#327)
  ({ errors: invalid }) =>
    document.getElementById(invalid.password ? 'reset-password' : 'reset-confirm')?.focus()
)
</script>

<template>
  <div class="flex min-h-[calc(100vh-8rem)] items-center justify-center px-4">
    <div class="w-full max-w-sm">
      <Card>
        <CardContent class="pt-8 pb-4 text-center">
          <div class="mb-4 flex items-center justify-center">
            <KidneyGeneticsLogo :size="64" variant="kidneys" :animated="false" />
          </div>
          <h1 class="mb-2 text-2xl font-medium">Choose a New Password</h1>
          <p class="text-sm text-muted-foreground">
            The link from your email is valid for one hour
          </p>
        </CardContent>

        <CardContent class="px-6 pb-2">
          <div
            v-if="!token"
            role="alert"
            class="rounded-md border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive"
          >
            This link has no reset token. Request a new one from
            <RouterLink to="/forgot-password" class="underline">Forgot password</RouterLink>.
          </div>

          <form v-else class="space-y-4" @submit.prevent="onSubmit">
            <div class="space-y-2">
              <Label for="reset-password">New Password</Label>
              <Input
                id="reset-password"
                v-model="password"
                v-bind="passwordAttrs"
                type="password"
                autocomplete="new-password"
                :disabled="authStore.isLoading || done"
                autofocus
                :class="{ 'border-destructive': errors.password }"
                :aria-invalid="!!errors.password"
                :aria-describedby="errors.password ? 'reset-password-error' : undefined"
              />
              <p v-if="errors.password" id="reset-password-error" class="text-sm text-destructive">
                {{ errors.password }}
              </p>
            </div>

            <div class="space-y-2">
              <Label for="reset-confirm">Repeat Password</Label>
              <Input
                id="reset-confirm"
                v-model="confirm"
                v-bind="confirmAttrs"
                type="password"
                autocomplete="new-password"
                :disabled="authStore.isLoading || done"
                :class="{ 'border-destructive': errors.confirm }"
                :aria-invalid="!!errors.confirm"
                :aria-describedby="errors.confirm ? 'reset-confirm-error' : undefined"
              />
              <p v-if="errors.confirm" id="reset-confirm-error" class="text-sm text-destructive">
                {{ errors.confirm }}
              </p>
            </div>

            <div
              v-if="done"
              role="status"
              class="rounded-md border border-green-500/50 bg-green-500/10 p-3 text-sm text-green-700 dark:text-green-400"
            >
              Your password has been changed. Taking you to the login page…
            </div>

            <div
              v-if="authStore.error"
              role="alert"
              class="rounded-md border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive"
            >
              {{ authStore.error }}
            </div>

            <Button type="submit" class="w-full" size="lg" :disabled="authStore.isLoading || done">
              {{ authStore.isLoading ? 'Saving...' : 'Set New Password' }}
            </Button>
          </form>
        </CardContent>

        <CardFooter class="justify-center pb-6 pt-0">
          <RouterLink
            to="/login"
            class="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft class="size-4" />
            Back to Login
          </RouterLink>
        </CardFooter>
      </Card>
    </div>
  </div>
</template>
