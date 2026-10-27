<script setup lang="ts">
import { ref, useTemplateRef } from 'vue'
import { z } from 'zod/v3'
import { toTypedSchema } from '@vee-validate/zod'
import { useForm } from 'vee-validate'
import { useAuthStore } from '@/stores/auth'
import { RouterLink } from 'vue-router'
import KidneyGeneticsLogo from '@/components/KidneyGeneticsLogo.vue'
import FormAlert from '@/components/auth/FormAlert.vue'
import { focusFirstInvalid } from '@/components/auth/focusFirstInvalid'
import { Card, CardContent, CardFooter } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form'
import { ArrowLeft } from 'lucide-vue-next'

const authStore = useAuthStore()
const formRef = useTemplateRef('form')

// Same Zod schema as ForgotPasswordModal
const forgotPasswordSchema = toTypedSchema(
  z.object({
    email: z.string().min(1, 'Email is required').email('Enter a valid email address')
  })
)

const { handleSubmit } = useForm({
  validationSchema: forgotPasswordSchema,
  initialValues: { email: '' }
})

const submitted = ref(false)

const onSubmit = handleSubmit(
  async values => {
    // A server without email (SMTP) answers 503 with "ask an administrator"; shown as the error
    submitted.value = await authStore.requestPasswordReset(values.email)
  },
  () => focusFirstInvalid(formRef.value)
)
</script>

<template>
  <div class="flex min-h-[calc(100vh-8rem)] items-center justify-center px-4 py-8">
    <div class="w-full max-w-sm">
      <Card>
        <CardContent class="pt-2 text-center">
          <div class="mb-4 flex items-center justify-center">
            <KidneyGeneticsLogo :size="64" variant="kidneys" :animated="false" />
          </div>
          <h1 class="mb-2 text-2xl font-semibold tracking-tight">Forgot your password?</h1>
          <p class="text-sm text-muted-foreground">
            Enter your account email. Where reset by email is available, we send you a link;
            otherwise an administrator can reset your password.
          </p>
        </CardContent>

        <CardContent>
          <form ref="form" class="space-y-4" novalidate @submit.prevent="onSubmit">
            <FormField v-slot="{ componentField }" name="email">
              <FormItem>
                <FormLabel>Email</FormLabel>
                <FormControl>
                  <Input
                    v-bind="componentField"
                    type="email"
                    autocomplete="email"
                    :disabled="authStore.isLoading || submitted"
                    autofocus
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            </FormField>

            <FormAlert v-if="submitted" tone="success">
              If an account uses this address, a reset link is on its way. It is valid for one hour.
            </FormAlert>

            <FormAlert v-if="authStore.error">{{ authStore.error }}</FormAlert>

            <Button
              type="submit"
              class="w-full"
              size="lg"
              :disabled="authStore.isLoading || submitted"
            >
              {{ authStore.isLoading ? 'Sending…' : 'Send reset link' }}
            </Button>
          </form>
        </CardContent>

        <CardFooter class="justify-center">
          <RouterLink
            to="/login"
            class="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft class="size-4" aria-hidden="true" />
            Back to sign in
          </RouterLink>
        </CardFooter>
      </Card>
    </div>
  </div>
</template>
