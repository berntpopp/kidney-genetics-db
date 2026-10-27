<script setup>
/**
 * User Management View
 * Full CRUD operations for user accounts with role management
 */

import { ref, computed, onMounted, h } from 'vue'
import { useTable } from '@tanstack/vue-table'
import { useAuthStore } from '@/stores/auth'
import AdminHeader from '@/components/admin/AdminHeader.vue'
import { Chip, DataState, PAGE_CONTAINER, StatusBadge } from '@/components/shared'
import { toast } from 'vue-sonner'
import {
  CircleCheck,
  CircleMinus,
  Loader2,
  Pencil,
  Search,
  Trash2,
  UserCheck,
  UserPlus,
  UserX,
  ShieldCheck,
  PenLine,
  Eye
} from 'lucide-vue-next'
import { DataTable, dataTableFeatures } from '@/components/ui/data-table'
import { Card, CardContent } from '@/components/ui/card'
import { Button, buttonVariants } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '@/components/ui/dialog'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle
} from '@/components/ui/alert-dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@/components/ui/select'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'

const authStore = useAuthStore()

// State
const users = ref([])
const loading = ref(false)
const search = ref('')
const showCreateDialog = ref(false)
const showDeleteDialog = ref(false)
const editingUser = ref(null)
const deletingUser = ref(null)
const deactivatingUser = ref(null)
const showDeactivateDialog = ref(false)
// Own account: no self-deactivation or self-demotion from the UI
const isEditingSelf = computed(
  () => !!editingUser.value && editingUser.value.id === authStore.user?.id
)
const saving = ref(false)
const deleting = ref(false)
const formValid = computed(() => {
  const d = userFormData.value
  if (!d.username || !d.email) return false
  if (!/.+@.+\..+/.test(d.email)) return false
  if (!editingUser.value && (!d.password || d.password.length < 8)) return false
  return true
})

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

// Roles are permissions, not statuses: neutral chips with an icon and an explanation
const ROLE_INFO = {
  admin: { icon: ShieldCheck, tip: 'Admin: full access, including users, pipelines and backups' },
  curator: { icon: PenLine, tip: 'Curator: can curate genes and review staging' },
  viewer: { icon: Eye, tip: 'Viewer: read-only access' }
}
const loadError = ref(null)

const formatDate = dateString => {
  if (!dateString) return 'Never'
  const date = new Date(dateString)
  return date.toLocaleDateString() + ' ' + date.toLocaleTimeString()
}

// Column definitions for TanStack Table
const iconButton = (label, icon, onClick, opts = {}) =>
  h(Tooltip, null, {
    default: () => [
      h(TooltipTrigger, { asChild: true }, () =>
        h(
          Button,
          {
            variant: 'ghost',
            size: 'icon-sm',
            'aria-label': label,
            class: opts.danger ? 'text-danger hover:text-danger' : '',
            disabled: opts.disabled,
            onClick
          },
          () => h(icon, { class: 'size-4', 'aria-hidden': 'true' })
        )
      ),
      h(TooltipContent, null, () => label)
    ]
  })

const columns = [
  {
    accessorKey: 'username',
    header: 'Username',
    cell: ({ row }) => h('span', { class: 'font-medium' }, row.getValue('username'))
  },
  {
    accessorKey: 'role',
    header: 'Role',
    cell: ({ row }) => {
      const role = row.getValue('role')
      const info = ROLE_INFO[role]
      return h(Chip, { kind: 'neutral', label: role, icon: info?.icon, tooltip: info?.tip })
    }
  },
  {
    accessorKey: 'is_active',
    header: 'Status',
    cell: ({ row }) => h(StatusBadge, { status: row.getValue('is_active') ? 'active' : 'inactive' })
  },
  {
    accessorKey: 'email',
    header: 'Email'
  },
  {
    accessorKey: 'full_name',
    header: 'Full Name',
    cell: ({ row }) =>
      h(
        'span',
        { class: row.getValue('full_name') ? '' : 'text-muted-foreground' },
        row.getValue('full_name') || '—'
      )
  },
  {
    accessorKey: 'is_verified',
    header: 'Verified',
    cell: ({ row }) => {
      const ok = row.getValue('is_verified')
      return h(
        'span',
        {
          class:
            'inline-flex items-center gap-1 text-sm ' +
            (ok ? 'text-success' : 'text-muted-foreground')
        },
        [
          h(ok ? CircleCheck : CircleMinus, { class: 'size-4', 'aria-hidden': 'true' }),
          ok ? 'Yes' : 'No'
        ]
      )
    },
    size: 90
  },
  {
    accessorKey: 'last_login',
    header: 'Last Login',
    cell: ({ row }) => {
      const val = row.getValue('last_login')
      return h(
        'span',
        { class: 'tabular-nums ' + (val ? '' : 'text-muted-foreground') },
        val ? formatDate(val) : 'Never'
      )
    }
  },
  {
    id: 'actions',
    header: () => h('span', { class: 'sr-only' }, 'Actions'),
    cell: ({ row }) => {
      const user = row.original
      const self = user.id === authStore.user?.id
      return h('div', { class: 'flex items-center justify-end gap-1' }, [
        iconButton(`Edit ${user.username}`, Pencil, () => editUser(user)),
        iconButton(
          `${user.is_active ? 'Deactivate' : 'Activate'} ${user.username}`,
          user.is_active ? UserX : UserCheck,
          () => requestToggleUserStatus(user),
          { disabled: self }
        ),
        iconButton(`Delete ${user.username}`, Trash2, () => confirmDelete(user), {
          disabled: self,
          danger: true
        })
      ])
    },
    enableSorting: false,
    size: 120
  }
]

// TanStack Table
const table = useTable({
  features: dataTableFeatures,
  manualPagination: true, // unpaged: render every row
  get data() {
    return filteredUsers.value
  },
  columns
})

// Methods
const loadUsers = async () => {
  loading.value = true
  loadError.value = null
  try {
    const data = await authStore.getAllUsers()
    users.value = data
  } catch (error) {
    window.logService.error('Failed to load users:', error)
    loadError.value = error.response?.data?.detail || error.message || 'Request failed'

    // Check if it's an authentication error
    if (error.response?.status === 401) {
      toast.error('Session expired. Please login again.', { duration: Infinity })
      // Clear auth and redirect to login
      await authStore.logout()
    }
  } finally {
    loading.value = false
  }
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

// Deactivation locks the user out, so it is confirmed; activation is not
const requestToggleUserStatus = user => {
  if (user.is_active) {
    deactivatingUser.value = user
    showDeactivateDialog.value = true
  } else {
    toggleUserStatus(user)
  }
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

    toast.success(`User ${user.username} ${updated.is_active ? 'activated' : 'deactivated'}`, {
      duration: 5000
    })
  } catch (error) {
    window.logService.error('Failed to toggle user status:', error)
    toast.error('Failed to update user status', { duration: Infinity })
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

    toast.success(`User ${deletingUser.value.username} deleted`, { duration: 5000 })
    showDeleteDialog.value = false
    deletingUser.value = null
  } catch (error) {
    window.logService.error('Failed to delete user:', error)
    toast.error('Failed to delete user', { duration: Infinity })
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

      toast.success('User updated successfully', { duration: 5000 })
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
      toast.success('User created successfully', { duration: 5000 })
    }

    closeDialog()
  } catch (error) {
    window.logService.error('Failed to save user:', error)
    toast.error(error.response?.data?.detail || 'Failed to save user', { duration: Infinity })
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
}

// Lifecycle
onMounted(() => {
  loadUsers()
})
</script>

<template>
  <div :class="PAGE_CONTAINER">
    <AdminHeader title="User Management" subtitle="Manage user accounts, roles, and permissions" />

    <!-- Actions Bar -->
    <div class="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 mb-4">
      <div class="relative w-full md:w-1/2">
        <Search
          class="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
          aria-hidden="true"
        />
        <Input
          v-model="search"
          aria-label="Search users"
          placeholder="Search users by name, email, or username"
          class="pl-9"
        />
      </div>
      <Button size="sm" @click="showCreateDialog = true">
        <UserPlus class="size-4" aria-hidden="true" />
        Add User
      </Button>
    </div>

    <!-- User Table -->
    <Card>
      <CardContent class="p-0">
        <DataState
          :loading="loading && !users.length"
          :error="loadError"
          error-title="Could not load users"
          :empty="!filteredUsers.length"
          :empty-message="search ? 'No users match this search.' : 'No users yet.'"
          class="m-4"
          @retry="loadUsers"
        >
          <template #loading>
            <div class="space-y-3 p-4" aria-hidden="true">
              <div
                v-for="i in 4"
                :key="i"
                class="h-8 rounded-md bg-muted motion-safe:animate-pulse"
              />
            </div>
          </template>
          <DataTable :table="table" />
        </DataState>
      </CardContent>
    </Card>

    <!-- Create/Edit Dialog -->
    <Dialog v-model:open="showCreateDialog">
      <DialogContent class="max-w-[500px]">
        <DialogHeader>
          <DialogTitle>{{ editingUser ? 'Edit User' : 'Create New User' }}</DialogTitle>
          <DialogDescription>
            {{
              editingUser ? 'Update user details below.' : 'Fill in the details for the new user.'
            }}
          </DialogDescription>
        </DialogHeader>

        <div class="space-y-4">
          <div class="space-y-2">
            <Label for="username">Username</Label>
            <Input
              id="username"
              v-model="userFormData.username"
              :disabled="!!editingUser"
              placeholder="Enter username"
            />
          </div>

          <div class="space-y-2">
            <Label for="email">Email</Label>
            <Input
              id="email"
              v-model="userFormData.email"
              type="email"
              placeholder="user@example.com"
            />
          </div>

          <div class="space-y-2">
            <Label for="full_name">Full Name</Label>
            <Input id="full_name" v-model="userFormData.full_name" placeholder="Enter full name" />
          </div>

          <div v-if="!editingUser" class="space-y-2">
            <Label for="password">Password</Label>
            <Input
              id="password"
              v-model="userFormData.password"
              type="password"
              placeholder="Minimum 8 characters"
            />
          </div>

          <div class="space-y-2">
            <Label for="role">Role</Label>
            <Select v-model="userFormData.role" :disabled="isEditingSelf">
              <SelectTrigger id="role">
                <SelectValue placeholder="Select a role" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem v-for="role in roles" :key="role" :value="role">
                  {{ role }}
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div class="flex items-center gap-6">
            <div class="flex items-center gap-2">
              <Checkbox
                id="is_active"
                :disabled="isEditingSelf"
                :model-value="userFormData.is_active"
                @update:model-value="val => (userFormData.is_active = val)"
              />
              <Label for="is_active" class="cursor-pointer">Active</Label>
            </div>
            <div class="flex items-center gap-2">
              <Checkbox
                id="is_verified"
                :model-value="userFormData.is_verified"
                @update:model-value="val => (userFormData.is_verified = val)"
              />
              <Label for="is_verified" class="cursor-pointer">Email Verified</Label>
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" @click="closeDialog">Cancel</Button>
          <Button :disabled="!formValid || saving" @click="saveUser">
            <Loader2 v-if="saving" class="size-4 mr-2 animate-spin" />
            {{ editingUser ? 'Update' : 'Create' }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <!-- Deactivate Confirmation Dialog -->
    <AlertDialog v-model:open="showDeactivateDialog">
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Deactivate user?</AlertDialogTitle>
          <AlertDialogDescription>
            "{{ deactivatingUser?.username }}" will no longer be able to sign in until the account
            is activated again.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction
            :class="buttonVariants({ variant: 'destructive' })"
            @click="toggleUserStatus(deactivatingUser)"
          >
            Deactivate
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>

    <!-- Delete Confirmation Dialog -->
    <AlertDialog v-model:open="showDeleteDialog">
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Confirm Delete</AlertDialogTitle>
          <AlertDialogDescription>
            Are you sure you want to delete user "{{ deletingUser?.username }}"? This action cannot
            be undone.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel @click="showDeleteDialog = false">Cancel</AlertDialogCancel>
          <AlertDialogAction
            :class="buttonVariants({ variant: 'destructive' })"
            :disabled="deleting"
            @click="deleteUser"
          >
            <Loader2 v-if="deleting" class="size-4 mr-2 animate-spin" />
            Delete
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  </div>
</template>
