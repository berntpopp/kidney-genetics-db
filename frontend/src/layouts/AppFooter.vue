<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { getAllVersions, getFrontendVersion } from '@/utils/version'
import { useLogStore } from '@/stores/logStore'
import { Button } from '@/components/ui/button'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter
} from '@/components/ui/dialog'
import {
  BookOpen,
  CircleAlert,
  ExternalLink,
  Github,
  HelpCircle,
  Info,
  Scale,
  Server,
  ShieldAlert,
  ShieldCheck,
  Terminal,
  Wifi,
  WifiOff
} from 'lucide-vue-next'

const GITHUB_URL = 'https://github.com/berntpopp/kidney-genetics-db'

const logStore = useLogStore()

// Version state
const frontendVersion = ref(getFrontendVersion())
const backendVersion = ref('...')
const backendReachable = ref(false)

// Network status (SSR-safe default; actual value set in onMounted)
const isOnline = ref(true)

// Disclaimer
const disclaimerOpen = ref(false)
const disclaimerAcknowledged = ref(false)

// Computed
const errorCount = computed(() => logStore.errorCount)

// Network listeners
const handleOnline = () => {
  isOnline.value = true
}
const handleOffline = () => {
  isOnline.value = false
}

// Fetch backend version
async function checkBackend() {
  try {
    const versions = await getAllVersions()
    backendVersion.value = versions.backend?.version ?? 'unknown'
    backendReachable.value = true
  } catch {
    backendVersion.value = 'unreachable'
    backendReachable.value = false
  }
}

onMounted(() => {
  isOnline.value = navigator.onLine
  window.addEventListener('online', handleOnline)
  window.addEventListener('offline', handleOffline)
  // Check if disclaimer was previously acknowledged
  disclaimerAcknowledged.value = window.localStorage.getItem('kgdb-disclaimer') === 'true'
  checkBackend()
})

onUnmounted(() => {
  window.removeEventListener('online', handleOnline)
  window.removeEventListener('offline', handleOffline)
})

function acknowledgeDisclaimer() {
  disclaimerAcknowledged.value = true
  window.localStorage.setItem('kgdb-disclaimer', 'true')
  disclaimerOpen.value = false
}
</script>

<template>
  <footer class="fixed bottom-0 left-0 right-0 z-40 border-t bg-background/95 backdrop-blur-sm">
    <div class="container mx-auto flex items-center justify-between px-4 h-8">
      <!-- Left: Version + Online status -->
      <div class="flex items-center gap-1.5">
        <TooltipProvider :delay-duration="300">
          <!-- Version popover -->
          <Popover>
            <PopoverTrigger as-child>
              <Button variant="ghost" size="sm" class="h-6 text-[11px] text-muted-foreground px-1">
                <Info class="size-3 mr-1" />
                v{{ frontendVersion }}
              </Button>
            </PopoverTrigger>
            <PopoverContent align="start" side="top" class="w-60 p-3">
              <div class="space-y-2">
                <div class="flex items-center justify-between">
                  <span class="text-xs font-medium">Frontend</span>
                  <Badge variant="secondary" class="text-[10px]">v{{ frontendVersion }}</Badge>
                </div>
                <div class="flex items-center justify-between">
                  <span class="text-xs font-medium">Backend</span>
                  <Badge
                    :variant="backendReachable ? 'secondary' : 'destructive'"
                    class="text-[10px]"
                  >
                    <Server class="size-2.5 mr-1" />
                    {{ backendReachable ? `v${backendVersion}` : 'unreachable' }}
                  </Badge>
                </div>
              </div>
            </PopoverContent>
          </Popover>

          <!-- Online indicator -->
          <Tooltip>
            <TooltipTrigger as-child>
              <div class="flex items-center">
                <Wifi v-if="isOnline" class="size-3 text-green-500" />
                <WifiOff v-else class="size-3 text-destructive" />
              </div>
            </TooltipTrigger>
            <TooltipContent side="top">
              <p>{{ isOnline ? 'Online' : 'Offline — some features unavailable' }}</p>
            </TooltipContent>
          </Tooltip>

          <!-- Backend status -->
          <Tooltip>
            <TooltipTrigger as-child>
              <div class="flex items-center">
                <Server
                  class="size-3"
                  :class="backendReachable ? 'text-green-500' : 'text-destructive'"
                />
              </div>
            </TooltipTrigger>
            <TooltipContent side="top">
              <p>Backend: {{ backendReachable ? `v${backendVersion}` : 'unreachable' }}</p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>

      <!-- Right: Links + Log viewer -->
      <div class="flex items-center gap-0.5">
        <TooltipProvider :delay-duration="300">
          <!-- GitHub -->
          <Tooltip>
            <TooltipTrigger as-child>
              <Button variant="ghost" size="icon" class="size-6" as-child>
                <a
                  :href="GITHUB_URL"
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label="GitHub Repository"
                >
                  <Github class="size-3.5" />
                </a>
              </Button>
            </TooltipTrigger>
            <TooltipContent side="top"><p>GitHub Repository</p></TooltipContent>
          </Tooltip>

          <!-- Docs -->
          <Tooltip>
            <TooltipTrigger as-child>
              <Button variant="ghost" size="icon" class="size-6" as-child>
                <a
                  :href="`${GITHUB_URL}#readme`"
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label="Documentation"
                >
                  <BookOpen class="size-3.5" />
                </a>
              </Button>
            </TooltipTrigger>
            <TooltipContent side="top"><p>Documentation</p></TooltipContent>
          </Tooltip>

          <!-- License -->
          <Tooltip>
            <TooltipTrigger as-child>
              <Button variant="ghost" size="icon" class="size-6" as-child>
                <a
                  :href="`${GITHUB_URL}/blob/main/LICENSE`"
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label="License"
                >
                  <Scale class="size-3.5" />
                </a>
              </Button>
            </TooltipTrigger>
            <TooltipContent side="top"><p>License</p></TooltipContent>
          </Tooltip>

          <!-- FAQ / Issues -->
          <Tooltip>
            <TooltipTrigger as-child>
              <Button variant="ghost" size="icon" class="size-6" as-child>
                <a
                  :href="`${GITHUB_URL}/issues`"
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label="FAQ and Issues"
                >
                  <HelpCircle class="size-3.5" />
                </a>
              </Button>
            </TooltipTrigger>
            <TooltipContent side="top"><p>FAQ &amp; Issues</p></TooltipContent>
          </Tooltip>

          <Separator orientation="vertical" class="h-4 mx-0.5" />

          <!-- Disclaimer -->
          <Tooltip>
            <TooltipTrigger as-child>
              <Button
                variant="ghost"
                size="icon"
                class="size-6"
                :class="disclaimerAcknowledged ? 'text-green-600' : 'text-amber-500'"
                :aria-label="disclaimerAcknowledged ? 'Disclaimer acknowledged' : 'View disclaimer'"
                @click="disclaimerOpen = true"
              >
                <ShieldCheck v-if="disclaimerAcknowledged" class="size-3.5" />
                <ShieldAlert v-else class="size-3.5" />
              </Button>
            </TooltipTrigger>
            <TooltipContent side="top">
              <p>{{ disclaimerAcknowledged ? 'Disclaimer acknowledged' : 'View disclaimer' }}</p>
            </TooltipContent>
          </Tooltip>

          <!-- Log Viewer -->
          <Tooltip>
            <TooltipTrigger as-child>
              <Button
                variant="ghost"
                size="icon"
                class="size-6 relative"
                aria-label="Log Viewer"
                @click="logStore.showViewer"
              >
                <Terminal class="size-3.5" />
                <span
                  v-if="errorCount > 0"
                  class="absolute -top-0.5 -right-0.5 size-2 rounded-full bg-destructive"
                />
              </Button>
            </TooltipTrigger>
            <TooltipContent side="top">
              <p>
                Log Viewer
                <kbd class="ml-1 text-[10px] opacity-60">Ctrl+Shift+L</kbd>
              </p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>
    </div>

    <!-- Disclaimer Dialog -->
    <Dialog v-model:open="disclaimerOpen">
      <DialogContent class="max-w-lg">
        <DialogHeader>
          <DialogTitle class="flex items-center gap-2">
            <CircleAlert class="size-5 text-amber-500" />
            Research Use Disclaimer
          </DialogTitle>
          <DialogDescription>
            Please read and acknowledge before using this application.
          </DialogDescription>
        </DialogHeader>
        <div class="space-y-3 text-sm">
          <p>
            The <strong>Kidney Genetics Database (KGDB)</strong> aggregates gene-disease association
            data from multiple public sources including ClinGen, GenCC, PanelApp, HPO, ClinVar,
            gnomAD, and PubMed.
          </p>
          <div class="rounded-md border border-amber-200 bg-amber-50 dark:bg-amber-950/20 p-3">
            <p class="text-amber-800 dark:text-amber-200 text-xs">
              The information on this website is not intended for direct diagnostic use or medical
              decision-making without review by a genetics professional. Individuals should not
              change their health behavior solely on the basis of information contained on this
              website. KGDB does not independently verify the data obtained from these sources.
            </p>
          </div>
          <p class="text-xs text-muted-foreground">
            Data may be incomplete, outdated, or contain errors inherent to the original sources.
            Researchers should always verify findings against primary source databases. This tool is
            provided as-is under the
            <a
              :href="`${GITHUB_URL}/blob/main/LICENSE`"
              target="_blank"
              rel="noopener noreferrer"
              class="underline"
            >
              MIT License
              <ExternalLink class="size-2.5 inline" />
            </a>
            .
          </p>
        </div>
        <DialogFooter>
          <Button v-if="!disclaimerAcknowledged" variant="default" @click="acknowledgeDisclaimer">
            <ShieldCheck class="size-4 mr-1" />
            I Understand
          </Button>
          <Button v-else variant="outline" @click="disclaimerOpen = false">Close</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </footer>
</template>
