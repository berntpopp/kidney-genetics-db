<template>
  <div class="container mx-auto px-4 py-6">
    <!-- Breadcrumb -->
    <Breadcrumb class="mb-2">
      <BreadcrumbList>
        <BreadcrumbItem v-for="(crumb, index) in breadcrumbs" :key="index">
          <BreadcrumbLink v-if="!crumb.disabled && crumb.to" as-child>
            <RouterLink :to="crumb.to">{{ crumb.title }}</RouterLink>
          </BreadcrumbLink>
          <BreadcrumbPage v-else>{{ crumb.title }}</BreadcrumbPage>
          <BreadcrumbSeparator v-if="index < breadcrumbs.length - 1" />
        </BreadcrumbItem>
      </BreadcrumbList>
    </Breadcrumb>

    <!-- Header -->
    <div class="flex items-center gap-3 mb-6">
      <CircleUser class="size-6 text-primary" />
      <div>
        <h1 class="text-2xl font-bold">User Profile</h1>
        <p class="text-sm text-muted-foreground">Manage your account settings</p>
      </div>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
      <!-- Left Column - User Info -->
      <div class="md:col-span-1 space-y-4">
        <Card>
          <CardContent class="pt-6">
            <div class="flex flex-col items-center text-center">
              <Avatar class="h-24 w-24 mb-4">
                <AvatarFallback class="text-2xl bg-primary text-primary-foreground">
                  <User class="size-12" />
                </AvatarFallback>
              </Avatar>

              <h2 class="text-xl font-medium mb-1">{{ authStore.user?.username }}</h2>
              <p class="text-sm text-muted-foreground mb-3">{{ authStore.user?.email }}</p>

              <Badge :variant="roleColor === 'error' ? 'destructive' : 'secondary'" class="mb-4">
                {{ authStore.userRole }}
              </Badge>

              <Separator class="my-4" />

              <div class="w-full text-left space-y-2">
                <div class="flex justify-between text-sm">
                  <span class="text-muted-foreground">Member Since</span>
                  <span>{{ formatDate(authStore.user?.created_at) }}</span>
                </div>
                <div class="flex justify-between text-sm">
                  <span class="text-muted-foreground">Last Login</span>
                  <span>{{ formatDate(authStore.user?.last_login) }}</span>
                </div>
                <div v-if="authStore.user?.is_active" class="flex justify-between text-sm">
                  <span class="text-muted-foreground">Status</span>
                  <Badge
                    variant="secondary"
                    class="bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200"
                  >
                    Active
                  </Badge>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <!-- Quick Actions -->
        <Card v-if="authStore.isAdmin">
          <CardHeader class="pb-2">
            <CardTitle class="text-lg">Admin Actions</CardTitle>
          </CardHeader>
          <CardContent class="space-y-1">
            <RouterLink
              to="/admin"
              class="flex items-center gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-accent"
            >
              <ShieldCheck :size="16" />
              Admin Panel
            </RouterLink>
            <RouterLink
              to="/admin/users"
              class="flex items-center gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-accent"
            >
              <Users :size="16" />
              Manage Users
            </RouterLink>
          </CardContent>
        </Card>
      </div>

      <!-- Right Column - Settings -->
      <div class="md:col-span-2 space-y-4">
        <!-- Account Information -->
        <Card>
          <CardHeader>
            <CardTitle class="flex items-center gap-2">
              <UserCog class="size-5" />
              Account Information
            </CardTitle>
          </CardHeader>
          <CardContent>
            <form @submit.prevent="saveAccount">
              <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                <div class="space-y-2">
                  <Label for="username">Username</Label>
                  <Input
                    id="username"
                    v-model="accountData.username"
                    :disabled="!editingAccount"
                    placeholder="Username"
                  />
                </div>
                <div class="space-y-2">
                  <Label for="email">Email</Label>
                  <Input
                    id="email"
                    v-model="accountData.email"
                    type="email"
                    :disabled="!editingAccount"
                    placeholder="Email"
                  />
                </div>
                <div class="space-y-2 md:col-span-2">
                  <Label for="full_name">Full Name</Label>
                  <Input
                    id="full_name"
                    v-model="accountData.full_name"
                    :disabled="!editingAccount"
                    placeholder="Full Name"
                  />
                </div>
              </div>

              <Alert
                v-if="accountSuccess"
                class="mb-4 border-green-500 bg-green-50 dark:bg-green-950"
              >
                <AlertDescription>{{ accountSuccess }}</AlertDescription>
              </Alert>
              <Alert v-if="accountError" variant="destructive" class="mb-4">
                <AlertDescription>{{ accountError }}</AlertDescription>
              </Alert>

              <div class="flex justify-end gap-2">
                <Button v-if="!editingAccount" variant="outline" @click="startEditAccount">
                  Edit
                </Button>
                <template v-else>
                  <Button variant="ghost" @click="cancelEditAccount">Cancel</Button>
                  <Button type="submit" :disabled="accountLoading">
                    {{ accountLoading ? 'Saving...' : 'Save Changes' }}
                  </Button>
                </template>
              </div>
            </form>
          </CardContent>
        </Card>

        <!-- Change Password -->
        <Card>
          <CardHeader>
            <CardTitle class="flex items-center gap-2">
              <KeyRound class="size-5" />
              Change Password
            </CardTitle>
          </CardHeader>
          <CardContent>
            <form @submit.prevent="changePassword">
              <div class="space-y-4 mb-4">
                <div class="space-y-2">
                  <Label for="current-password">Current Password</Label>
                  <Input
                    id="current-password"
                    v-model="passwordData.currentPassword"
                    type="password"
                    placeholder="Current password"
                  />
                </div>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div class="space-y-2">
                    <Label for="new-password">New Password</Label>
                    <div class="relative">
                      <Input
                        id="new-password"
                        v-model="passwordData.newPassword"
                        :type="showNewPassword ? 'text' : 'password'"
                        placeholder="New password"
                      />
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        class="absolute right-0 top-0 h-full px-3"
                        @click="showNewPassword = !showNewPassword"
                      >
                        <Eye v-if="!showNewPassword" :size="16" />
                        <EyeOff v-else :size="16" />
                      </Button>
                    </div>
                  </div>
                  <div class="space-y-2">
                    <Label for="confirm-password">Confirm New Password</Label>
                    <Input
                      id="confirm-password"
                      v-model="passwordData.confirmPassword"
                      type="password"
                      placeholder="Confirm password"
                    />
                  </div>
                </div>
              </div>

              <Alert
                v-if="passwordSuccess"
                class="mb-4 border-green-500 bg-green-50 dark:bg-green-950"
              >
                <AlertDescription>{{ passwordSuccess }}</AlertDescription>
              </Alert>
              <Alert v-if="passwordError" variant="destructive" class="mb-4">
                <AlertDescription>{{ passwordError }}</AlertDescription>
              </Alert>

              <div class="flex justify-end">
                <Button type="submit" :disabled="passwordLoading">
                  {{ passwordLoading ? 'Changing...' : 'Change Password' }}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>

        <!-- Preferences -->
        <Card>
          <CardHeader>
            <CardTitle class="flex items-center gap-2">
              <Cog class="size-5" />
              Preferences
            </CardTitle>
          </CardHeader>
          <CardContent class="space-y-4">
            <div class="flex items-center justify-between">
              <div>
                <Label>Email Notifications</Label>
                <p class="text-xs text-muted-foreground">Receive email notifications</p>
              </div>
              <Switch v-model:checked="preferences.emailNotifications" />
            </div>
            <div class="flex items-center justify-between">
              <div>
                <Label class="text-muted-foreground">Two-Factor Authentication</Label>
                <p class="text-xs text-muted-foreground">Coming soon</p>
              </div>
              <Switch :checked="preferences.twoFactorAuth" disabled />
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { RouterLink } from 'vue-router'
import {
  CircleUser,
  User,
  UserCog,
  KeyRound,
  Cog,
  Eye,
  EyeOff,
  ShieldCheck,
  Users
} from 'lucide-vue-next'
import { ref, reactive, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator
} from '@/components/ui/breadcrumb'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Alert, AlertDescription } from '@/components/ui/alert'

const authStore = useAuthStore()
const router = useRouter()

const breadcrumbs = [
  { title: 'Home', to: '/', disabled: false },
  { title: 'Profile', disabled: true }
]

onMounted(() => {
  if (!authStore.isAuthenticated) {
    router.push('/login?redirect=/profile')
  }
  if (authStore.user) {
    accountData.username = authStore.user.username || ''
    accountData.email = authStore.user.email || ''
    accountData.full_name = (authStore.user as Record<string, string>).full_name || ''
  }
})

const editingAccount = ref(false)
const accountLoading = ref(false)
const accountSuccess = ref('')
const accountError = ref('')
const accountData = reactive({ username: '', email: '', full_name: '' })

const passwordLoading = ref(false)
const passwordSuccess = ref('')
const passwordError = ref('')
const showNewPassword = ref(false)
const passwordData = reactive({ currentPassword: '', newPassword: '', confirmPassword: '' })

const preferences = reactive({ emailNotifications: true, twoFactorAuth: false })

const roleColor = computed(() => {
  switch (authStore.userRole) {
    case 'admin':
      return 'error'
    case 'curator':
      return 'warning'
    default:
      return 'primary'
  }
})

const formatDate = (dateString: string | undefined | null) => {
  if (!dateString) return 'Never'
  const date = new Date(dateString)
  return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })
}

const startEditAccount = () => {
  accountData.username = authStore.user?.username || ''
  accountData.email = authStore.user?.email || ''
  accountData.full_name = (authStore.user as Record<string, string>)?.full_name || ''
  editingAccount.value = true
  accountSuccess.value = ''
  accountError.value = ''
}

const cancelEditAccount = () => {
  editingAccount.value = false
}

const saveAccount = async () => {
  if (!accountData.username) {
    accountError.value = 'Username is required'
    return
  }
  if (!accountData.email || !accountData.email.includes('@')) {
    accountError.value = 'Valid email is required'
    return
  }

  accountLoading.value = true
  accountError.value = ''
  accountSuccess.value = ''

  try {
    // TODO: Implement API call to update user profile
    await new Promise(resolve => setTimeout(resolve, 1000))

    accountSuccess.value = 'Profile updated successfully!'
    editingAccount.value = false

    authStore.user = { ...authStore.user, ...accountData } as typeof authStore.user
  } catch (error) {
    accountError.value = (error as Error).message || 'Failed to update profile'
  } finally {
    accountLoading.value = false
  }
}

const changePassword = async () => {
  if (!passwordData.currentPassword || !passwordData.newPassword) {
    passwordError.value = 'All password fields are required'
    return
  }
  if (passwordData.newPassword !== passwordData.confirmPassword) {
    passwordError.value = 'Passwords do not match'
    return
  }
  if (passwordData.newPassword.length < 8) {
    passwordError.value = 'Password must be at least 8 characters'
    return
  }

  passwordLoading.value = true
  passwordError.value = ''
  passwordSuccess.value = ''

  const success = await authStore.changePassword(
    passwordData.currentPassword,
    passwordData.newPassword
  )

  if (success) {
    passwordSuccess.value = 'Password changed successfully!'
    passwordData.currentPassword = ''
    passwordData.newPassword = ''
    passwordData.confirmPassword = ''
  } else {
    passwordError.value = authStore.error || 'Failed to change password'
  }

  passwordLoading.value = false
}
</script>
