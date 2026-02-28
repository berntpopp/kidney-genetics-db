<template>
  <div class="max-w-full">
    <!-- Panels list -->
    <div v-if="panels?.length" class="mb-4">
      <div class="text-sm font-medium mb-3">Panels ({{ panelCount }})</div>

      <div class="space-y-1">
        <div
          v-for="(panel, index) in displayPanels"
          :key="index"
          class="flex items-center gap-3 p-2 rounded-md bg-muted/30"
        >
          <Avatar class="h-6 w-6" :style="{ backgroundColor: getRegionColor(panel.region) + '20' }">
            <AvatarFallback
              class="text-[10px] font-bold"
              :style="{ color: getRegionColor(panel.region) }"
            >
              {{ getRegionCode(panel.region) }}
            </AvatarFallback>
          </Avatar>

          <div class="flex-1 min-w-0">
            <div class="text-sm font-medium truncate">
              {{ panel.name }}
            </div>
            <div class="text-xs text-muted-foreground">
              Version {{ panel.version }} &bull; {{ panel.region }}
            </div>
          </div>

          <Button
            variant="ghost"
            size="icon"
            class="h-6 w-6 shrink-0"
            as="a"
            :href="getPanelUrl(panel)"
            target="_blank"
          >
            <ExternalLink class="size-3" />
          </Button>
        </div>
      </div>

      <!-- Show more button -->
      <Button
        v-if="hasMorePanels"
        variant="ghost"
        size="sm"
        class="mt-2"
        @click="showAllPanels = !showAllPanels"
      >
        {{ showAllPanels ? 'Show Less' : `Show ${remainingPanels} More Panels` }}
        <component :is="showAllPanels ? ChevronUp : ChevronDown" class="size-4 ml-1" />
      </Button>
    </div>

    <!-- Regions summary -->
    <div v-if="regions?.length" class="mb-4">
      <div class="text-sm font-medium mb-2">Regions</div>
      <div class="flex flex-wrap gap-2">
        <Badge
          v-for="region in regions"
          :key="region"
          variant="outline"
          :style="{
            borderColor: getRegionColor(region),
            color: getRegionColor(region),
            backgroundColor: getRegionColor(region) + '15'
          }"
        >
          <MapPin class="size-3 mr-1" />
          {{ region }}
        </Badge>
      </div>
    </div>

    <!-- Phenotypes -->
    <div v-if="phenotypes?.length" class="mb-4">
      <div class="text-sm font-medium mb-2">Associated Phenotypes</div>
      <div class="flex flex-wrap gap-1.5">
        <Badge
          v-for="(phenotype, index) in displayPhenotypes"
          :key="index"
          variant="outline"
          :style="{
            borderColor: '#f97316',
            color: '#f97316'
          }"
          class="text-xs"
        >
          {{ phenotype }}
        </Badge>
        <Badge
          v-if="phenotypes.length > 5"
          variant="outline"
          class="text-xs cursor-pointer"
          @click="showAllPhenotypes = !showAllPhenotypes"
        >
          {{ showAllPhenotypes ? 'Show Less' : `+${phenotypes.length - 5} more` }}
        </Badge>
      </div>
    </div>

    <!-- Evidence levels -->
    <div v-if="evidenceLevels?.length" class="mb-4">
      <div class="text-sm font-medium mb-2">Evidence Levels</div>
      <div class="flex flex-wrap gap-2">
        <Badge
          v-for="level in evidenceLevels"
          :key="level"
          variant="outline"
          :style="{
            borderColor: getEvidenceLevelColor(level),
            color: getEvidenceLevelColor(level),
            backgroundColor: getEvidenceLevelColor(level) + '15'
          }"
        >
          Level {{ level }}
        </Badge>
      </div>
    </div>

    <!-- Modes of inheritance -->
    <div v-if="modesOfInheritance?.length" class="mb-4">
      <div class="text-sm font-medium mb-2">Inheritance</div>
      <div class="space-y-1">
        <div v-for="mode in modesOfInheritance" :key="mode" class="flex items-center gap-2 py-1">
          <GitBranch class="size-3 text-yellow-600 dark:text-yellow-400 shrink-0" />
          <span class="text-xs">{{ formatInheritance(mode) }}</span>
        </div>
      </div>
    </div>

    <!-- Statistics -->
    <div class="mt-4 p-3 bg-muted/30 rounded-md">
      <div class="grid grid-cols-3 gap-4">
        <div class="text-center">
          <div class="text-xl font-bold" style="color: #f97316">
            {{ panelCount }}
          </div>
          <div class="text-xs text-muted-foreground">Panels</div>
        </div>
        <div class="text-center">
          <div class="text-xl font-bold" style="color: #f97316">
            {{ regions?.length || 0 }}
          </div>
          <div class="text-xs text-muted-foreground">Regions</div>
        </div>
        <div class="text-center">
          <div class="text-xl font-bold" style="color: #f97316">
            {{ phenotypes?.length || 0 }}
          </div>
          <div class="text-xs text-muted-foreground">Phenotypes</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ChevronUp, ChevronDown, MapPin, GitBranch, ExternalLink } from 'lucide-vue-next'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'

const props = defineProps({
  evidenceData: {
    type: Object,
    required: true
  },
  sourceName: {
    type: String,
    default: 'PanelApp'
  }
})

const showAllPanels = ref(false)
const showAllPhenotypes = ref(false)

// Data accessors
const panels = computed(() => {
  return props.evidenceData?.panels || []
})

const panelCount = computed(() => {
  return props.evidenceData?.panel_count || panels.value.length
})

const regions = computed(() => {
  return props.evidenceData?.regions || []
})

const phenotypes = computed(() => {
  return props.evidenceData?.phenotypes || []
})

const evidenceLevels = computed(() => {
  return props.evidenceData?.evidence_levels || []
})

const modesOfInheritance = computed(() => {
  return props.evidenceData?.modes_of_inheritance || []
})

// Display logic
const displayPanels = computed(() => {
  if (showAllPanels.value) {
    return panels.value
  }
  return panels.value.slice(0, 5)
})

const displayPhenotypes = computed(() => {
  if (showAllPhenotypes.value) {
    return phenotypes.value
  }
  return phenotypes.value.slice(0, 5)
})

const hasMorePanels = computed(() => {
  return panels.value.length > 5
})

const remainingPanels = computed(() => {
  return panels.value.length - 5
})

// Helper functions
const getRegionColor = region => {
  const colors = {
    UK: '#3b82f6',
    Australia: '#22c55e',
    US: '#ef4444',
    Europe: '#8b5cf6'
  }
  return colors[region] || '#6b7280'
}

const getRegionCode = region => {
  const codes = {
    UK: 'UK',
    Australia: 'AU',
    US: 'US',
    Europe: 'EU'
  }
  return codes[region] || region.substring(0, 2).toUpperCase()
}

const getPanelUrl = panel => {
  if (panel.region === 'UK') {
    return `https://panelapp.genomicsengland.co.uk/panels/${panel.id}/`
  } else if (panel.region === 'Australia') {
    return `https://panelapp.agha.umccr.org/panels/${panel.id}/`
  }
  return '#'
}

const getEvidenceLevelColor = level => {
  const colors = {
    3: '#22c55e',
    2: '#f59e0b',
    1: '#ef4444',
    0: '#6b7280'
  }
  return colors[level] || '#6b7280'
}

const formatInheritance = mode => {
  // Shorten long inheritance descriptions
  if (mode.length > 80) {
    return mode.substring(0, 77) + '...'
  }
  return mode
}
</script>
