<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuItem
} from '@/components/ui/dropdown-menu'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { CircleUser, ShieldEllipsis, LogOut, ChevronDown } from 'lucide-vue-next'

const authStore = useAuthStore()
const router = useRouter()

const userInitials = computed(() => authStore.user?.username?.charAt(0).toUpperCase() ?? 'U')

const roleBadgeVariant = computed<'destructive' | 'secondary' | 'default'>(() => {
  switch (authStore.userRole) {
    case 'admin':
      return 'destructive'
    case 'curator':
      return 'secondary'
    default:
      return 'default'
  }
})

const goToProfile = () => {
  router.push('/profile')
}

const goToAdminPanel = () => {
  router.push('/admin')
}

const handleLogout = async () => {
  await authStore.logout()
}
</script>

<template>
  <DropdownMenu>
    <DropdownMenuTrigger as-child>
      <Button variant="ghost" class="flex items-center gap-2">
        <Avatar class="size-8">
          <AvatarFallback>{{ userInitials }}</AvatarFallback>
        </Avatar>
        <span class="hidden sm:inline text-sm font-medium">{{ authStore.user?.username }}</span>
        <ChevronDown class="size-4 text-muted-foreground" />
      </Button>
    </DropdownMenuTrigger>
    <DropdownMenuContent align="end" class="w-56">
      <DropdownMenuLabel class="font-normal">
        <div class="flex flex-col space-y-1">
          <p class="text-sm font-medium leading-none">{{ authStore.user?.username }}</p>
          <p class="text-xs leading-none text-muted-foreground">{{ authStore.user?.email }}</p>
        </div>
      </DropdownMenuLabel>
      <div class="px-2 py-1">
        <Badge :variant="roleBadgeVariant" class="text-xs">{{ authStore.userRole }}</Badge>
      </div>
      <DropdownMenuSeparator />
      <DropdownMenuItem @click="goToProfile">
        <CircleUser class="mr-2 size-4" />
        My Profile
      </DropdownMenuItem>
      <DropdownMenuItem v-if="authStore.isAdmin" @click="goToAdminPanel">
        <ShieldEllipsis class="mr-2 size-4" />
        Admin Panel
      </DropdownMenuItem>
      <DropdownMenuSeparator />
      <DropdownMenuItem @click="handleLogout">
        <LogOut class="mr-2 size-4" />
        Logout
      </DropdownMenuItem>
    </DropdownMenuContent>
  </DropdownMenu>
</template>
