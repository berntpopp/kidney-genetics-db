<template>
  <Dialog v-model:open="showDialog">
    <DialogTrigger as-child>
      <Button variant="ghost" size="sm" class="h-8 gap-1 text-primary">
        <CircleHelp :size="16" />
        Understanding Evidence Tiers
      </Button>
    </DialogTrigger>
    <DialogContent class="max-w-[700px] max-h-[80vh]">
      <DialogHeader>
        <DialogTitle class="flex items-center gap-2">
          <Info :size="20" class="text-primary" />
          Evidence Tier Classification
        </DialogTitle>
        <DialogDescription> Understanding evidence tiers and groups </DialogDescription>
      </DialogHeader>
      <ScrollArea class="max-h-[60vh] pr-4">
        <!-- Introduction -->
        <p class="text-sm mb-4">
          Genes are automatically classified into evidence tiers based on the number of supporting
          data sources and the overall evidence score. This classification helps identify genes with
          stronger scientific support for their disease associations.
        </p>

        <Alert class="mb-4">
          <Info :size="16" />
          <AlertDescription class="text-xs">
            <strong>Note:</strong> These automated tiers are separate from manual ClinGen clinical
            validity curation, which will be integrated in future updates.
          </AlertDescription>
        </Alert>

        <!-- Evidence Groups -->
        <h3 class="text-base font-semibold mb-3">Evidence Groups</h3>
        <div class="space-y-2 mb-6">
          <div
            v-for="(config, groupKey) in GROUP_CONFIG"
            :key="groupKey"
            class="flex items-start gap-3 p-2 rounded-md border"
          >
            <component
              :is="config.icon"
              :size="18"
              :style="{ color: config.color }"
              class="mt-0.5 shrink-0"
            />
            <div>
              <Badge
                :style="{ backgroundColor: config.color + '20', color: config.color }"
                variant="outline"
              >
                {{ config.label }}
              </Badge>
              <p class="text-xs text-muted-foreground mt-1">{{ config.description }}</p>
            </div>
          </div>
        </div>

        <Separator class="my-4" />

        <!-- Evidence Tiers -->
        <h3 class="text-base font-semibold mb-3">Evidence Tiers</h3>
        <div class="space-y-2 mb-6">
          <div
            v-for="(config, tierKey) in TIER_CONFIG"
            :key="tierKey"
            class="flex items-start gap-3 p-2 rounded-md border"
          >
            <component
              :is="config.icon"
              :size="18"
              :style="{ color: config.color }"
              class="mt-0.5 shrink-0"
            />
            <div>
              <Badge
                :style="{ backgroundColor: config.color + '20', color: config.color }"
                variant="outline"
              >
                {{ config.label }}
              </Badge>
              <p class="text-xs text-muted-foreground mt-1">{{ config.description }}</p>
            </div>
          </div>
        </div>

        <Separator class="my-4" />

        <!-- Data Sources Info -->
        <p class="text-sm">
          <strong>Evidence sources include:</strong> PanelApp (gene panels), HPO (phenotype
          associations), ClinGen (clinical validity), GenCC (gene-disease curation), PubTator
          (literature mining), and additional curated databases.
        </p>
      </ScrollArea>
      <DialogFooter>
        <Button variant="outline" @click="showDialog = false">Close</Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>

<script setup>
import { ref } from 'vue'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Separator } from '@/components/ui/separator'
import { ScrollArea } from '@/components/ui/scroll-area'
import { CircleHelp, Info } from 'lucide-vue-next'
import { TIER_CONFIG, GROUP_CONFIG } from '@/utils/evidenceTiers'

const showDialog = ref(false)
</script>
