<template>
  <v-dialog v-model="dialog" max-width="700" scrollable>
    <template #activator="{ props }">
      <v-btn v-bind="props" variant="text" size="small" color="primary">
        <v-icon start>mdi-help-circle-outline</v-icon>
        Understanding Evidence Tiers
      </v-btn>
    </template>

    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon color="primary" class="mr-2">mdi-information</v-icon>
        <span>Evidence Tier Classification</span>
      </v-card-title>

      <v-divider />

      <v-card-text class="pa-4">
        <!-- Introduction -->
        <div class="text-body-2 mb-4">
          Genes are automatically classified into evidence tiers based on the number of supporting
          data sources and the overall evidence score. This classification helps identify genes with
          stronger scientific support for their disease associations.
        </div>

        <v-alert type="info" variant="tonal" density="compact" class="mb-4">
          <strong>Note:</strong> These automated tiers are separate from manual ClinGen clinical
          validity curation, which will be integrated in future updates.
        </v-alert>

        <!-- Major Groups -->
        <div class="mb-5">
          <div class="text-h6 mb-3">Evidence Groups</div>

          <div v-for="(config, groupKey) in GROUP_CONFIG" :key="groupKey" class="mb-3">
            <v-card variant="outlined" class="pa-3">
              <div class="d-flex align-center mb-2">
                <v-chip :color="config.color" size="small" variant="flat" class="mr-2">
                  <v-icon :icon="config.icon" size="small" start />
                  {{ config.label }}
                </v-chip>
              </div>
              <div class="text-body-2">{{ config.description }}</div>
            </v-card>
          </div>
        </div>

        <!-- Detailed Tiers -->
        <div>
          <div class="text-h6 mb-3">Evidence Tiers</div>

          <div v-for="(config, tierKey) in TIER_CONFIG" :key="tierKey" class="mb-3">
            <v-card variant="outlined" class="pa-3">
              <div class="d-flex align-center mb-2">
                <v-chip :color="config.color" size="small" variant="flat" class="mr-2">
                  <v-icon :icon="config.icon" size="small" start />
                  {{ config.label }}
                </v-chip>
              </div>
              <div class="text-body-2">{{ config.description }}</div>
            </v-card>
          </div>
        </div>

        <!-- Data Sources Info -->
        <v-divider class="my-4" />

        <div class="text-body-2">
          <strong>Evidence sources include:</strong> PanelApp (gene panels), HPO (phenotype
          associations), ClinGen (clinical validity), GenCC (gene-disease curation), PubTator
          (literature mining), and additional curated databases.
        </div>
      </v-card-text>

      <v-divider />

      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" @click="dialog = false">Close</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref } from 'vue'
import { TIER_CONFIG, GROUP_CONFIG } from '@/utils/evidenceTiers'

// Dialog state
const dialog = ref(false)
</script>

<style scoped>
/* Following Style Guide - Clean information display */
.v-card {
  border: 1px solid rgb(var(--v-theme-surface-variant));
}

.v-card-text {
  line-height: 1.6;
}

/* Dark theme adjustments */
.v-theme--dark .v-card {
  background: rgb(var(--v-theme-surface));
}
</style>
