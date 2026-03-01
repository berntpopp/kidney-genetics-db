<script setup>
/**
 * User Management View
 * Full CRUD operations for user accounts with role management
 */

import { ref, computed, onMounted, h } from 'vue'
import { useVueTable, getCoreRowModel, getSortedRowModel } from '@tanstack/vue-table'
import { useAuthStore } from '@/stores/auth'
import AdminHeader from '@/components/admin/AdminHeader.vue'
import { ADMIN_BREADCRUMBS } from '@/utils/adminBreadcrumbs'
import { toast } from 'vue-sonner'
import {
  CircleCheck,
  CircleX,
  Pencil,
  UserX,
  UserCheck,
  Trash2,
  UserPlus,
  Search,
  Loader2
} from 'lucide-vue-next'
import { DataTable } from '@/components/ui/data-table'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
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

// Role color helpers
const getRoleVariant = role => {
  switch (role) {
    case 'admin':
      return 'destructive'
    case 'curator':
      return 'default'
    case 'viewer':
      return 'secondary'
    default:
      return 'outline'
  }
}

const formatDate = dateString => {
  if (!dateString) return 'Never'
  const date = new Date(dateString)
  return date.toLocaleDateString() + ' ' + date.toLocaleTimeString()
}

// Column definitions for TanStack Table
const columns = [
  {
    accessorKey: 'username',
    header: 'Username',
    cell: ({ row }) => h('span', { class: 'font-medium' }, row.getValue('username'))
  },
  {
    accessorKey: 'email',
    header: 'Email'
  },
  {
    accessorKey: 'full_name',
    header: 'Full Name',
    cell: ({ row }) => h('span', null, row.getValue('full_name') || '-')
  },
  {
    accessorKey: 'role',
    header: 'Role',
    cell: ({ row }) =>
      h(Badge, { variant: getRoleVariant(row.getValue('role')) }, () => row.getValue('role'))
  },
  {
    accessorKey: 'is_active',
    header: 'Status',
    cell: ({ row }) =>
      h(Badge, { variant: row.getValue('is_active') ? 'default' : 'secondary' }, () =>
        row.getValue('is_active') ? 'Active' : 'Inactive'
      )
  },
  {
    accessorKey: 'is_verified',
    header: 'Verified',
    cell: ({ row }) =>
      h(row.getValue('is_verified') ? CircleCheck : CircleX, {
        class: `size-4 ${row.getValue('is_verified') ? 'text-green-600 dark:text-green-400' : 'text-destructive'}`
      }),
    size: 80
  },
  {
    accessorKey: 'last_login',
    header: 'Last Login',
    cell: ({ row }) => {
      const val = row.getValue('last_login')
      return h(
        'span',
        { class: val ? '' : 'text-muted-foreground' },
        val ? formatDate(val) : 'Never'
      )
    }
  },
  {
    id: 'actions',
    header: '',
    cell: ({ row }) => {
      const user = row.original
      return h('div', { class: 'flex items-center gap-1' }, [
        h(Tooltip, null, {
          default: () => [
            h(TooltipTrigger, { asChild: true }, () =>
              h(
                Button,
                {
                  variant: 'ghost',
                  size: 'icon',
                  class: 'h-8 w-8',
                  onClick: () => editUser(user)
                },
                () => h(Pencil, { class: 'size-4' })
              )
            ),
            h(TooltipContent, null, () => 'Edit user')
          ]
        }),
        h(Tooltip, null, {
          default: () => [
            h(TooltipTrigger, { asChild: true }, () =>
              h(
                Button,
                {
                  variant: 'ghost',
                  size: 'icon',
                  class: 'h-8 w-8',
                  onClick: () => toggleUserStatus(user)
                },
                () =>
                  h(user.is_active ? UserX : UserCheck, {
                    class: 'size-4'
                  })
              )
            ),
            h(TooltipContent, null, () => `${user.is_active ? 'Deactivate' : 'Activate'} user`)
          ]
        }),
        h(Tooltip, null, {
          default: () => [
            h(TooltipTrigger, { asChild: true }, () =>
              h(
                Button,
                {
                  variant: 'ghost',
                  size: 'icon',
                  class: 'h-8 w-8 text-destructive',
                  disabled: user.id === authStore.user?.id,
                  onClick: () => confirmDelete(user)
                },
                () => h(Trash2, { class: 'size-4' })
              )
            ),
            h(TooltipContent, null, () => 'Delete user')
          ]
        })
      ])
    },
    enableSorting: false,
    size: 120
  }
]

// TanStack Table
const table = useVueTable({
  get data() {
    return filteredUsers.value
  },
  columns,
  getCoreRowModel: getCoreRowModel(),
  getSortedRowModel: getSortedRowModel()
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
      toast.error('Session expired. Please login again.', { duration: Infinity })
      // Clear auth and redirect to login
      await authStore.logout()
    } else {
      toast.error('Failed to load users. Check if backend is running.', { duration: Infinity })
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
  <div class="container mx-auto px-4 py-6">
    <AdminHeader
      title="User Management"
      subtitle="Manage user accounts, roles, and permissions"
      icon="mdi-account-group"
      icon-color="primary"
      :breadcrumbs="ADMIN_BREADCRUMBS.users"
    />

    <!-- Actions Bar -->
    <div class="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 mb-4">
      <div class="relative w-full md:w-1/2">
        <Search :size="16" class="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
        <Input
          v-model="search"
          placeholder="Search users by name, email, or username"
          class="pl-9"
        />
      </div>
      <Button size="sm" @click="showCreateDialog = true">
        <UserPlus class="size-4 mr-2" />
        Add User
      </Button>
    </div>

    <!-- User Table -->
    <Card>
      <CardContent class="p-0">
        <div v-if="loading" class="flex items-center justify-center py-12">
          <Loader2 class="size-6 animate-spin text-muted-foreground" />
          <span class="ml-2 text-sm text-muted-foreground">Loading users...</span>
        </div>
        <DataTable v-else :table="table" />
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
            <Select v-model="userFormData.role">
              <SelectTrigger>
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
                :checked="userFormData.is_active"
                @update:checked="val => (userFormData.is_active = val)"
              />
              <Label for="is_active" class="cursor-pointer">Active</Label>
            </div>
            <div class="flex items-center gap-2">
              <Checkbox
                id="is_verified"
                :checked="userFormData.is_verified"
                @update:checked="val => (userFormData.is_verified = val)"
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
            class="bg-destructive text-destructive-foreground hover:bg-destructive/90"
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
