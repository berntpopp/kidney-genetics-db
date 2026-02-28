<template>
  <div>
    <div class="flex items-center flex-wrap gap-2 mb-2">
      <span class="font-bold text-base">{{ gene.approved_symbol }}</span>
      <span class="text-muted-foreground">•</span>
      <span>{{ gene.hgnc_id }}</span>
      <template v-if="hgncData?.mane_select">
        <span class="text-muted-foreground">•</span>
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger as-child>
              <span class="font-mono cursor-help">
                {{ hgncData.mane_select.refseq_transcript_id || 'N/A' }}
              </span>
            </TooltipTrigger>
            <TooltipContent class="max-w-xs">
              <p class="font-medium mb-1">MANE Select Transcripts</p>
              <div class="text-xs space-y-0.5">
                <div v-if="hgncData.mane_select.refseq_transcript_id">
                  <span class="text-muted-foreground">RefSeq:</span>
                  <span class="font-mono ml-1">{{
                    hgncData.mane_select.refseq_transcript_id
                  }}</span>
                </div>
                <div v-if="hgncData.mane_select.ensembl_transcript_id">
                  <span class="text-muted-foreground">Ensembl:</span>
                  <span class="font-mono ml-1">{{
                    hgncData.mane_select.ensembl_transcript_id
                  }}</span>
                </div>
              </div>
              <p class="text-xs mt-1 text-muted-foreground">
                Matched Annotation from NCBI and EMBL-EBI
              </p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </template>
    </div>
  </div>
</template>

<script setup>
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'

defineProps({
  gene: {
    type: Object,
    required: true
  },
  hgncData: {
    type: Object,
    default: null
  }
})
</script>
