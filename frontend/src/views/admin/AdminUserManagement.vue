<template>
  <v-container fluid class="pa-4">
    <AdminHeader
      title="User Management"
      subtitle="Manage user accounts, roles, and permissions"
      back-route="/admin"
    />

    <!-- Actions Bar -->
    <v-row class="mb-4">
      <v-col cols="12" md="6">
        <v-text-field
          v-model="search"
          prepend-inner-icon="mdi-magnify"
          label="Search users by name, email, or username"
          density="compact"
          variant="outlined"
          clearable
          hide-details
        />
      </v-col>
      <v-col cols="12" md="6" class="text-right">
        <v-btn
          color="primary"
          prepend-icon="mdi-account-plus"
          size="small"
          @click="showCreateDialog = true"
        >
          Add User
        </v-btn>
      </v-col>
    </v-row>

    <!-- User Table -->
    <v-card>
      <v-data-table
        :headers="headers"
        :items="filteredUsers"
        :loading="loading"
        :search="search"
        density="compact"
        item-value="id"
        hover
      >
        <!-- Status column -->
        <template #item.is_active="{ item }">
          <v-chip :color="item.is_active ? 'success' : 'error'" size="small" label>
            {{ item.is_active ? 'Active' : 'Inactive' }}
          </v-chip>
        </template>

        <!-- Verified column -->
        <template #item.is_verified="{ item }">
          <v-icon
            :icon="item.is_verified ? 'mdi-check-circle' : 'mdi-close-circle'"
            :color="item.is_verified ? 'success' : 'error'"
            size="small"
          />
        </template>

        <!-- Role column -->
        <template #item.role="{ item }">
          <v-chip :color="getRoleColor(item.role)" size="small" label>
            {{ item.role }}
          </v-chip>
        </template>

        <!-- Last login column -->
        <template #item.last_login="{ item }">
          <span v-if="item.last_login">
            {{ formatDate(item.last_login) }}
          </span>
          <span v-else class="text-medium-emphasis">Never</span>
        </template>

        <!-- Actions column -->
        <template #item.actions="{ item }">
          <v-btn
            icon="mdi-pencil"
            size="x-small"
            variant="text"
            title="Edit user"
            @click="editUser(item)"
          />
          <v-btn
            :icon="item.is_active ? 'mdi-account-off' : 'mdi-account-check'"
            size="x-small"
            variant="text"
            :title="item.is_active ? 'Deactivate user' : 'Activate user'"
            @click="toggleUserStatus(item)"
          />
          <v-btn
            icon="mdi-delete"
            size="x-small"
            variant="text"
            color="error"
            title="Delete user"
            :disabled="item.id === authStore.user?.id"
            @click="confirmDelete(item)"
          />
        </template>
      </v-data-table>
    </v-card>

    <!-- Create/Edit Dialog -->
    <v-dialog v-model="showCreateDialog" max-width="600">
      <v-card>
        <v-card-title>
          {{ editingUser ? 'Edit User' : 'Create New User' }}
        </v-card-title>

        <v-card-text>
          <v-form ref="userForm" v-model="formValid">
            <v-text-field
              v-model="userFormData.username"
              label="Username"
              required
              :rules="[v => !!v || 'Username is required']"
              density="compact"
              variant="outlined"
            />

            <v-text-field
              v-model="userFormData.email"
              label="Email"
              type="email"
              required
              :rules="[
                v => !!v || 'Email is required',
                v => /.+@.+\..+/.test(v) || 'Email must be valid'
              ]"
              density="compact"
              variant="outlined"
            />

            <v-text-field
              v-model="userFormData.full_name"
              label="Full Name"
              density="compact"
              variant="outlined"
            />

            <v-text-field
              v-if="!editingUser"
              v-model="userFormData.password"
              label="Password"
              type="password"
              required
              :rules="[
                v => !!v || 'Password is required',
                v => v.length >= 8 || 'Password must be at least 8 characters'
              ]"
              density="compact"
              variant="outlined"
            />

            <v-select
              v-model="userFormData.role"
              label="Role"
              :items="roles"
              density="compact"
              variant="outlined"
            />

            <v-checkbox v-model="userFormData.is_active" label="Active" density="compact" />

            <v-checkbox
              v-model="userFormData.is_verified"
              label="Email Verified"
              density="compact"
            />
          </v-form>
        </v-card-text>

        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="closeDialog"> Cancel </v-btn>
          <v-btn
            color="primary"
            variant="flat"
            :loading="saving"
            :disabled="!formValid"
            @click="saveUser"
          >
            {{ editingUser ? 'Update' : 'Create' }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Delete Confirmation Dialog -->
    <v-dialog v-model="showDeleteDialog" max-width="400">
      <v-card>
        <v-card-title>Confirm Delete</v-card-title>
        <v-card-text>
          Are you sure you want to delete user "{{ deletingUser?.username }}"? This action cannot be
          undone.
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showDeleteDialog = false">Cancel</v-btn>
          <v-btn color="error" variant="flat" :loading="deleting" @click="deleteUser">
            Delete
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Snackbar for notifications -->
    <v-snackbar v-model="snackbar" :color="snackbarColor" :timeout="3000" location="top">
      {{ snackbarText }}
    </v-snackbar>
  </v-container>
</template>

<script setup>
/**
 * User Management View
 * Full CRUD operations for user accounts with role management
 */

import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import AdminHeader from '@/components/admin/AdminHeader.vue'

const authStore = useAuthStore()

// State
const users = ref([])
const loading = ref(false)
const search = ref('')
const showCreateDialog = ref(false)
const showDeleteDialog = ref(false)
const editingUser = ref(null)
const deletingUser = ref(null)
const saving = ref(false)
const deleting = ref(false)
const formValid = ref(false)
const userForm = ref(null)

// Snackbar state
const snackbar = ref(false)
const snackbarText = ref('')
const snackbarColor = ref('success')

// Form data
const userFormData = ref({
  username: '',
  email: '',
  full_name: '',
  password: '',
  role: 'viewer',
  is_active: true,
  is_verified: false
})

// Table configuration
const headers = [
  { title: 'Username', key: 'username', align: 'start' },
  { title: 'Email', key: 'email' },
  { title: 'Full Name', key: 'full_name' },
  { title: 'Role', key: 'role' },
  { title: 'Status', key: 'is_active' },
  { title: 'Verified', key: 'is_verified', align: 'center' },
  { title: 'Last Login', key: 'last_login' },
  { title: 'Actions', key: 'actions', sortable: false, align: 'center' }
]

const roles = ['admin', 'curator', 'viewer']

// Computed
const filteredUsers = computed(() => {
  if (!search.value) return users.value

  const searchLower = search.value.toLowerCase()
  return users.value.filter(
    user =>
      user.username?.toLowerCase().includes(searchLower) ||
      user.email?.toLowerCase().includes(searchLower) ||
      user.full_name?.toLowerCase().includes(searchLower)
  )
})

// Methods
const loadUsers = async () => {
  loading.value = true
  try {
    const data = await authStore.getAllUsers()
    users.value = data
  } catch (error) {
    window.logService.error('Failed to load users:', error)

    // Check if it's an authentication error
    if (error.response?.status === 401) {
      showSnackbar('Session expired. Please login again.', 'error')
      // Clear auth and redirect to login
      await authStore.logout()
    } else {
      showSnackbar('Failed to load users. Check if backend is running.', 'error')
    }
  } finally {
    loading.value = false
  }
}

const getRoleColor = role => {
  switch (role) {
    case 'admin':
      return 'error'
    case 'curator':
      return 'warning'
    case 'viewer':
      return 'info'
    default:
      return 'grey'
  }
}

const formatDate = dateString => {
  if (!dateString) return 'Never'
  const date = new Date(dateString)
  return date.toLocaleDateString() + ' ' + date.toLocaleTimeString()
}

const editUser = user => {
  editingUser.value = user
  userFormData.value = {
    username: user.username,
    email: user.email,
    full_name: user.full_name || '',
    password: '',
    role: user.role,
    is_active: user.is_active,
    is_verified: user.is_verified
  }
  showCreateDialog.value = true
}

const toggleUserStatus = async user => {
  try {
    const updated = await authStore.updateUser(user.id, {
      is_active: !user.is_active
    })

    // Update local state
    const index = users.value.findIndex(u => u.id === user.id)
    if (index > -1) {
      users.value[index] = updated
    }

    showSnackbar(
      `User ${user.username} ${updated.is_active ? 'activated' : 'deactivated'}`,
      'success'
    )
  } catch (error) {
    window.logService.error('Failed to toggle user status:', error)
    showSnackbar('Failed to update user status', 'error')
  }
}

const confirmDelete = user => {
  deletingUser.value = user
  showDeleteDialog.value = true
}

const deleteUser = async () => {
  if (!deletingUser.value) return

  deleting.value = true
  try {
    await authStore.deleteUser(deletingUser.value.id)

    // Remove from local state
    users.value = users.value.filter(u => u.id !== deletingUser.value.id)

    showSnackbar(`User ${deletingUser.value.username} deleted`, 'success')
    showDeleteDialog.value = false
    deletingUser.value = null
  } catch (error) {
    window.logService.error('Failed to delete user:', error)
    showSnackbar('Failed to delete user', 'error')
  } finally {
    deleting.value = false
  }
}

const saveUser = async () => {
  if (!formValid.value) return

  saving.value = true
  try {
    if (editingUser.value) {
      // Update existing user
      const updates = {
        email: userFormData.value.email,
        full_name: userFormData.value.full_name,
        role: userFormData.value.role,
        is_active: userFormData.value.is_active,
        is_verified: userFormData.value.is_verified
      }

      const updated = await authStore.updateUser(editingUser.value.id, updates)

      // Update local state
      const index = users.value.findIndex(u => u.id === editingUser.value.id)
      if (index > -1) {
        users.value[index] = updated
      }

      showSnackbar('User updated successfully', 'success')
    } else {
      // Create new user
      const newUser = await authStore.registerUser({
        username: userFormData.value.username,
        email: userFormData.value.email,
        full_name: userFormData.value.full_name,
        password: userFormData.value.password,
        role: userFormData.value.role,
        is_active: userFormData.value.is_active,
        is_verified: userFormData.value.is_verified
      })

      users.value.push(newUser)
      showSnackbar('User created successfully', 'success')
    }

    closeDialog()
  } catch (error) {
    window.logService.error('Failed to save user:', error)
    showSnackbar(error.response?.data?.detail || 'Failed to save user', 'error')
  } finally {
    saving.value = false
  }
}

const closeDialog = () => {
  showCreateDialog.value = false
  editingUser.value = null
  userFormData.value = {
    username: '',
    email: '',
    full_name: '',
    password: '',
    role: 'viewer',
    is_active: true,
    is_verified: false
  }
  userForm.value?.reset()
}

const showSnackbar = (text, color = 'success') => {
  snackbarText.value = text
  snackbarColor.value = color
  snackbar.value = true
}

// Lifecycle
onMounted(() => {
  loadUsers()
})
</script>
