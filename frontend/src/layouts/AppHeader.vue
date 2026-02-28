<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { KGDBLogo } from '@/components/branding'
import UserMenu from '@/components/auth/UserMenu.vue'
import { Button } from '@/components/ui/button'
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { Separator } from '@/components/ui/separator'
import { useAuthStore } from '@/stores/auth'
import { useAppTheme } from '@/composables/useAppTheme'
import {
  Menu,
  Sun,
  Moon,
  LogIn,
  Dna,
  LayoutDashboard,
  Network,
  RefreshCw,
  Info,
  CircleUser,
  ShieldEllipsis,
  LogOut
} from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const { isDark, toggleTheme } = useAppTheme()

const drawerOpen = ref(false)

const navLinks = [
  { to: '/genes', label: 'Gene Browser', icon: Dna },
  { to: '/dashboard', label: 'Data Overview', icon: LayoutDashboard },
  { to: '/network-analysis', label: 'Network Analysis', icon: Network },
  { to: '/data-sources', label: 'Data Sources', icon: RefreshCw },
  { to: '/about', label: 'About', icon: Info }
]

const isActive = (path: string) => {
  if (path === '/genes') return route.path.startsWith('/genes')
  return route.path === path
}

const handleLogout = async () => {
  drawerOpen.value = false
  await authStore.logout()
}

const navigateMobile = (to: string) => {
  drawerOpen.value = false
  router.push(to)
}
</script>

<template>
  <header
    class="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60"
  >
    <div class="container mx-auto flex h-14 items-center px-4">
      <!-- Logo -->
      <div class="mr-6 flex items-center">
        <RouterLink to="/" class="flex items-center">
          <KGDBLogo
            :size="32"
            variant="with-text"
            text-layout="horizontal"
            :animated="false"
            :interactive="false"
          />
        </RouterLink>
      </div>

      <!-- Desktop Nav Links -->
      <nav class="hidden md:flex items-center gap-1 flex-1">
        <RouterLink
          v-for="link in navLinks"
          :key="link.to"
          :to="link.to"
          class="inline-flex items-center px-3 py-2 text-sm font-medium transition-colors hover:text-primary"
          :class="{
            'text-primary border-b-2 border-primary': isActive(link.to),
            'text-muted-foreground': !isActive(link.to)
          }"
        >
          {{ link.label }}
        </RouterLink>
      </nav>

      <!-- Desktop Right Area -->
      <div class="hidden md:flex items-center gap-2">
        <!-- User Menu (Vuetify - will be migrated in 03-02) -->
        <UserMenu v-if="authStore.isAuthenticated" />

        <!-- Login Button -->
        <Button v-else variant="default" size="sm" as-child>
          <RouterLink to="/login">
            <LogIn class="mr-2 size-4" />
            Login
          </RouterLink>
        </Button>

        <!-- Theme Toggle -->
        <Button
          variant="ghost"
          size="icon"
          :title="isDark ? 'Switch to light mode' : 'Switch to dark mode'"
          @click="toggleTheme"
        >
          <Sun v-if="isDark" class="size-5" />
          <Moon v-else class="size-5" />
        </Button>
      </div>

      <!-- Mobile Menu Button -->
      <div class="flex md:hidden ml-auto">
        <Button variant="ghost" size="icon" @click="drawerOpen = true">
          <Menu class="size-5" />
          <span class="sr-only">Toggle menu</span>
        </Button>
      </div>
    </div>
  </header>

  <!-- Mobile Navigation Drawer -->
  <Sheet v-model:open="drawerOpen">
    <SheetContent side="left" class="w-72 px-0">
      <SheetHeader class="px-4 pb-4 border-b">
        <SheetTitle class="text-left">
          <KGDBLogo :size="28" variant="with-text" text-layout="horizontal" :animated="false" />
        </SheetTitle>
      </SheetHeader>

      <!-- User Section (authenticated) -->
      <div v-if="authStore.isAuthenticated" class="px-4 py-3">
        <div class="flex items-center gap-3">
          <div
            class="flex size-10 items-center justify-center rounded-full bg-primary text-primary-foreground"
          >
            <CircleUser class="size-5" />
          </div>
          <div class="flex flex-col">
            <span class="text-sm font-medium">{{ authStore.user?.username }}</span>
            <span class="text-xs text-muted-foreground">{{ authStore.user?.email }}</span>
          </div>
        </div>
        <div class="mt-3 flex flex-col gap-1">
          <button
            class="flex items-center gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-accent"
            @click="navigateMobile('/profile')"
          >
            <CircleUser class="size-4" />
            My Profile
          </button>
          <button
            v-if="authStore.isAdmin"
            class="flex items-center gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-accent"
            @click="navigateMobile('/admin')"
          >
            <ShieldEllipsis class="size-4" />
            Admin Panel
          </button>
          <button
            class="flex items-center gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-accent"
            @click="handleLogout"
          >
            <LogOut class="size-4" />
            Logout
          </button>
        </div>
        <Separator class="mt-3" />
      </div>

      <!-- Login (unauthenticated) -->
      <div v-else class="px-4 py-3">
        <button
          class="flex items-center gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-accent w-full"
          @click="navigateMobile('/login')"
        >
          <LogIn class="size-4" />
          Login
        </button>
        <Separator class="mt-3" />
      </div>

      <!-- Nav Links -->
      <nav class="flex flex-col gap-1 px-4 py-2">
        <button
          v-for="link in navLinks"
          :key="link.to"
          class="flex items-center gap-3 rounded-md px-2 py-2 text-sm transition-colors hover:bg-accent"
          :class="{
            'bg-accent text-accent-foreground font-medium': isActive(link.to),
            'text-muted-foreground': !isActive(link.to)
          }"
          @click="navigateMobile(link.to)"
        >
          <component :is="link.icon" class="size-4" />
          {{ link.label }}
        </button>
      </nav>

      <!-- Theme Toggle at Bottom -->
      <div class="mt-auto border-t px-4 py-3">
        <button
          class="flex items-center gap-3 rounded-md px-2 py-2 text-sm hover:bg-accent w-full"
          @click="toggleTheme"
        >
          <Sun v-if="isDark" class="size-4" />
          <Moon v-else class="size-4" />
          {{ isDark ? 'Light Mode' : 'Dark Mode' }}
        </button>
      </div>
    </SheetContent>
  </Sheet>
</template>
