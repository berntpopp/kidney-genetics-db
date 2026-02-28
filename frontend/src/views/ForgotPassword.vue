<script setup lang="ts">
import { ref } from 'vue'
import { z } from 'zod'
import { toTypedSchema } from '@vee-validate/zod'
import { useForm } from 'vee-validate'
import { useAuthStore } from '@/stores/auth'
import { useRouter, RouterLink } from 'vue-router'
import KidneyGeneticsLogo from '@/components/KidneyGeneticsLogo.vue'
import { Card, CardContent, CardFooter } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { ArrowLeft } from 'lucide-vue-next'

const authStore = useAuthStore()
const router = useRouter()

// Same Zod schema as ForgotPasswordModal
const forgotPasswordSchema = toTypedSchema(
  z.object({
    email: z.string().min(1, 'Email is required').email('Invalid email address')
  })
)

const { handleSubmit, defineField, errors } = useForm({
  validationSchema: forgotPasswordSchema
})

const [email, emailAttrs] = defineField('email', {
  validateOnBlur: true,
  validateOnInput: true
})

const submitted = ref(false)

const onSubmit = handleSubmit(async values => {
  const success = await authStore.requestPasswordReset(values.email)

  if (success) {
    submitted.value = true
    setTimeout(() => {
      router.push('/login')
    }, 3000)
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
          <h1 class="mb-2 text-2xl font-medium">Reset Password</h1>
          <p class="text-sm text-muted-foreground">
            Enter your email address and we'll send you instructions to reset your password
          </p>
        </CardContent>

        <!-- Reset Form -->
        <CardContent class="px-6 pb-2">
          <form class="space-y-4" @submit.prevent="onSubmit">
            <div class="space-y-2">
              <Label for="page-forgot-email">Email Address</Label>
              <Input
                id="page-forgot-email"
                v-model="email"
                v-bind="emailAttrs"
                type="email"
                placeholder="Enter your email"
                :disabled="authStore.isLoading || submitted"
                autofocus
                :class="{ 'border-destructive': errors.email }"
              />
              <p v-if="errors.email" class="text-sm text-destructive">
                {{ errors.email }}
              </p>
            </div>

            <div
              v-if="submitted"
              class="rounded-md border border-green-500/50 bg-green-500/10 p-3 text-sm text-green-700 dark:text-green-400"
            >
              Password reset instructions have been sent to your email.
            </div>

            <div
              v-if="authStore.error"
              class="rounded-md border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive"
            >
              {{ authStore.error }}
            </div>

            <Button
              type="submit"
              class="w-full"
              size="lg"
              :disabled="authStore.isLoading || submitted"
            >
              <span v-if="authStore.isLoading" class="flex items-center gap-2">
                <span
                  class="size-4 animate-spin rounded-full border-2 border-current border-t-transparent"
                />
                Sending...
              </span>
              <span v-else>Send Reset Email</span>
            </Button>
          </form>
        </CardContent>

        <!-- Footer -->
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
