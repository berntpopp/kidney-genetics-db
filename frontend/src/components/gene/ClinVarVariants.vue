<template>
  <div v-if="clinvarData">
    <div class="text-xs text-muted-foreground mb-2">Clinical Variants (ClinVar):</div>

    <div
      v-if="clinvarData.total_variants === 0 || clinvarData.no_data_available"
      class="flex items-center"
    >
      <Badge
        variant="outline"
        class="text-xs"
        :style="{ backgroundColor: '#6b728020', color: '#6b7280' }"
      >
        <Info :size="12" class="mr-1" />
        No variants available
      </Badge>
    </div>

    <div v-else class="flex items-center flex-wrap gap-2">
      <!-- Total variants -->
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger as-child>
            <Badge
              variant="outline"
              class="cursor-help"
              :style="{ backgroundColor: '#0ea5e920', color: '#0ea5e9', borderColor: '#0ea5e940' }"
            >
              {{ clinvarData.total_variants }} total
            </Badge>
          </TooltipTrigger>
          <TooltipContent class="max-w-xs">
            <p class="font-medium text-xs">Total ClinVar Variants</p>
            <p class="text-xs text-muted-foreground">
              All variants submitted to ClinVar for {{ geneSymbol }}
            </p>
            <hr class="my-2 border-border" />
            <div class="text-xs">
              <p class="font-medium mb-1">Review Confidence:</p>
              <div class="flex items-center">
                <ShieldCheck :size="12" class="mr-1 text-green-600 dark:text-green-400" />
                <span class="font-medium">{{ clinvarData.high_confidence_percentage }}%</span>
                <span class="ml-1">with high-quality review</span>
              </div>
              <p class="text-xs mt-1 text-muted-foreground" style="font-size: 0.7rem">
                ({{
                  clinvarData.high_confidence_count ||
                  Math.round(
                    (clinvarData.total_variants * clinvarData.high_confidence_percentage) / 100
                  )
                }}
                of {{ clinvarData.total_variants }} variants)
              </p>
              <p class="text-xs mt-2 text-muted-foreground" style="font-size: 0.7rem">
                High-quality = Expert panel reviewed or<br />
                multiple submitters with no conflicts
              </p>
            </div>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>

      <!-- Pathogenic/Likely pathogenic -->
      <TooltipProvider
        v-if="clinvarData.pathogenic_count + clinvarData.likely_pathogenic_count > 0"
      >
        <Tooltip>
          <TooltipTrigger as-child>
            <Badge
              variant="outline"
              class="cursor-help"
              :style="{ backgroundColor: '#ef444420', color: '#ef4444', borderColor: '#ef444440' }"
            >
              {{ clinvarData.pathogenic_count + clinvarData.likely_pathogenic_count }} P/LP
            </Badge>
          </TooltipTrigger>
          <TooltipContent class="max-w-xs">
            <p class="font-medium text-xs">Pathogenic Variants</p>
            <div class="text-xs text-muted-foreground">
              <p>Pathogenic: {{ clinvarData.pathogenic_count }}</p>
              <p>Likely pathogenic: {{ clinvarData.likely_pathogenic_count }}</p>
              <p class="mt-1">{{ clinvarData.pathogenic_percentage }}% of all variants</p>
              <div v-if="clinvarData.consequence_categories" class="mt-2">
                <hr class="my-1 border-border" />
                <span v-if="clinvarData.consequence_categories.truncating">
                  Truncating: {{ clinvarData.consequence_categories.truncating }}<br />
                </span>
                <span v-if="clinvarData.consequence_categories.missense">
                  Missense: {{ clinvarData.consequence_categories.missense }}
                </span>
              </div>
            </div>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>

      <!-- VUS -->
      <TooltipProvider v-if="clinvarData.vus_count > 0">
        <Tooltip>
          <TooltipTrigger as-child>
            <Badge
              variant="outline"
              class="cursor-help"
              :style="{ backgroundColor: '#f59e0b20', color: '#f59e0b', borderColor: '#f59e0b40' }"
            >
              {{ clinvarData.vus_count }} VUS
            </Badge>
          </TooltipTrigger>
          <TooltipContent class="max-w-xs">
            <p class="font-medium text-xs">Uncertain Significance</p>
            <p class="text-xs text-muted-foreground">
              Variants of uncertain significance requiring further evidence
            </p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>

      <!-- Benign/Likely benign -->
      <TooltipProvider v-if="clinvarData.benign_count + clinvarData.likely_benign_count > 0">
        <Tooltip>
          <TooltipTrigger as-child>
            <Badge
              variant="outline"
              class="cursor-help"
              :style="{ color: '#22c55e', borderColor: '#22c55e40' }"
            >
              {{ clinvarData.benign_count + clinvarData.likely_benign_count }} B/LB
            </Badge>
          </TooltipTrigger>
          <TooltipContent class="max-w-xs">
            <p class="font-medium text-xs">Benign Variants</p>
            <div class="text-xs text-muted-foreground">
              <p>Benign: {{ clinvarData.benign_count }}</p>
              <p>Likely benign: {{ clinvarData.likely_benign_count }}</p>
            </div>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>

      <!-- Molecular consequences -->
      <TooltipProvider v-if="clinvarData.consequence_categories && clinvarData.total_variants > 0">
        <Tooltip>
          <TooltipTrigger as-child>
            <Badge
              variant="outline"
              class="cursor-help"
              :style="{ backgroundColor: '#7c3aed20', color: '#7c3aed', borderColor: '#7c3aed40' }"
            >
              <Dna :size="12" class="mr-1" />
              Consequences
            </Badge>
          </TooltipTrigger>
          <TooltipContent class="max-w-sm">
            <p class="font-medium text-xs mb-2">Molecular Consequences</p>

            <div
              v-if="clinvarData.consequence_categories.truncating > 0"
              class="mb-2 p-2 rounded"
              style="background-color: rgba(255, 82, 82, 0.1)"
            >
              <div class="flex items-center">
                <AlertTriangle :size="14" class="mr-1 text-destructive" />
                <strong class="text-xs"
                  >{{ clinvarData.consequence_categories.truncating }} Truncating</strong
                >
              </div>
              <p class="text-xs text-muted-foreground">
                {{ clinvarData.truncating_percentage }}% of all variants
              </p>
              <p class="text-muted-foreground" style="font-size: 0.7rem">
                (nonsense, frameshift, essential splice sites)
              </p>
            </div>

            <div class="text-xs text-muted-foreground">
              <p v-if="clinvarData.consequence_categories.missense > 0">
                <strong>Missense:</strong> {{ clinvarData.consequence_categories.missense }} ({{
                  clinvarData.missense_percentage
                }}%)
              </p>
              <p v-if="clinvarData.consequence_categories.synonymous > 0">
                <strong>Synonymous:</strong> {{ clinvarData.consequence_categories.synonymous }} ({{
                  clinvarData.synonymous_percentage
                }}%)
              </p>
              <p v-if="clinvarData.consequence_categories.inframe > 0">
                <strong>In-frame:</strong> {{ clinvarData.consequence_categories.inframe }}
              </p>
              <p v-if="clinvarData.consequence_categories.splice_region > 0">
                <strong>Splice region:</strong>
                {{ clinvarData.consequence_categories.splice_region }}
              </p>
            </div>

            <div v-if="clinvarData.top_molecular_consequences?.length" class="mt-2">
              <hr class="my-2 border-border" />
              <p class="text-xs text-muted-foreground">Most common:</p>
              <p
                v-for="(cons, idx) in clinvarData.top_molecular_consequences.slice(0, 3)"
                :key="idx"
                class="text-xs text-muted-foreground"
              >
                &bull; {{ cons.consequence }}: {{ cons.count }}
              </p>
            </div>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    </div>
  </div>
</template>

<script setup>
import { Badge } from '@/components/ui/badge'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { Info, ShieldCheck, Dna, AlertTriangle } from 'lucide-vue-next'

defineProps({
  clinvarData: {
    type: Object,
    default: null
  },
  geneSymbol: {
    type: String,
    required: true
  }
})
</script>
