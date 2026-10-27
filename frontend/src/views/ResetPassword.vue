<script setup lang="ts">
import { ref, useTemplateRef } from 'vue'
import { z } from 'zod/v3'
import { toTypedSchema } from '@vee-validate/zod'
import { useForm } from 'vee-validate'
import { useAuthStore } from '@/stores/auth'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import KidneyGeneticsLogo from '@/components/KidneyGeneticsLogo.vue'
import FormAlert from '@/components/auth/FormAlert.vue'
import PasswordInput from '@/components/auth/PasswordInput.vue'
import { focusFirstInvalid } from '@/components/auth/focusFirstInvalid'
import { Card, CardContent, CardFooter } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form'
import { ArrowLeft } from 'lucide-vue-next'

const authStore = useAuthStore()
const route = useRoute()
const router = useRouter()
const formRef = useTemplateRef('form')

// The emailed link carries the token: /reset-password?token=...
const token = typeof route.query.token === 'string' ? route.query.token : ''

const resetPasswordSchema = toTypedSchema(
  z
    .object({
      password: z.string().min(8, 'Password must be at least 8 characters'),
      confirm: z.string().min(1, 'Repeat the new password')
    })
    .refine(v => v.password === v.confirm, { message: 'Passwords do not match', path: ['confirm'] })
)

const { handleSubmit } = useForm({
  validationSchema: resetPasswordSchema,
  initialValues: { password: '', confirm: '' }
})

const done = ref(false)

const onSubmit = handleSubmit(
  async values => {
    if (await authStore.resetPassword(token, values.password)) {
      done.value = true
      setTimeout(() => router.push('/login'), 3000)
    }
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
          <h1 class="mb-2 text-2xl font-semibold tracking-tight">Choose a new password</h1>
          <p v-if="token" class="text-sm text-muted-foreground">
            The link from your email is valid for one hour.
          </p>
        </CardContent>

        <CardContent>
          <FormAlert v-if="!token">
            This link has no reset token. Request a new link from
            <RouterLink to="/forgot-password">Forgot password</RouterLink>.
          </FormAlert>

          <form v-else ref="form" class="space-y-4" novalidate @submit.prevent="onSubmit">
            <FormField v-slot="{ componentField }" name="password">
              <FormItem>
                <FormLabel>New password</FormLabel>
                <FormControl>
                  <PasswordInput
                    v-bind="componentField"
                    autocomplete="new-password"
                    :disabled="authStore.isLoading || done"
                    autofocus
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            </FormField>

            <FormField v-slot="{ componentField }" name="confirm">
              <FormItem>
                <FormLabel>Repeat new password</FormLabel>
                <FormControl>
                  <PasswordInput
                    v-bind="componentField"
                    autocomplete="new-password"
                    :disabled="authStore.isLoading || done"
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            </FormField>

            <FormAlert v-if="done" tone="success">
              Your password has been changed. Taking you to the sign-in page…
            </FormAlert>

            <FormAlert v-if="authStore.error">
              <p>{{ authStore.error }}</p>
              <RouterLink to="/forgot-password">Request a new link</RouterLink>
            </FormAlert>

            <Button type="submit" class="w-full" size="lg" :disabled="authStore.isLoading || done">
              {{ authStore.isLoading ? 'Saving…' : 'Set new password' }}
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
