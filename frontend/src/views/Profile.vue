<template>
  <v-container>
    <!-- Page Header with Breadcrumbs -->
    <div class="mb-6">
      <!-- Breadcrumbs -->
      <v-breadcrumbs :items="breadcrumbs" density="compact" class="pa-0 mb-2">
        <template #divider>
          <ChevronRight class="size-4" />
        </template>
      </v-breadcrumbs>

      <!-- Header -->
      <div class="d-flex align-center">
        <CircleUser class="size-6 text-primary mr-3" />
        <div class="flex-grow-1">
          <h1 class="text-h4 font-weight-bold">User Profile</h1>
          <p class="text-body-2 text-medium-emphasis ma-0">Manage your account settings</p>
        </div>
      </div>
    </div>

    <v-row>
      <!-- Left Column - User Info -->
      <v-col cols="12" md="4">
        <v-card>
          <v-card-text class="text-center pt-6">
            <!-- Avatar -->
            <v-avatar size="96" color="primary" class="mb-4">
              <User class="size-12" />
            </v-avatar>

            <!-- User Info -->
            <h2 class="text-h5 font-weight-medium mb-1">{{ authStore.user?.username }}</h2>
            <p class="text-body-2 text-medium-emphasis mb-3">{{ authStore.user?.email }}</p>

            <!-- Role Badge -->
            <v-chip :color="roleColor" label class="mb-4">
              {{ authStore.userRole }}
            </v-chip>

            <!-- User Stats -->
            <v-divider class="my-4" />
            <div class="text-left">
              <div class="d-flex justify-space-between mb-2">
                <span class="text-body-2 text-medium-emphasis">Member Since</span>
                <span class="text-body-2">{{ formatDate(authStore.user?.created_at) }}</span>
              </div>
              <div class="d-flex justify-space-between mb-2">
                <span class="text-body-2 text-medium-emphasis">Last Login</span>
                <span class="text-body-2">{{ formatDate(authStore.user?.last_login) }}</span>
              </div>
              <div v-if="authStore.user?.is_active" class="d-flex justify-space-between">
                <span class="text-body-2 text-medium-emphasis">Status</span>
                <v-chip color="success" size="x-small" label>Active</v-chip>
              </div>
            </div>
          </v-card-text>
        </v-card>

        <!-- Quick Actions -->
        <v-card v-if="authStore.isAdmin" class="mt-4">
          <v-card-title class="text-h6">Admin Actions</v-card-title>
          <v-list density="compact">
            <v-list-item :to="'/admin'" prepend-icon="mdi-shield-crown">
              <v-list-item-title>Admin Panel</v-list-item-title>
            </v-list-item>
            <v-list-item :to="'/admin/users'" prepend-icon="mdi-account-group">
              <v-list-item-title>Manage Users</v-list-item-title>
            </v-list-item>
          </v-list>
        </v-card>
      </v-col>

      <!-- Right Column - Settings -->
      <v-col cols="12" md="8">
        <!-- Account Information -->
        <v-card class="mb-4">
          <v-card-title>
            <UserCog class="size-5 mr-2" />
            Account Information
          </v-card-title>
          <v-card-text>
            <v-form ref="accountForm" v-model="accountFormValid">
              <v-row>
                <v-col cols="12" md="6">
                  <v-text-field
                    v-model="accountData.username"
                    label="Username"
                    density="compact"
                    variant="outlined"
                    :disabled="!editingAccount"
                    :rules="editingAccount ? [rules.required] : []"
                  />
                </v-col>
                <v-col cols="12" md="6">
                  <v-text-field
                    v-model="accountData.email"
                    label="Email"
                    density="compact"
                    variant="outlined"
                    :disabled="!editingAccount"
                    :rules="editingAccount ? [rules.required, rules.email] : []"
                  />
                </v-col>
                <v-col cols="12">
                  <v-text-field
                    v-model="accountData.full_name"
                    label="Full Name"
                    density="compact"
                    variant="outlined"
                    :disabled="!editingAccount"
                  />
                </v-col>
              </v-row>

              <v-alert
                v-if="accountSuccess"
                type="success"
                density="compact"
                variant="tonal"
                class="mb-4"
              >
                {{ accountSuccess }}
              </v-alert>

              <v-alert
                v-if="accountError"
                type="error"
                density="compact"
                variant="tonal"
                closable
                class="mb-4"
                @click:close="accountError = ''"
              >
                {{ accountError }}
              </v-alert>

              <div class="d-flex justify-end ga-2">
                <v-btn v-if="!editingAccount" variant="outlined" @click="startEditAccount">
                  Edit
                </v-btn>
                <template v-else>
                  <v-btn variant="text" @click="cancelEditAccount"> Cancel </v-btn>
                  <v-btn
                    color="primary"
                    variant="flat"
                    :loading="accountLoading"
                    :disabled="!accountFormValid"
                    @click="saveAccount"
                  >
                    Save Changes
                  </v-btn>
                </template>
              </div>
            </v-form>
          </v-card-text>
        </v-card>

        <!-- Change Password -->
        <v-card class="mb-4">
          <v-card-title>
            <KeyRound class="size-5 mr-2" />
            Change Password
          </v-card-title>
          <v-card-text>
            <v-form ref="passwordForm" v-model="passwordFormValid">
              <v-row>
                <v-col cols="12">
                  <v-text-field
                    v-model="passwordData.currentPassword"
                    label="Current Password"
                    type="password"
                    density="compact"
                    variant="outlined"
                    :rules="[rules.required]"
                  />
                </v-col>
                <v-col cols="12" md="6">
                  <v-text-field
                    v-model="passwordData.newPassword"
                    label="New Password"
                    :type="showNewPassword ? 'text' : 'password'"
                    density="compact"
                    variant="outlined"
                    :append-inner-icon="showNewPassword ? 'mdi-eye' : 'mdi-eye-off'"
                    :rules="[rules.required, rules.minLength, rules.complexity]"
                    @click:append-inner="showNewPassword = !showNewPassword"
                  />
                </v-col>
                <v-col cols="12" md="6">
                  <v-text-field
                    v-model="passwordData.confirmPassword"
                    label="Confirm New Password"
                    type="password"
                    density="compact"
                    variant="outlined"
                    :rules="[rules.required, rules.passwordMatch]"
                  />
                </v-col>
              </v-row>

              <v-alert
                v-if="passwordSuccess"
                type="success"
                density="compact"
                variant="tonal"
                class="mb-4"
              >
                {{ passwordSuccess }}
              </v-alert>

              <v-alert
                v-if="passwordError"
                type="error"
                density="compact"
                variant="tonal"
                closable
                class="mb-4"
                @click:close="passwordError = ''"
              >
                {{ passwordError }}
              </v-alert>

              <div class="d-flex justify-end">
                <v-btn
                  color="primary"
                  variant="flat"
                  :loading="passwordLoading"
                  :disabled="!passwordFormValid"
                  @click="changePassword"
                >
                  Change Password
                </v-btn>
              </div>
            </v-form>
          </v-card-text>
        </v-card>

        <!-- Preferences -->
        <v-card>
          <v-card-title>
            <Cog class="size-5 mr-2" />
            Preferences
          </v-card-title>
          <v-card-text>
            <v-switch
              v-model="preferences.emailNotifications"
              label="Email Notifications"
              density="compact"
              color="primary"
              hide-details
              class="mb-3"
            />
            <v-switch
              v-model="preferences.twoFactorAuth"
              label="Two-Factor Authentication"
              density="compact"
              color="primary"
              hide-details
              disabled
            />
            <p class="text-caption text-medium-emphasis mt-1">
              Two-factor authentication coming soon
            </p>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { ChevronRight, CircleUser, User, UserCog, KeyRound, Cog } from 'lucide-vue-next'
import { ref, reactive, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'

const authStore = useAuthStore()
const router = useRouter()

// Breadcrumbs
const breadcrumbs = [
  {
    title: 'Home',
    to: '/',
    disabled: false
  },
  {
    title: 'Profile',
    disabled: true
  }
]

// Check authentication
onMounted(() => {
  if (!authStore.isAuthenticated) {
    router.push('/login?redirect=/profile')
  }
})

// Form refs
const accountForm = ref(null)
const passwordForm = ref(null)

// Account data
const editingAccount = ref(false)
const accountFormValid = ref(false)
const accountLoading = ref(false)
const accountSuccess = ref('')
const accountError = ref('')
const accountData = reactive({
  username: '',
  email: '',
  full_name: ''
})

// Password data
const passwordFormValid = ref(false)
const passwordLoading = ref(false)
const passwordSuccess = ref('')
const passwordError = ref('')
const showNewPassword = ref(false)
const passwordData = reactive({
  currentPassword: '',
  newPassword: '',
  confirmPassword: ''
})

// Preferences
const preferences = reactive({
  emailNotifications: true,
  twoFactorAuth: false
})

// Computed
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

// Validation rules
const rules = {
  required: value => !!value || 'Required',
  email: value => {
    const pattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    return pattern.test(value) || 'Invalid email address'
  },
  minLength: value => value.length >= 8 || 'Minimum 8 characters',
  complexity: value => {
    const hasUpper = /[A-Z]/.test(value)
    const hasLower = /[a-z]/.test(value)
    const hasNumber = /[0-9]/.test(value)
    const hasSpecial = /[!@#$%^&*(),.?":{}|<>]/.test(value)

    return (
      (hasUpper && hasLower && hasNumber && hasSpecial) ||
      'Password must contain uppercase, lowercase, number, and special character'
    )
  },
  passwordMatch: value => value === passwordData.newPassword || 'Passwords must match'
}

// Methods
const formatDate = dateString => {
  if (!dateString) return 'Never'
  const date = new Date(dateString)
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  })
}

const startEditAccount = () => {
  accountData.username = authStore.user?.username || ''
  accountData.email = authStore.user?.email || ''
  accountData.full_name = authStore.user?.full_name || ''
  editingAccount.value = true
  accountSuccess.value = ''
  accountError.value = ''
}

const cancelEditAccount = () => {
  editingAccount.value = false
  accountForm.value?.reset()
}

const saveAccount = async () => {
  if (!accountFormValid.value) return

  accountLoading.value = true
  accountError.value = ''
  accountSuccess.value = ''

  try {
    // TODO: Implement API call to update user profile
    // await authStore.updateProfile(accountData)

    // Simulated success
    await new Promise(resolve => setTimeout(resolve, 1000))

    accountSuccess.value = 'Profile updated successfully!'
    editingAccount.value = false

    // Update local user data
    authStore.user = {
      ...authStore.user,
      ...accountData
    }
  } catch (error) {
    accountError.value = error.message || 'Failed to update profile'
  } finally {
    accountLoading.value = false
  }
}

const changePassword = async () => {
  if (!passwordFormValid.value) return

  passwordLoading.value = true
  passwordError.value = ''
  passwordSuccess.value = ''

  const success = await authStore.changePassword(
    passwordData.currentPassword,
    passwordData.newPassword
  )

  if (success) {
    passwordSuccess.value = 'Password changed successfully!'
    passwordForm.value?.reset()
    passwordData.currentPassword = ''
    passwordData.newPassword = ''
    passwordData.confirmPassword = ''
  } else {
    passwordError.value = authStore.error || 'Failed to change password'
  }

  passwordLoading.value = false
}

// Initialize account data
onMounted(() => {
  if (authStore.user) {
    accountData.username = authStore.user.username || ''
    accountData.email = authStore.user.email || ''
    accountData.full_name = authStore.user.full_name || ''
  }
})
</script>
