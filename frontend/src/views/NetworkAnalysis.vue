<template>
  <div :class="PAGE_CONTAINER">
    <PageHeader
      title="Network Analysis"
      description="Protein-protein interactions and functional clusters of kidney-disease genes"
    >
      <template #breadcrumb>
        <Breadcrumb>
          <BreadcrumbList>
            <BreadcrumbItem v-for="(crumb, index) in breadcrumbs" :key="index">
              <BreadcrumbLink v-if="!crumb.disabled && crumb.to" as-child>
                <RouterLink :to="crumb.to">{{ crumb.title }}</RouterLink>
              </BreadcrumbLink>
              <BreadcrumbPage v-else>{{ crumb.title }}</BreadcrumbPage>
              <BreadcrumbSeparator v-if="index < breadcrumbs.length - 1" />
            </BreadcrumbItem>
          </BreadcrumbList>
        </Breadcrumb>
      </template>
      <template #actions>
        <Badge v-if="filteredGenes.length > 0" variant="secondary" class="tabular-nums">
          {{ filteredGenes.length }} genes selected
        </Badge>
        <!-- Same network as the graph card: clustering drops clusters below the minimum size -->
        <Badge v-if="displayNetwork" variant="secondary" class="tabular-nums">
          Network: {{ displayNetwork.nodes }} genes &middot; {{ displayNetwork.edges }} interactions
        </Badge>
        <HoverPopover v-if="clusterStats" content-class="w-72 p-3 text-xs leading-relaxed">
          <Badge variant="secondary" class="tabular-nums cursor-help">
            {{ clusterStats.num_clusters }} clusters &middot; Q={{
              clusterStats.modularity.toFixed(3)
            }}
          </Badge>
          <template #content>
            <p>
              <strong>Modularity Q = {{ clusterStats.modularity.toFixed(3) }}</strong>
              measures how much denser the connections within clusters are than expected by chance.
              Values above about 0.3 indicate clear community structure.
            </p>
            <p class="mt-1.5 text-muted-foreground">{{ clusteringSummary }}</p>
          </template>
        </HoverPopover>
      </template>
    </PageHeader>

    <!-- Control Bar -->
    <Card class="mb-3">
      <CardContent class="p-3 overflow-hidden">
        <!-- Row 1: Parameter inputs -->
        <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3 items-end">
          <div class="col-span-2 md:col-span-1 space-y-1 min-w-0">
            <div class="flex items-center gap-1">
              <label for="na-tiers" class="text-xs font-medium text-muted-foreground">
                Evidence Tiers
              </label>
              <HoverPopover :content-class="HELP_CLASS">
                <CircleHelp class="size-3.5 text-muted-foreground" aria-hidden="true" />
                <span class="sr-only">About Evidence Tiers</span>
                <template #content>{{ HELP.tiers }}</template>
              </HoverPopover>
            </div>
            <Popover>
              <PopoverTrigger as-child>
                <Button id="na-tiers" variant="outline" class="w-full justify-start h-9 text-xs">
                  <span v-if="selectedTiers.length === 0" class="text-muted-foreground">
                    Select tiers
                  </span>
                  <span v-else>{{ selectedTiers.length }} of {{ tierOptions.length }} tiers</span>
                </Button>
              </PopoverTrigger>
              <PopoverContent class="w-[260px] p-2">
                <div
                  v-for="opt in tierOptions"
                  :key="opt.value"
                  class="flex items-center space-x-2 py-1.5 px-1"
                >
                  <Checkbox
                    :id="`tier-${opt.value}`"
                    :model-value="selectedTiers.includes(opt.value)"
                    @update:model-value="toggleTier(opt.value, !!$event)"
                  />
                  <Label :for="`tier-${opt.value}`" class="text-sm cursor-pointer">
                    {{ opt.title }}
                  </Label>
                </div>
              </PopoverContent>
            </Popover>
          </div>
          <div class="space-y-1 min-w-0">
            <div class="flex items-center gap-1">
              <label for="na-min-score" class="text-xs font-medium text-muted-foreground">
                Min Score
              </label>
              <HoverPopover :content-class="HELP_CLASS">
                <CircleHelp class="size-3.5 text-muted-foreground" aria-hidden="true" />
                <span class="sr-only">About Min Score</span>
                <template #content>{{ HELP.minScore }}</template>
              </HoverPopover>
            </div>
            <Input
              id="na-min-score"
              v-model.number="minScore"
              type="number"
              min="0"
              max="100"
              class="h-9"
            />
          </div>
          <div class="space-y-1 min-w-0">
            <div class="flex items-center gap-1">
              <label for="na-max-genes" class="text-xs font-medium text-muted-foreground">
                Max Genes
              </label>
              <HoverPopover :content-class="HELP_CLASS">
                <CircleHelp class="size-3.5 text-muted-foreground" aria-hidden="true" />
                <span class="sr-only">About Max Genes</span>
                <template #content>{{ HELP.maxGenes }}</template>
              </HoverPopover>
            </div>
            <Input
              id="na-max-genes"
              v-model.number="maxGenes"
              type="number"
              :min="networkAnalysisConfig.geneSelection.minGenesLimit"
              :max="networkAnalysisConfig.geneSelection.maxGenesHardLimit"
              class="h-9"
            />
          </div>
          <div class="space-y-1 min-w-0">
            <div class="flex items-center gap-1">
              <label for="na-string-score" class="text-xs font-medium text-muted-foreground">
                STRING Score
              </label>
              <HoverPopover :content-class="HELP_CLASS">
                <CircleHelp class="size-3.5 text-muted-foreground" aria-hidden="true" />
                <span class="sr-only">About STRING Score</span>
                <template #content>{{ HELP.stringScore }}</template>
              </HoverPopover>
            </div>
            <Input
              id="na-string-score"
              v-model.number="minStringScore"
              type="number"
              :min="networkAnalysisConfig.networkConstruction.minStringScoreRange.min"
              :max="networkAnalysisConfig.networkConstruction.minStringScoreRange.max"
              :step="networkAnalysisConfig.networkConstruction.minStringScoreRange.step"
              class="h-9"
            />
          </div>
          <div class="space-y-1 min-w-0">
            <div class="flex items-center gap-1">
              <label for="na-algorithm" class="text-xs font-medium text-muted-foreground">
                Clustering Algorithm
              </label>
              <HoverPopover :content-class="HELP_CLASS">
                <CircleHelp class="size-3.5 text-muted-foreground" aria-hidden="true" />
                <span class="sr-only">About Clustering Algorithm</span>
                <template #content>{{ HELP.algorithm }}</template>
              </HoverPopover>
            </div>
            <Select v-model="clusterAlgorithm">
              <SelectTrigger id="na-algorithm" class="h-9 w-full">
                <SelectValue placeholder="Algorithm" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem v-for="opt in algorithmOptions" :key="opt.value" :value="opt.value">
                  {{ opt.title }}
                </SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        <!-- Row 2: Step buttons + utility actions; enrichment controls wrap below as one group -->
        <div class="flex flex-wrap items-end gap-x-2 gap-y-3 mt-3 pt-3 border-t">
          <div class="grid grid-cols-3 gap-2 w-full sm:flex sm:w-auto">
            <!-- Step 1: Filter -->
            <Button
              :variant="stepVariant(1)"
              :disabled="loadingGenes"
              size="sm"
              @click="fetchFilteredGenes"
            >
              <span :class="stepBadgeClass(1)">1</span>
              <Filter class="size-3.5 mr-1 max-sm:hidden" aria-hidden="true" />
              <span v-if="loadingGenes">Loading...</span>
              <span v-else>Filter<span class="max-sm:hidden"> Genes</span></span>
            </Button>

            <!-- Step 2: Build -->
            <Button
              :variant="stepVariant(2)"
              :disabled="filteredGenes.length === 0 || pipelineBusy"
              size="sm"
              @click="buildNetwork"
            >
              <span :class="stepBadgeClass(2)">2</span>
              <NetworkIcon class="size-3.5 mr-1 max-sm:hidden" aria-hidden="true" />
              <span v-if="buildingNetwork">Building...</span>
              <span v-else>Build<span class="max-sm:hidden"> Network</span></span>
            </Button>

            <!-- Step 3: Cluster -->
            <Button
              :variant="stepVariant(3)"
              :disabled="!networkData || pipelineBusy"
              size="sm"
              @click="clusterNetwork"
            >
              <span :class="stepBadgeClass(3)">3</span>
              <ChartScatter class="size-3.5 mr-1 max-sm:hidden" aria-hidden="true" />
              <span v-if="clustering">Clustering...</span>
              <span v-else>Cluster</span>
            </Button>
          </div>

          <!-- Utility actions, right of the step buttons -->
          <TooltipProvider>
            <div class="ml-auto flex gap-1 self-end">
              <Tooltip v-if="filteredGenes.length > 0">
                <TooltipTrigger as-child>
                  <Button
                    variant="ghost"
                    size="icon"
                    class="size-8"
                    :disabled="isEncoding"
                    aria-label="Share this analysis as a link"
                    @click="handleShareNetwork"
                  >
                    <Share2 class="size-3.5" aria-hidden="true" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Share this analysis as a link</TooltipContent>
              </Tooltip>
              <Tooltip v-if="hasAnyState">
                <TooltipTrigger as-child>
                  <Button
                    variant="ghost"
                    size="icon"
                    class="size-8 text-danger hover:text-danger"
                    aria-label="Reset all"
                    @click="resetAll"
                  >
                    <RotateCcw class="size-3.5" aria-hidden="true" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Reset all</TooltipContent>
              </Tooltip>
              <Tooltip>
                <TooltipTrigger as-child>
                  <Button
                    variant="ghost"
                    size="icon"
                    class="size-8"
                    aria-label="Advanced settings"
                    aria-controls="na-advanced"
                    :aria-expanded="showAdvanced"
                    @click="showAdvanced = !showAdvanced"
                  >
                    <SlidersHorizontal class="size-3.5" :class="{ 'text-primary': showAdvanced }" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Advanced settings</TooltipContent>
              </Tooltip>
            </div>
          </TooltipProvider>

          <!-- Step 4: Enrichment (appears after clustering) -->
          <div
            v-if="clusterStats"
            class="grid grid-cols-2 items-end gap-2 w-full sm:flex sm:flex-wrap"
          >
            <div class="col-span-2 space-y-1 min-w-0">
              <div class="flex items-center gap-1">
                <label for="na-clusters" class="text-xs font-medium text-muted-foreground">
                  Clusters to enrich
                </label>
                <HoverPopover :content-class="HELP_CLASS">
                  <CircleHelp class="size-3.5 text-muted-foreground" aria-hidden="true" />
                  <span class="sr-only">About clusters to enrich</span>
                  <template #content>{{ HELP.clusters }}</template>
                </HoverPopover>
              </div>
              <Popover>
                <PopoverTrigger as-child>
                  <Button
                    id="na-clusters"
                    variant="outline"
                    size="sm"
                    class="text-xs w-full sm:w-auto sm:min-w-[140px] sm:max-w-[18rem] justify-start"
                  >
                    <span v-if="selectedClusters.length === 0" class="text-muted-foreground">
                      None selected
                    </span>
                    <span v-else-if="selectedClusters.length === 1" class="truncate">
                      {{ clusterTitle(selectedClusters[0]!) }}
                    </span>
                    <span v-else>
                      {{ selectedClusters.length }} of {{ clusterList.length }} clusters
                    </span>
                  </Button>
                </PopoverTrigger>
                <PopoverContent class="w-[300px] p-2" align="start" side="bottom">
                  <p class="px-1 pb-2 text-xs text-muted-foreground">
                    Genes of the selected clusters are pooled and tested against
                    <template v-if="enrichmentBackground === 'network'">
                      all {{ networkGeneIds.length }} network genes.
                    </template>
                    <template v-else>the background chosen under Background.</template>
                  </p>
                  <div class="max-h-[300px] overflow-y-auto space-y-0.5">
                    <button
                      v-for="cluster in clusterList"
                      :key="cluster.value"
                      type="button"
                      :aria-pressed="selectedClusters.includes(cluster.value)"
                      class="flex w-full items-center space-x-2 py-1.5 px-1 rounded text-left cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                      :class="
                        selectedClusters.includes(cluster.value) ? 'bg-muted' : 'hover:bg-muted/50'
                      "
                      @click="
                        toggleCluster(cluster.value, !selectedClusters.includes(cluster.value))
                      "
                    >
                      <div
                        class="size-4 rounded-sm border flex items-center justify-center flex-shrink-0"
                        :style="{ borderColor: cluster.color }"
                      >
                        <!-- Foreground check: white on grey/olive swatches fell below 3:1 -->
                        <Check
                          v-if="selectedClusters.includes(cluster.value)"
                          class="size-3 text-foreground"
                        />
                      </div>
                      <Circle
                        class="size-3 flex-shrink-0"
                        :style="{ color: cluster.color, fill: cluster.color }"
                      />
                      <span
                        class="text-sm flex-1 min-w-0"
                        :title="cluster.labelTerm ? clusterLabelNote(cluster.labelTerm) : undefined"
                      >
                        {{ cluster.title }}
                        <!-- title tooltips are mouse-only; screen readers get the note here -->
                        <span v-if="cluster.labelTerm" class="sr-only">
                          ({{ clusterLabelNote(cluster.labelTerm) }})
                        </span>
                      </span>
                      <Badge variant="outline" class="text-xs">{{ cluster.size }}</Badge>
                    </button>
                  </div>
                  <p
                    v-if="selectsWholeNetwork"
                    class="px-1 pt-2 text-xs text-muted-foreground"
                    role="status"
                  >
                    Every cluster is selected, so the network is tested against itself and no term
                    can be enriched. Select fewer clusters.
                  </p>
                </PopoverContent>
              </Popover>
            </div>

            <div class="space-y-1 min-w-0">
              <label for="na-enrich-type" class="text-xs font-medium text-muted-foreground">
                Enrichment
              </label>
              <Select v-model="enrichmentType">
                <SelectTrigger id="na-enrich-type" class="h-8 w-full sm:w-44 text-xs">
                  <SelectValue placeholder="Type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem v-for="opt in enrichmentOptions" :key="opt.value" :value="opt.value">
                    {{ opt.title }}
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div class="space-y-1 min-w-0">
              <div class="flex items-center gap-1">
                <label for="na-enrich-bg" class="text-xs font-medium text-muted-foreground">
                  Background
                </label>
                <HoverPopover :content-class="HELP_CLASS">
                  <CircleHelp class="size-3.5 text-muted-foreground" aria-hidden="true" />
                  <span class="sr-only">About the enrichment background</span>
                  <template #content>{{ HELP.background }}</template>
                </HoverPopover>
              </div>
              <Select v-model="enrichmentBackground">
                <SelectTrigger id="na-enrich-bg" class="h-8 w-full sm:w-40 text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="reference">All genes</SelectItem>
                  <SelectItem value="network">Network genes</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <Button
              :variant="stepVariant(4)"
              size="sm"
              class="col-span-2 sm:col-auto"
              :disabled="selectedClusters.length === 0 || runningEnrichment || pipelineBusy"
              @click="runEnrichmentAndSwitch"
            >
              <span :class="stepBadgeClass(4)">4</span>
              <ChartBarBig class="size-3.5 mr-1" aria-hidden="true" />
              <span v-if="runningEnrichment">Running...</span>
              <span v-else>Enrich</span>
            </Button>
          </div>
        </div>

        <!-- What to do next, and why a step is unavailable -->
        <p class="mt-2 text-xs text-muted-foreground" role="status" data-testid="next-step">
          {{ nextStepText }}
        </p>
        <p
          v-if="hiddenGenes"
          class="mt-1 text-xs text-muted-foreground"
          data-testid="hidden-genes-note"
        >
          <span class="tabular-nums">{{ hiddenGenes.hidden }}</span>
          of
          <span class="tabular-nums">{{ hiddenGenes.submitted }}</span>
          genes hidden{{
            hiddenGenes.reasons.length ? `: ${hiddenGenes.reasons.join(', or ')}` : ''
          }}.
          <button
            type="button"
            class="ml-1 font-medium text-foreground underline underline-offset-2 hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-sm"
            @click="showAdvanced = true"
          >
            Adjust filters
          </button>
        </p>

        <!-- Row 3: Advanced settings (collapsible) -->
        <div
          v-if="showAdvanced"
          id="na-advanced"
          class="flex flex-wrap items-end gap-4 mt-3 pt-3 border-t"
        >
          <div class="flex items-center space-x-2">
            <Checkbox
              id="remove-isolated"
              :model-value="removeIsolated"
              @update:model-value="removeIsolated = !!$event"
            />
            <Label for="remove-isolated" class="text-xs cursor-pointer">Remove Isolated</Label>
          </div>
          <div class="flex items-center space-x-2">
            <Checkbox
              id="largest-component"
              :model-value="largestComponentOnly"
              @update:model-value="largestComponentOnly = !!$event"
            />
            <Label for="largest-component" class="text-xs cursor-pointer">
              Largest Component Only
            </Label>
          </div>
          <div class="space-y-1 w-24">
            <div class="flex items-center gap-1">
              <label for="na-min-degree" class="text-xs font-medium text-muted-foreground">
                Min Degree
              </label>
              <HoverPopover :content-class="HELP_CLASS">
                <CircleHelp class="size-3.5 text-muted-foreground" aria-hidden="true" />
                <span class="sr-only">About Min Degree</span>
                <template #content>{{ HELP.minDegree }}</template>
              </HoverPopover>
            </div>
            <Input
              id="na-min-degree"
              v-model.number="minDegree"
              type="number"
              min="0"
              :max="networkAnalysisConfig.filtering.maxMinDegree"
              class="h-8"
            />
          </div>
          <div class="space-y-1 w-24">
            <div class="flex items-center gap-1">
              <label for="na-min-cluster" class="text-xs font-medium text-muted-foreground">
                Min Cluster
              </label>
              <HoverPopover :content-class="HELP_CLASS">
                <CircleHelp class="size-3.5 text-muted-foreground" aria-hidden="true" />
                <span class="sr-only">About Min Cluster</span>
                <template #content>{{ HELP.minCluster }}</template>
              </HoverPopover>
            </div>
            <Input
              id="na-min-cluster"
              v-model.number="minClusterSize"
              type="number"
              min="1"
              :max="networkAnalysisConfig.filtering.maxMinClusterSize"
              class="h-8"
            />
          </div>
          <div class="space-y-1 w-24">
            <div class="flex items-center gap-1">
              <label for="na-fdr" class="text-xs font-medium text-muted-foreground">FDR</label>
              <HoverPopover :content-class="HELP_CLASS">
                <CircleHelp class="size-3.5 text-muted-foreground" aria-hidden="true" />
                <span class="sr-only">About FDR</span>
                <template #content>{{ HELP.fdr }}</template>
              </HoverPopover>
            </div>
            <Input
              id="na-fdr"
              :model-value="fdrThreshold"
              type="number"
              min="0.001"
              max="0.2"
              step="0.01"
              class="h-8"
              @update:model-value="onFdrChange"
            />
          </div>
        </div>
      </CardContent>
    </Card>

    <!-- Main content: Tabs for Network / Enrichment -->
    <Tabs v-model="activeTab">
      <TabsList v-if="displayNetwork" class="mb-3">
        <TabsTrigger value="network">
          <NetworkIcon class="size-4 mr-1.5" />
          Network
        </TabsTrigger>
        <TabsTrigger value="enrichment" :disabled="!clusterStats">
          <ChartBarBig class="size-4 mr-1.5" />
          Enrichment
          <Badge v-if="enrichmentResults" variant="secondary" class="ml-1.5 text-xs px-1.5 py-0">
            {{ visibleEnrichmentTerms.length }}
          </Badge>
        </TabsTrigger>
      </TabsList>

      <TabsContent value="network" class="mt-0">
        <!-- Network Visualization: NetworkGraph re-initialises itself when networkData changes -->
        <div v-if="displayNetwork">
          <NetworkGraph
            v-model:color-mode="nodeColorMode"
            :network-data="displayNetwork"
            :loading="buildingNetwork || clustering"
            :error="networkError ?? undefined"
            :cluster-id-mapping="clusterIdMapping"
            :cluster-colors-map="clusterColors"
            :cluster-labels="clusterLabels"
            :min-cluster-size="clusteredWith?.minClusterSize ?? 1"
            :hpo-classifications="hpoClassifications ?? undefined"
            :hgnc-ids="hgncIds"
            :loading-h-p-o-data="loadingHPOClassifications"
            :height="networkAnalysisConfig.ui.defaultGraphHeight"
            @refresh="buildNetwork"
            @node-click="handleNodeClick"
            @select-cluster="handleClusterSelection"
          />
        </div>

        <!-- Empty state -->
        <Card v-if="!displayNetwork">
          <CardContent class="flex flex-col items-center justify-center py-16 text-center">
            <NetworkIcon class="size-16 text-muted-foreground/30 mb-4" />
            <p class="text-lg font-medium text-muted-foreground">No network loaded</p>
            <p class="text-sm text-muted-foreground mt-1">
              Click
              <strong>Filter Genes</strong>
              then
              <strong>Build Network</strong>
              to create a protein-protein interaction network
            </p>
          </CardContent>
        </Card>
      </TabsContent>

      <TabsContent value="enrichment" class="mt-0">
        <Card v-if="!enrichmentRun">
          <CardContent class="flex flex-col items-center justify-center py-16 text-center">
            <ChartBarBig class="size-16 text-muted-foreground/30 mb-4" />
            <p class="text-lg font-medium text-muted-foreground">No enrichment results</p>
            <p class="text-sm text-muted-foreground mt-1">
              Choose clusters to enrich above and click
              <strong>Enrich</strong>
              to run functional enrichment analysis
            </p>
          </CardContent>
        </Card>

        <template v-else>
          <p class="mb-2 text-xs text-muted-foreground" data-testid="enrichment-background">
            {{ enrichmentRun.clusterLabel }}:
            <span class="tabular-nums">{{ enrichmentRun.geneCount }}</span>
            genes tested &middot; background:
            <template v-if="enrichmentRun.background === 'network'">
              <span class="tabular-nums">{{ enrichmentBackgroundSize }}</span>
              network genes<template v-if="enrichmentRun.type === 'hpo'">
                (only those with kidney HPO annotations are tested)</template
              >
            </template>
            <template v-else-if="enrichmentRun.type === 'hpo'">
              all kidney genes with HPO annotations
            </template>
            <template v-else>whole genome (Enrichr library)</template>
          </p>
          <EnrichmentTable
            :results="visibleEnrichmentTerms"
            :loading="runningEnrichment"
            :error="enrichmentError ?? undefined"
            :enrichment-type="enrichmentType"
            :fdr-threshold="fdrThreshold"
            :gene-set="geneSet"
            :excluded-genes="enrichmentResults?.excluded_genes || []"
            @refresh="runEnrichment"
            @update:enrichment-type="enrichmentType = $event"
            @update:gene-set="geneSet = $event"
            @update:fdr-threshold="onFdrChange"
            @gene-click="handleGeneClick"
          />
        </template>
      </TabsContent>
    </Tabs>

    <!-- Gene Details Dialog -->
    <Dialog v-model:open="geneDialog">
      <DialogContent v-if="selectedGene" class="max-w-lg">
        <DialogHeader>
          <DialogTitle>{{ selectedGene.label }}</DialogTitle>
        </DialogHeader>
        <Separator />
        <div class="space-y-3 py-2">
          <div v-if="hgncIds.get(selectedGene.gene_id)">
            <strong>HGNC:</strong>
            <OntologyTerm :id="hgncIds.get(selectedGene.gene_id)!" :name="selectedGene.label" />
          </div>
          <div v-if="selectedGene.cluster_id !== undefined && selectedGene.cluster_id !== null">
            <strong>Cluster:</strong>
            <Badge
              variant="outline"
              class="ml-1"
              :style="
                tintedChipStyle(clusterColors.get(selectedGene.cluster_id) ?? OTHER_CLUSTER_COLOR)
              "
            >
              {{ clusterTitle(selectedGene.cluster_id) }}
            </Badge>
          </div>
          <Button class="w-full" as-child>
            <router-link :to="`/genes/${selectedGene.label}`">View Gene Details</router-link>
          </Button>
        </div>
        <Separator />
        <DialogFooter>
          <Button variant="ghost" @click="geneDialog = false">Close</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, defineAsyncComponent } from 'vue'
import ComponentSkeleton from '@/components/ui/ComponentSkeleton.vue'
import ComponentError from '@/components/ui/ComponentError.vue'
import HoverPopover from '@/components/ui/HoverPopover.vue'
import {
  ChartBarBig,
  ChartScatter,
  Check,
  Circle,
  CircleHelp,
  Filter,
  Network as NetworkIcon,
  RotateCcw,
  Share2,
  SlidersHorizontal
} from 'lucide-vue-next'
import { toast } from 'vue-sonner'
import { RouterLink, useRouter, useRoute } from 'vue-router'

import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem
} from '@/components/ui/select'
import { Separator } from '@/components/ui/separator'
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter
} from '@/components/ui/dialog'
import { Popover, PopoverTrigger, PopoverContent } from '@/components/ui/popover'
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator
} from '@/components/ui/breadcrumb'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { OntologyTerm, PageHeader, PAGE_CONTAINER } from '@/components/shared'

import { geneApi } from '@/api/genes'
import EnrichmentTable from '@/components/network/EnrichmentTable.vue'
import { networkAnalysisConfig, OTHER_CLUSTER_COLOR } from '@/config/networkAnalysis'
import { tintedChipStyle } from '@/utils/evidenceTiers'
import { PUBLIC_BREADCRUMBS } from '@/utils/publicBreadcrumbs'
import useNetworkUrlState from '@/composables/useNetworkUrlState'
import useNetworkAnalysis, { clusterLabelNote } from '@/composables/useNetworkAnalysis'
import type { NetworkState } from '@/utils/networkStateCodec'
import { useSeoMeta } from '@/composables/useSeoMeta'
import { useJsonLd, getBreadcrumbSchema } from '@/composables/useJsonLd'

const NetworkGraph = defineAsyncComponent({
  loader: () => import('@/components/network/NetworkGraph.vue'),
  loadingComponent: ComponentSkeleton,
  errorComponent: ComponentError,
  delay: 200,
  timeout: 10000
})

/** Node payload emitted by NetworkGraph's nodeClick */
interface SelectedGene {
  label: string
  gene_id: number
  cluster_id?: number | null
}

// Breadcrumbs
const breadcrumbs = PUBLIC_BREADCRUMBS.networkAnalysis

useJsonLd(getBreadcrumbSchema(breadcrumbs))

useSeoMeta({
  title: 'Network Analysis — Kidney Gene Interactions',
  description:
    'Explore protein-protein interaction networks and functional clusters across kidney disease genes using STRING-DB data. Nephrology gene panel network visualization.',
  canonicalPath: '/network-analysis'
})

const HELP_CLASS = 'w-72 p-3 text-xs leading-relaxed'
const HELP = {
  tiers:
    'Only genes in the selected evidence tiers are included. The default keeps the three strongest tiers.',
  minScore: 'Minimum evidence score (0–100). Genes scoring lower are left out.',
  maxGenes: `Maximum number of genes in the network (${networkAnalysisConfig.geneSelection.minGenesLimit}–${networkAnalysisConfig.geneSelection.maxGenesHardLimit}). The highest-scoring genes are kept.`,
  stringScore: `Minimum STRING combined score for an interaction (${networkAnalysisConfig.networkConstruction.minStringScoreRange.min}–1000): 400 medium, 700 high, 900 highest confidence. Interactions come from the STRING physical subnetwork.`,
  algorithm:
    'How genes are grouped into clusters. Leiden (recommended) and Louvain use a fixed seed, so the same network always gives the same clusters; the resolution sets how fine the clusters are. Walktrap groups genes by short random walks.',
  minDegree:
    'Hide genes with fewer interactions than this when the network is built (0 keeps every gene).',
  minCluster: 'After clustering, drop clusters with fewer genes than this (1 keeps every cluster).',
  fdr: 'False discovery rate cut-off for significant terms. Lowering it filters the current results; raising it re-runs the analysis.',
  clusters:
    'Genes of the selected clusters are pooled and tested for enrichment against the chosen background. The largest cluster is selected after clustering.',
  background:
    'All genes: GO terms are tested against the whole genome (Enrichr library) and HPO terms against every kidney gene with HPO annotations; this describes what a cluster does. Network genes: tested against the genes in this network only; this shows what sets a cluster apart from the rest of the network, but has less power on small networks.'
}

// UI State
const showAdvanced = ref(false)
const activeTab = ref('network')
const geneDialog = ref(false)
const selectedGene = ref<SelectedGene | null>(null)

const {
  selectedTiers,
  minScore,
  maxGenes,
  filteredGenes,
  loadingGenes,
  minStringScore,
  clusterAlgorithm,
  removeIsolated,
  minDegree,
  minClusterSize,
  clusteredWith,
  largestComponentOnly,
  buildingNetwork,
  clustering,
  networkData,
  clusterData,
  clusterStats,
  networkError,
  networkGenes,
  builtParams,
  displayNetwork,
  networkGeneIds,
  clusterList,
  clusterIdMapping,
  clusterColors,
  clusterLabels,
  hgncIds,
  hiddenGenes,
  nextStep,
  selectedClusters,
  enrichmentType,
  enrichmentBackground,
  geneSet,
  fdrThreshold,
  runningEnrichment,
  enrichmentResults,
  enrichmentError,
  enrichmentRun,
  visibleEnrichmentTerms,
  hpoClassifications,
  loadingHPOClassifications,
  fetchFilteredGenes,
  buildNetwork,
  clusterNetwork,
  runEnrichment,
  fetchHPOClassifications,
  onFdrChange,
  reset
} = useNetworkAnalysis()

// URL State Management
const router = useRouter()
const route = useRoute()
const isRestoringFromUrl = ref(false)
const { syncStateToUrl, restoreStateFromUrl, copyShareableUrl, isEncoding } = useNetworkUrlState({
  debounceMs: 800
})

// Node Coloring State (config-driven defaults)
const nodeColorMode = ref(networkAnalysisConfig.nodeColoring.defaultMode)

// Options
const tierOptions = [
  { title: 'Comprehensive Support', value: 'comprehensive_support' },
  { title: 'Multi-Source Support', value: 'multi_source_support' },
  { title: 'Established Support', value: 'established_support' },
  { title: 'Preliminary Evidence', value: 'preliminary_evidence' },
  { title: 'Minimal Evidence', value: 'minimal_evidence' }
]

const algorithmOptions = [
  { title: 'Leiden (Recommended)', value: 'leiden' },
  { title: 'Louvain', value: 'louvain' },
  { title: 'Walktrap', value: 'walktrap' }
]

const enrichmentOptions = [
  { title: 'GO (Gene Ontology)', value: 'go' },
  { title: 'HPO (Phenotypes)', value: 'hpo' }
]

// Computed
const hasAnyState = computed(
  () => filteredGenes.value.length > 0 || !!networkData.value || !!clusterData.value
)

const pipelineBusy = computed(() => buildingNetwork.value || clustering.value)

const selectsWholeNetwork = computed(
  () =>
    enrichmentBackground.value === 'network' &&
    clusterList.value.length > 1 &&
    selectedClusters.value.length === clusterList.value.length
)

const clusteringSummary = computed(() => {
  const stats = clusterStats.value
  if (!stats) return ''
  const name =
    algorithmOptions.find(o => o.value === stats.algorithm)?.title.replace(' (Recommended)', '') ??
    stats.algorithm ??
    'unknown'
  const parts = [`Algorithm: ${name}`]
  if (stats.resolution != null) parts.push(`resolution ${stats.resolution}`)
  if (stats.modularityResolution != null)
    parts.push(`Q computed at resolution ${stats.modularityResolution}`)
  return parts.join(' · ')
})

const enrichmentBackgroundSize = computed(() => enrichmentRun.value?.backgroundSize ?? 0)

const nextStepText = computed(() => {
  switch (nextStep.value) {
    case 1:
      return 'Step 1: choose evidence tiers and a minimum score, then click Filter Genes.'
    case 2:
      return networkData.value
        ? 'Gene selection or network settings changed. Click Build Network to apply them.'
        : `Next: click Build Network to connect the ${filteredGenes.value.length} selected genes.`
    case 3:
      return clusterData.value
        ? 'Clustering settings changed. Click Cluster to apply them.'
        : 'Next: click Cluster to find functional modules in the network.'
    case 4:
      return selectedClusters.value.length === 0
        ? 'Next: choose clusters to enrich, then click Enrich.'
        : 'Next: click Enrich to test the selected clusters for GO or HPO terms.'
    default:
      return 'Analysis is up to date. Change any setting to run a step again.'
  }
})

const stepVariant = (step: number) => (nextStep.value === step ? 'default' : 'outline')
const stepBadgeClass = (step: number) => [
  'inline-flex items-center justify-center size-5 rounded-full text-xs font-bold mr-1.5',
  nextStep.value === step ? 'bg-primary-foreground text-primary' : 'bg-muted text-foreground'
]

const clusterTitle = (backendId: number) =>
  clusterList.value.find(c => c.backendId === backendId)?.title ?? `Cluster ${backendId + 1}`

// Utility Functions
const toggleTier = (tier: string, checked: boolean) => {
  if (checked) {
    if (!selectedTiers.value.includes(tier)) {
      selectedTiers.value = [...selectedTiers.value, tier]
    }
  } else {
    selectedTiers.value = selectedTiers.value.filter(t => t !== tier)
  }
}

const toggleCluster = (clusterId: number, checked: boolean) => {
  if (checked) {
    if (!selectedClusters.value.includes(clusterId)) {
      selectedClusters.value = [...selectedClusters.value, clusterId]
    }
  } else {
    selectedClusters.value = selectedClusters.value.filter(c => c !== clusterId)
  }
}

const resetAll = () => {
  reset()
  activeTab.value = 'network'
  nodeColorMode.value = networkAnalysisConfig.nodeColoring.defaultMode
  router.replace({ path: route.path })
}

const runEnrichmentAndSwitch = async () => {
  await runEnrichment()
  if (enrichmentResults.value) {
    activeTab.value = 'enrichment'
  }
}

const handleNodeClick = (nodeData: SelectedGene) => {
  selectedGene.value = nodeData
  geneDialog.value = true
}

const handleClusterSelection = (clusterId: number) => toggleCluster(clusterId, true)

const handleGeneClick = (geneSymbol: string) => {
  router.push(`/genes/${geneSymbol}`)
}

// URL state describes the network on screen: the genes and parameters it was built from
const getStateSnapshot = (): NetworkState => {
  const built = builtParams.value
  const genes = networkGenes.value.length ? networkGenes.value : filteredGenes.value
  return {
    geneIds: genes.map(g => Number(g.id)),
    selectedTiers: selectedTiers.value,
    minScore: minScore.value,
    maxGenes: maxGenes.value,
    minStringScore: built?.min_string_score ?? minStringScore.value,
    clusterAlgorithm: clusterStats.value?.algorithm ?? clusterAlgorithm.value,
    removeIsolated: built?.remove_isolated ?? removeIsolated.value,
    minDegree: built?.min_degree ?? minDegree.value,
    minClusterSize: minClusterSize.value,
    largestComponentOnly: built?.largest_component_only ?? largestComponentOnly.value,
    nodeColorMode: nodeColorMode.value,
    enrichmentType: enrichmentType.value,
    enrichmentBackground: enrichmentBackground.value,
    fdrThreshold: fdrThreshold.value,
    selectedClusters: selectedClusters.value,
    highlightedCluster: null,
    isClustered: !!clusterStats.value
  }
}

const applyRestoredState = async (urlState: NetworkState) => {
  isRestoringFromUrl.value = true
  try {
    if (urlState.selectedTiers) selectedTiers.value = urlState.selectedTiers
    if (urlState.minScore !== undefined) minScore.value = urlState.minScore
    if (urlState.maxGenes !== undefined) maxGenes.value = urlState.maxGenes
    if (urlState.minStringScore !== undefined) minStringScore.value = urlState.minStringScore
    if (urlState.clusterAlgorithm) clusterAlgorithm.value = urlState.clusterAlgorithm
    if (urlState.removeIsolated !== undefined) removeIsolated.value = urlState.removeIsolated
    if (urlState.minDegree !== undefined) minDegree.value = urlState.minDegree
    if (urlState.minClusterSize !== undefined) minClusterSize.value = urlState.minClusterSize
    if (urlState.largestComponentOnly !== undefined)
      largestComponentOnly.value = urlState.largestComponentOnly
    if (urlState.nodeColorMode) nodeColorMode.value = urlState.nodeColorMode
    if (urlState.enrichmentType) enrichmentType.value = urlState.enrichmentType
    if (urlState.enrichmentBackground === 'network') enrichmentBackground.value = 'network'
    if (urlState.fdrThreshold !== undefined) fdrThreshold.value = urlState.fdrThreshold

    if (urlState.geneIds && urlState.geneIds.length > 0) {
      loadingGenes.value = true
      try {
        const response = await geneApi.getGenesByIds(urlState.geneIds)
        filteredGenes.value = response.items
      } finally {
        loadingGenes.value = false
      }
      await buildNetwork()
      if (urlState.isClustered && networkData.value) {
        await clusterNetwork()
        // Clustering selects the largest cluster; the link's selection wins when it still exists
        const known = new Set(clusterList.value.map(c => c.value))
        const restored = (urlState.selectedClusters ?? []).filter(id => known.has(id))
        if (restored.length) selectedClusters.value = restored
      }
    }
  } catch (error) {
    window.logService?.error('[NetworkAnalysis] Failed to apply restored state:', error)
    toast.error(`Could not restore the shared analysis: ${(error as Error).message}`, {
      duration: Infinity
    })
  } finally {
    isRestoringFromUrl.value = false
  }
}

const handleShareNetwork = async () => {
  await copyShareableUrl(getStateSnapshot())
}

// Lifecycle
onMounted(async () => {
  await router.isReady()
  const hasUrlState = !!(route.query.v && (route.query.c || route.query.genes))
  if (hasUrlState) {
    const urlState = restoreStateFromUrl()
    if (urlState) await applyRestoredState(urlState)
  }
})

// Watchers
watch(nodeColorMode, async () => {
  if (networkData.value && !hpoClassifications.value) {
    await fetchHPOClassifications()
  }
})

watch(
  getStateSnapshot,
  state => {
    if (isRestoringFromUrl.value) return
    if (state.geneIds && state.geneIds.length > 0) {
      syncStateToUrl(state)
    }
  },
  { deep: true }
)
</script>
