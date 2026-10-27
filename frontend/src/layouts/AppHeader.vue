<script setup lang="ts">
import { computed, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import { KGDBLogo } from '@/components/branding'
import UserMenu from '@/components/auth/UserMenu.vue'
import LoginModal from '@/components/auth/LoginModal.vue'
import { Button } from '@/components/ui/button'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle
} from '@/components/ui/sheet'
import { Separator } from '@/components/ui/separator'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
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
  HelpCircle,
  CircleUser,
  ShieldEllipsis,
  ListChecks,
  LogOut,
  BookCheck
} from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const { isDark, toggleTheme } = useAppTheme()

const drawerOpen = ref(false)
const loginModalOpen = ref(false)

const themeLabel = computed(() => (isDark.value ? 'Switch to light mode' : 'Switch to dark mode'))

const handleLoginSuccess = (username: string) => {
  loginModalOpen.value = false
  toast.success(`Logged in as ${username}`, { duration: 5000 })
}

const navLinks = [
  { to: '/genes', label: 'Gene Browser', icon: Dna },
  { to: '/dashboard', label: 'Data Overview', icon: LayoutDashboard },
  { to: '/network-analysis', label: 'Network Analysis', icon: Network },
  { to: '/data-sources', label: 'Data Sources', icon: RefreshCw },
  { to: '/curation/associations', label: 'Curated', icon: BookCheck },
  { to: '/about', label: 'About', icon: Info },
  { to: '/faq', label: 'FAQ', icon: HelpCircle }
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

const openLoginFromDrawer = () => {
  drawerOpen.value = false
  loginModalOpen.value = true
}

const drawerItem =
  'flex min-h-11 w-full items-center gap-3 rounded-md px-2 text-sm transition-colors hover:bg-accent focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none'
</script>

<template>
  <header
    class="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80"
  >
    <div class="mx-auto flex h-14 w-full max-w-7xl items-center px-4 sm:px-6 lg:px-8">
      <RouterLink
        to="/"
        aria-label="Kidney-Genetics Database home"
        class="mr-6 flex shrink-0 items-center rounded-md focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
      >
        <KGDBLogo
          :size="32"
          variant="with-text"
          text-layout="horizontal"
          :animated="false"
          :interactive="false"
        />
      </RouterLink>

      <!-- Active link: weight + primary underline. The invisible bold ::after copy reserves
           the bold width, so links never shift when the active route changes. -->
      <nav aria-label="Main" class="hidden h-full flex-1 items-stretch gap-1 md:flex">
        <RouterLink
          v-for="link in navLinks"
          :key="link.to"
          :to="link.to"
          :data-label="link.label"
          :aria-current="isActive(link.to) ? 'page' : undefined"
          class="inline-flex flex-col items-center justify-center border-b-2 px-3 pt-0.5 text-sm whitespace-nowrap transition-colors after:invisible after:h-0 after:overflow-hidden after:font-semibold after:content-[attr(data-label)] hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none focus-visible:ring-inset"
          :class="
            isActive(link.to)
              ? 'border-primary font-semibold text-foreground'
              : 'border-transparent font-medium text-muted-foreground'
          "
        >
          {{ link.label }}
        </RouterLink>
      </nav>

      <div class="hidden items-center gap-2 md:flex">
        <UserMenu v-if="authStore.isAuthenticated" />
        <Button v-else variant="default" size="sm" @click="loginModalOpen = true">
          <LogIn class="mr-2 size-4" aria-hidden="true" />
          Login
        </Button>

        <Tooltip>
          <TooltipTrigger as-child>
            <Button variant="ghost" size="icon" :aria-label="themeLabel" @click="toggleTheme">
              <Sun v-if="isDark" class="size-5" aria-hidden="true" />
              <Moon v-else class="size-5" aria-hidden="true" />
            </Button>
          </TooltipTrigger>
          <TooltipContent>{{ themeLabel }}</TooltipContent>
        </Tooltip>
      </div>

      <div class="ml-auto flex md:hidden">
        <Tooltip>
          <TooltipTrigger as-child>
            <Button
              variant="ghost"
              size="icon"
              class="size-11"
              aria-label="Open menu"
              :aria-expanded="drawerOpen"
              @click="drawerOpen = true"
            >
              <Menu class="size-5" aria-hidden="true" />
            </Button>
          </TooltipTrigger>
          <TooltipContent>Open menu</TooltipContent>
        </Tooltip>
      </div>
    </div>
  </header>

  <!-- Mobile Navigation Drawer -->
  <Sheet v-model:open="drawerOpen">
    <SheetContent side="left" class="w-72 bg-background px-0">
      <SheetHeader class="border-b px-4 pb-4">
        <SheetTitle class="text-left">
          <KGDBLogo :size="28" variant="with-text" text-layout="horizontal" :animated="false" />
        </SheetTitle>
        <SheetDescription class="sr-only">Navigation menu</SheetDescription>
      </SheetHeader>

      <!-- User Section (authenticated) -->
      <div v-if="authStore.isAuthenticated" class="px-4 py-3">
        <div class="flex items-center gap-3">
          <div
            class="flex size-10 items-center justify-center rounded-full bg-primary text-primary-foreground"
          >
            <CircleUser class="size-5" aria-hidden="true" />
          </div>
          <div class="flex flex-col">
            <span class="text-sm font-medium">{{ authStore.user?.username }}</span>
            <span class="text-xs text-muted-foreground">{{ authStore.user?.email }}</span>
          </div>
        </div>
        <div class="mt-3 flex flex-col gap-1">
          <button :class="[drawerItem, 'text-foreground']" @click="navigateMobile('/profile')">
            <CircleUser class="size-4" aria-hidden="true" />
            My Profile
          </button>
          <button
            v-if="authStore.isCurator && !authStore.isAdmin"
            :class="[drawerItem, 'text-foreground']"
            @click="navigateMobile('/admin/staging')"
          >
            <ListChecks class="size-4" aria-hidden="true" />
            Gene Staging
          </button>
          <button
            v-if="authStore.isAdmin"
            :class="[drawerItem, 'text-foreground']"
            @click="navigateMobile('/admin')"
          >
            <ShieldEllipsis class="size-4" aria-hidden="true" />
            Admin Panel
          </button>
          <button :class="[drawerItem, 'text-foreground']" @click="handleLogout">
            <LogOut class="size-4" aria-hidden="true" />
            Logout
          </button>
        </div>
        <Separator class="mt-3" />
      </div>

      <!-- Login (unauthenticated) -->
      <div v-else class="px-4 py-3">
        <button :class="[drawerItem, 'text-foreground']" @click="openLoginFromDrawer">
          <LogIn class="size-4" aria-hidden="true" />
          Login
        </button>
        <Separator class="mt-3" />
      </div>

      <nav aria-label="Main" class="flex flex-col gap-1 px-4 py-2">
        <RouterLink
          v-for="link in navLinks"
          :key="link.to"
          :to="link.to"
          :aria-current="isActive(link.to) ? 'page' : undefined"
          :class="[
            drawerItem,
            isActive(link.to)
              ? 'bg-accent font-semibold text-primary'
              : 'font-medium text-foreground'
          ]"
          @click="drawerOpen = false"
        >
          <component :is="link.icon" class="size-4" aria-hidden="true" />
          {{ link.label }}
        </RouterLink>
      </nav>

      <div class="mt-auto border-t px-4 py-3">
        <button :class="[drawerItem, 'text-foreground']" @click="toggleTheme">
          <Sun v-if="isDark" class="size-4" aria-hidden="true" />
          <Moon v-else class="size-4" aria-hidden="true" />
          {{ isDark ? 'Light mode' : 'Dark mode' }}
        </button>
      </div>
    </SheetContent>
  </Sheet>

  <LoginModal v-model:open="loginModalOpen" @login-success="handleLoginSuccess" />
</template>
