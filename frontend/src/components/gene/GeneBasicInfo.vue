<template>
  <div class="gene-basic-info">
    <!-- Combined Gene Info & MANE Row -->
    <div class="d-flex align-center flex-wrap ga-2 mb-2">
      <span class="font-weight-bold text-body-1">{{ gene.approved_symbol }}</span>
      <span class="text-medium-emphasis">•</span>
      <span>{{ gene.hgnc_id }}</span>
      <template v-if="hgncData?.mane_select">
        <span class="text-medium-emphasis">•</span>
        <v-tooltip location="bottom">
          <template #activator="{ props }">
            <span class="font-mono" v-bind="props" style="cursor: help">
              {{ hgncData.mane_select.refseq_transcript_id || 'N/A' }}
            </span>
          </template>
          <div class="pa-2">
            <div class="font-weight-medium mb-1">MANE Select Transcripts</div>
            <div class="text-caption">
              <div v-if="hgncData.mane_select.refseq_transcript_id">
                <span class="text-medium-emphasis">RefSeq:</span>
                <span class="font-mono">{{ hgncData.mane_select.refseq_transcript_id }}</span>
              </div>
              <div v-if="hgncData.mane_select.ensembl_transcript_id">
                <span class="text-medium-emphasis">Ensembl:</span>
                <span class="font-mono">{{ hgncData.mane_select.ensembl_transcript_id }}</span>
              </div>
            </div>
            <div class="text-caption mt-1 text-medium-emphasis">
              Matched Annotation from NCBI and EMBL-EBI
            </div>
          </div>
        </v-tooltip>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Gene } from '@/types/gene'

interface Props {
  gene: Gene
  hgncData?: any
}

defineProps<Props>()
</script>