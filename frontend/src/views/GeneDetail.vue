<template>
  <v-container>
    <v-row v-if="loading">
      <v-col cols="12" class="text-center">
        <v-progress-circular indeterminate color="primary" />
      </v-col>
    </v-row>

    <template v-else-if="gene">
      <!-- Header -->
      <v-row>
        <v-col cols="12">
          <v-btn icon="mdi-arrow-left" variant="text" to="/genes" class="mb-4" />
          <h1 class="text-h3">{{ gene.approved_symbol }}</h1>
          <p class="text-subtitle-1">HGNC ID: {{ gene.hgnc_id }}</p>
        </v-col>
      </v-row>

      <!-- Gene Info Card -->
      <v-row>
        <v-col cols="12" md="4">
          <v-card>
            <v-card-title>Gene Information</v-card-title>
            <v-list>
              <v-list-item>
                <v-list-item-title>Symbol</v-list-item-title>
                <v-list-item-subtitle>{{ gene.approved_symbol }}</v-list-item-subtitle>
              </v-list-item>
              <v-list-item>
                <v-list-item-title>HGNC ID</v-list-item-title>
                <v-list-item-subtitle>{{ gene.hgnc_id }}</v-list-item-subtitle>
              </v-list-item>
              <v-list-item v-if="gene.aliases?.length">
                <v-list-item-title>Aliases</v-list-item-title>
                <v-list-item-subtitle>{{ gene.aliases.join(', ') }}</v-list-item-subtitle>
              </v-list-item>
              <v-list-item>
                <v-list-item-title>Evidence Count</v-list-item-title>
                <v-list-item-subtitle>{{ gene.evidence_count || 0 }}</v-list-item-subtitle>
              </v-list-item>
              <v-list-item v-if="gene.evidence_score">
                <v-list-item-title>Evidence Score</v-list-item-title>
                <v-list-item-subtitle>
                  <v-chip :color="getScoreColor(gene.evidence_score)" size="small">
                    {{ gene.evidence_score.toFixed(1) }}
                  </v-chip>
                </v-list-item-subtitle>
              </v-list-item>
            </v-list>
          </v-card>
        </v-col>

        <!-- Sources Card -->
        <v-col cols="12" md="8">
          <v-card>
            <v-card-title>Data Sources</v-card-title>
            <v-card-text>
              <v-chip
                v-for="source in gene.sources"
                :key="source"
                :color="getSourceColor(source)"
                class="ma-1"
              >
                {{ source }}
              </v-chip>
              <p v-if="!gene.sources?.length" class="text-grey">No source information available</p>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <!-- Evidence Section -->
      <v-row class="mt-4">
        <v-col cols="12">
          <h2 class="text-h5 mb-4">Evidence Details</h2>
        </v-col>
      </v-row>

      <v-row v-if="loadingEvidence">
        <v-col cols="12" class="text-center">
          <v-progress-circular indeterminate color="primary" />
        </v-col>
      </v-row>

      <v-row v-else-if="evidence?.evidence?.length">
        <v-col cols="12">
          <v-expansion-panels>
            <v-expansion-panel v-for="(item, index) in evidence.evidence" :key="index">
              <v-expansion-panel-title>
                <div>
                  <strong>{{ item.source_name }}</strong>
                  <span class="text-grey ml-2">{{ item.source_detail }}</span>
                </div>
              </v-expansion-panel-title>
              <v-expansion-panel-text>
                <!-- Panels Section -->
                <div v-if="item.evidence_data?.panels?.length" class="mb-4">
                  <h4 class="text-subtitle-2 mb-2">Gene Panels</h4>
                  <v-chip
                    v-for="panel in item.evidence_data.panels"
                    :key="panel.id"
                    size="small"
                    class="ma-1"
                  >
                    {{ panel.name }} (v{{ panel.version }})
                  </v-chip>
                </div>

                <!-- Phenotypes Section -->
                <div v-if="item.evidence_data?.phenotypes?.length" class="mb-4">
                  <h4 class="text-subtitle-2 mb-2">Phenotypes</h4>
                  <v-list density="compact">
                    <v-list-item
                      v-for="(phenotype, idx) in item.evidence_data.phenotypes"
                      :key="idx"
                    >
                      <v-list-item-title>{{ phenotype }}</v-list-item-title>
                    </v-list-item>
                  </v-list>
                </div>

                <!-- Inheritance Modes -->
                <div v-if="item.evidence_data?.modes_of_inheritance?.length" class="mb-4">
                  <h4 class="text-subtitle-2 mb-2">Modes of Inheritance</h4>
                  <v-chip
                    v-for="(mode, idx) in item.evidence_data.modes_of_inheritance"
                    :key="idx"
                    size="small"
                    variant="outlined"
                    class="ma-1"
                  >
                    {{ mode }}
                  </v-chip>
                </div>

                <!-- Evidence List -->
                <div v-if="item.evidence_data?.evidence?.length" class="mb-4">
                  <h4 class="text-subtitle-2 mb-2">Supporting Evidence</h4>
                  <v-chip
                    v-for="(ev, idx) in [...new Set(item.evidence_data.evidence)]"
                    :key="idx"
                    size="small"
                    variant="text"
                    class="ma-1"
                  >
                    {{ ev }}
                  </v-chip>
                </div>

                <!-- Metadata -->
                <div class="text-caption text-grey mt-2">
                  Last updated: {{ formatDate(item.evidence_data?.last_updated) }}
                </div>
              </v-expansion-panel-text>
            </v-expansion-panel>
          </v-expansion-panels>
        </v-col>
      </v-row>

      <v-row v-else>
        <v-col cols="12">
          <v-alert type="info" variant="tonal"> No evidence data available for this gene </v-alert>
        </v-col>
      </v-row>
    </template>

    <v-row v-else>
      <v-col cols="12">
        <v-alert type="error" variant="tonal"> Gene not found </v-alert>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { geneApi } from '../api/genes'

const route = useRoute()
const gene = ref(null)
const evidence = ref(null)
const loading = ref(true)
const loadingEvidence = ref(true)

const getSourceColor = source => {
  const colors = {
    PanelApp: 'primary',
    HPO: 'secondary',
    PubTator: 'info',
    Literature: 'success',
    Diagnostic: 'warning'
  }
  return colors[source] || 'grey'
}

const getScoreColor = score => {
  if (score >= 80) return 'success'
  if (score >= 60) return 'warning'
  if (score >= 40) return 'orange'
  return 'error'
}

const formatDate = dateString => {
  if (!dateString) return 'Unknown'
  return new Date(dateString).toLocaleDateString()
}

onMounted(async () => {
  const symbol = route.params.symbol

  try {
    gene.value = await geneApi.getGene(symbol)
  } catch (error) {
    console.error('Error loading gene:', error)
  } finally {
    loading.value = false
  }

  try {
    evidence.value = await geneApi.getGeneEvidence(symbol)
  } catch (error) {
    console.error('Error loading evidence:', error)
  } finally {
    loadingEvidence.value = false
  }
})
</script>
