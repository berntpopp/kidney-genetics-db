<template>
  <div :class="PAGE_CONTAINER">
    <PageHeader title="Your profile" description="Your account details and password.">
      <template #breadcrumb>
        <Breadcrumb>
          <BreadcrumbList>
            <BreadcrumbItem>
              <BreadcrumbLink as-child><RouterLink to="/">Home</RouterLink></BreadcrumbLink>
            </BreadcrumbItem>
            <BreadcrumbSeparator />
            <BreadcrumbItem><BreadcrumbPage>Profile</BreadcrumbPage></BreadcrumbItem>
          </BreadcrumbList>
        </Breadcrumb>
      </template>
    </PageHeader>

    <div class="grid grid-cols-1 gap-6 lg:grid-cols-3">
      <div class="space-y-6 lg:col-span-1">
        <Card>
          <CardHeader>
            <CardTitle tag="h2" class="text-base font-semibold">Account</CardTitle>
          </CardHeader>
          <CardContent>
            <!-- Read-only: there is no self-service profile endpoint; admins edit users (#374) -->
            <dl class="grid grid-cols-[auto_1fr] gap-x-4 gap-y-3 text-sm">
              <dt class="text-muted-foreground">Username</dt>
              <dd class="min-w-0 break-words font-medium">{{ authStore.user?.username }}</dd>
              <dt class="text-muted-foreground">Email</dt>
              <dd class="min-w-0 break-all">{{ authStore.user?.email }}</dd>
              <template v-if="fullName">
                <dt class="text-muted-foreground">Full name</dt>
                <dd class="min-w-0 break-words">{{ fullName }}</dd>
              </template>
              <dt class="text-muted-foreground">Role</dt>
              <dd><Chip kind="neutral" :label="roleLabel" /></dd>
              <dt class="text-muted-foreground">Status</dt>
              <dd>
                <StatusBadge :status="authStore.user?.is_active ? 'active' : 'inactive'" />
              </dd>
              <dt class="text-muted-foreground">Member since</dt>
              <dd class="tabular-nums">{{ formatDate(authStore.user?.created_at) }}</dd>
              <dt class="text-muted-foreground">Last sign-in</dt>
              <dd class="tabular-nums">{{ formatDate(lastLogin) }}</dd>
            </dl>
            <p class="mt-4 text-sm text-muted-foreground">
              To change your name or email, ask an administrator.
            </p>
          </CardContent>
        </Card>

        <Card v-if="authStore.isAdmin">
          <CardHeader>
            <CardTitle tag="h2" class="text-base font-semibold">Administration</CardTitle>
          </CardHeader>
          <CardContent class="space-y-1">
            <RouterLink
              to="/admin"
              class="flex items-center gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-muted"
            >
              <ShieldCheck class="size-4 text-muted-foreground" aria-hidden="true" />
              Admin panel
            </RouterLink>
            <RouterLink
              to="/admin/users"
              class="flex items-center gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-muted"
            >
              <Users class="size-4 text-muted-foreground" aria-hidden="true" />
              Manage users
            </RouterLink>
          </CardContent>
        </Card>
      </div>

      <NotificationPrefsCard v-if="authStore.isAuthenticated" class="lg:col-span-3" />

      <Card class="lg:col-span-2">
        <CardHeader>
          <CardTitle tag="h2" class="text-base font-semibold">Change password</CardTitle>
          <CardDescription>You will be signed out and asked to sign in again.</CardDescription>
        </CardHeader>
        <CardContent>
          <form ref="form" class="space-y-4" novalidate @submit.prevent="onSubmit">
            <FormField v-slot="{ componentField }" name="currentPassword">
              <FormItem class="sm:max-w-[calc(50%-0.5rem)]">
                <FormLabel>Current password</FormLabel>
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
            <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <FormField v-slot="{ componentField }" name="newPassword">
                <FormItem>
                  <FormLabel>New password</FormLabel>
                  <FormControl>
                    <PasswordInput
                      v-bind="componentField"
                      autocomplete="new-password"
                      :disabled="authStore.isLoading"
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              </FormField>
              <FormField v-slot="{ componentField }" name="confirmPassword">
                <FormItem>
                  <FormLabel>Repeat new password</FormLabel>
                  <FormControl>
                    <PasswordInput
                      v-bind="componentField"
                      autocomplete="new-password"
                      :disabled="authStore.isLoading"
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              </FormField>
            </div>

            <FormAlert v-if="authStore.error">{{ authStore.error }}</FormAlert>

            <div class="flex justify-end">
              <Button type="submit" :disabled="authStore.isLoading">
                {{ authStore.isLoading ? 'Changing…' : 'Change password' }}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, useTemplateRef } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { z } from 'zod/v3'
import { toTypedSchema } from '@vee-validate/zod'
import { useForm } from 'vee-validate'
import { ShieldCheck, Users } from 'lucide-vue-next'
import { useAuthStore } from '@/stores/auth'
import { Chip, PageHeader, PAGE_CONTAINER, StatusBadge } from '@/components/shared'
import NotificationPrefsCard from '@/components/auth/NotificationPrefsCard.vue'
import FormAlert from '@/components/auth/FormAlert.vue'
import PasswordInput from '@/components/auth/PasswordInput.vue'
import { focusFirstInvalid } from '@/components/auth/focusFirstInvalid'
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator
} from '@/components/ui/breadcrumb'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form'

const authStore = useAuthStore()
const router = useRouter()
const formRef = useTemplateRef('form')

onMounted(() => {
  authStore.clearError()
  if (!authStore.isAuthenticated) {
    router.push('/login?redirect=/profile')
  }
})

// Optional fields the API may send beyond the User type
const extra = computed(
  () => (authStore.user ?? {}) as { full_name?: string | null; last_login?: string | null }
)
const fullName = computed(() => extra.value.full_name || '')
const lastLogin = computed(() => extra.value.last_login)

const ROLE_LABELS: Record<string, string> = {
  admin: 'Administrator',
  curator: 'Curator',
  public: 'Public'
}
const roleLabel = computed(() => ROLE_LABELS[authStore.userRole ?? ''] ?? authStore.userRole ?? '')

const formatDate = (dateString: string | undefined | null) => {
  if (!dateString) return 'Never'
  const date = new Date(dateString)
  return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })
}

const passwordSchema = toTypedSchema(
  z
    .object({
      currentPassword: z.string().min(1, 'Enter your current password'),
      newPassword: z.string().min(8, 'Password must be at least 8 characters'),
      confirmPassword: z.string().min(1, 'Repeat the new password')
    })
    .refine(v => v.newPassword === v.confirmPassword, {
      message: 'Passwords do not match',
      path: ['confirmPassword']
    })
)

const { handleSubmit } = useForm({
  validationSchema: passwordSchema,
  initialValues: { currentPassword: '', newPassword: '', confirmPassword: '' }
})

// On success the store signs out and redirects to /login (#290)
const onSubmit = handleSubmit(
  values => authStore.changePassword(values.currentPassword, values.newPassword),
  () => focusFirstInvalid(formRef.value)
)
</script>
