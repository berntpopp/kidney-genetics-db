/**
 * Network Analysis Configuration
 *
 * Centralized configuration for network analysis parameters.
 * These values control gene selection, network construction, and visualization behavior.
 */

export const networkAnalysisConfig = {
  // Gene Selection Parameters
  geneSelection: {
    defaultMinScore: 20, // Minimum evidence score for gene inclusion
    defaultMaxGenes: 700, // Maximum genes to include in network
    maxGenesHardLimit: 700, // Hard limit for gene count (cannot exceed)
    minGenesLimit: 10, // Minimum genes required
    largeNetworkThreshold: 500 // Show warning when exceeding this threshold
  },

  // Network Construction Parameters
  networkConstruction: {
    defaultMinStringScore: 400, // Default STRING confidence score (0-1000)
    minStringScoreRange: {
      min: 0,
      max: 1000,
      step: 50
    },
    defaultClusteringAlgorithm: 'leiden' // Default clustering algorithm
  },

  // Network Filtering Parameters
  filtering: {
    defaultRemoveIsolated: false, // Remove isolated nodes by default
    defaultMinDegree: 2, // Default minimum node degree
    defaultMinClusterSize: 3, // Default minimum cluster size
    defaultLargestComponentOnly: false // Keep only largest component
  },

  // Enrichment Analysis Parameters
  enrichment: {
    defaultEnrichmentType: 'hpo', // Default enrichment type (hpo or go)
    defaultFdrThreshold: 0.05, // Default FDR significance threshold
    hpoGeneSet: 'HPO (Phenotypes)',
    goGeneSets: [
      'GO_Biological_Process_2023',
      'GO_Molecular_Function_2023',
      'GO_Cellular_Component_2023'
    ]
  },

  // UI Configuration
  ui: {
    defaultGraphHeight: '700px', // Default height for network visualization
    warningMessages: {
      largeNetwork: {
        title: 'Large Network Warning',
        threshold: 500,
        message: count =>
          `You have selected ${count} genes. Networks with >${networkAnalysisConfig.geneSelection.largeNetworkThreshold} nodes may take longer to build and visualize. Consider filtering to higher evidence tiers for better performance.`
      }
    }
  }
}

export default networkAnalysisConfig
