<template>
  <div class="panelapp-evidence">
    <!-- Panels list -->
    <div v-if="panels?.length" class="mb-4">
      <div class="text-subtitle-2 font-weight-medium mb-3">Panels ({{ panelCount }})</div>

      <v-list density="compact" class="transparent">
        <v-list-item
          v-for="(panel, index) in displayPanels"
          :key="index"
          class="px-0 mb-2 panel-item"
        >
          <template #prepend>
            <v-avatar size="24" :color="getRegionColor(panel.region)">
              <span class="text-caption font-weight-bold">{{ getRegionCode(panel.region) }}</span>
            </v-avatar>
          </template>

          <div>
            <div class="text-body-2 font-weight-medium">
              {{ panel.name }}
            </div>
            <div class="text-caption text-medium-emphasis">
              Version {{ panel.version }} • {{ panel.region }}
            </div>
          </div>

          <template #append>
            <v-btn
              icon="mdi-open-in-new"
              size="x-small"
              variant="text"
              :href="getPanelUrl(panel)"
              target="_blank"
            />
          </template>
        </v-list-item>
      </v-list>

      <!-- Show more button -->
      <v-btn
        v-if="hasMorePanels"
        variant="text"
        size="small"
        class="mt-2"
        @click="showAllPanels = !showAllPanels"
      >
        {{ showAllPanels ? 'Show Less' : `Show ${remainingPanels} More Panels` }}
        <v-icon :icon="showAllPanels ? 'mdi-chevron-up' : 'mdi-chevron-down'" end />
      </v-btn>
    </div>

    <!-- Regions summary -->
    <div v-if="regions?.length" class="mb-4">
      <div class="text-subtitle-2 font-weight-medium mb-2">Regions</div>
      <div class="d-flex ga-2">
        <v-chip
          v-for="region in regions"
          :key="region"
          size="small"
          :color="getRegionColor(region)"
          variant="tonal"
        >
          <v-icon icon="mdi-map-marker" start size="x-small" />
          {{ region }}
        </v-chip>
      </div>
    </div>

    <!-- Phenotypes -->
    <div v-if="phenotypes?.length" class="mb-4">
      <div class="text-subtitle-2 font-weight-medium mb-2">Associated Phenotypes</div>
      <div class="phenotype-chips">
        <v-chip
          v-for="(phenotype, index) in displayPhenotypes"
          :key="index"
          size="x-small"
          variant="outlined"
          color="orange"
        >
          {{ phenotype }}
        </v-chip>
        <v-chip
          v-if="phenotypes.length > 5"
          size="x-small"
          variant="outlined"
          @click="showAllPhenotypes = !showAllPhenotypes"
        >
          {{ showAllPhenotypes ? 'Show Less' : `+${phenotypes.length - 5} more` }}
        </v-chip>
      </div>
    </div>

    <!-- Evidence levels -->
    <div v-if="evidenceLevels?.length" class="mb-4">
      <div class="text-subtitle-2 font-weight-medium mb-2">Evidence Levels</div>
      <div class="d-flex ga-2">
        <v-chip
          v-for="level in evidenceLevels"
          :key="level"
          size="small"
          :color="getEvidenceLevelColor(level)"
          variant="tonal"
        >
          Level {{ level }}
        </v-chip>
      </div>
    </div>

    <!-- Modes of inheritance -->
    <div v-if="modesOfInheritance?.length" class="mb-4">
      <div class="text-subtitle-2 font-weight-medium mb-2">Inheritance</div>
      <v-list density="compact" class="transparent">
        <v-list-item v-for="mode in modesOfInheritance" :key="mode" class="px-0">
          <template #prepend>
            <v-icon icon="mdi-family-tree" size="x-small" color="orange" />
          </template>
          <v-list-item-title class="text-caption">{{ formatInheritance(mode) }}</v-list-item-title>
        </v-list-item>
      </v-list>
    </div>

    <!-- Statistics -->
    <div class="mt-4 pa-3 bg-surface-light rounded">
      <v-row dense>
        <v-col cols="4">
          <div class="text-center">
            <div class="text-h5 font-weight-bold text-orange">
              {{ panelCount }}
            </div>
            <div class="text-caption text-medium-emphasis">Panels</div>
          </div>
        </v-col>
        <v-col cols="4">
          <div class="text-center">
            <div class="text-h5 font-weight-bold text-orange">
              {{ regions?.length || 0 }}
            </div>
            <div class="text-caption text-medium-emphasis">Regions</div>
          </div>
        </v-col>
        <v-col cols="4">
          <div class="text-center">
            <div class="text-h5 font-weight-bold text-orange">
              {{ phenotypes?.length || 0 }}
            </div>
            <div class="text-caption text-medium-emphasis">Phenotypes</div>
          </div>
        </v-col>
      </v-row>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

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
    UK: 'blue',
    Australia: 'green',
    US: 'red',
    Europe: 'purple'
  }
  return colors[region] || 'grey'
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
    3: 'success',
    2: 'warning',
    1: 'error',
    0: 'grey'
  }
  return colors[level] || 'grey'
}

const formatInheritance = mode => {
  // Shorten long inheritance descriptions
  if (mode.length > 80) {
    return mode.substring(0, 77) + '...'
  }
  return mode
}
</script>

<style scoped>
.panelapp-evidence {
  max-width: 100%;
}

.panel-item {
  padding: 8px;
  background: rgba(var(--v-theme-surface-variant), 0.1);
  border-radius: 6px;
  margin-bottom: 4px;
}

.phenotype-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.bg-surface-light {
  background: rgba(var(--v-theme-surface-variant), 0.3);
}
</style>
