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
    largeNetworkThreshold: 700 // Show warning when exceeding this threshold
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
    defaultEnrichmentType: 'go', // Default enrichment type (go or hpo)
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
        threshold: 700,
        message: count =>
          `You have selected ${count} genes. Networks with >${networkAnalysisConfig.geneSelection.largeNetworkThreshold} nodes may take longer to build and visualize. Consider filtering to higher evidence tiers for better performance.`
      }
    }
  },

  // Node Coloring Configuration
  nodeColoring: {
    // Available color modes
    modes: [
      { value: 'cluster', label: 'Cluster', description: 'Color nodes by clustering assignment' },
      {
        value: 'clinical_group',
        label: 'Clinical Classification',
        description: 'Color by HPO clinical group'
      },
      { value: 'onset_group', label: 'Age of Onset', description: 'Color by HPO onset group' },
      {
        value: 'syndromic',
        label: 'Syndromic Assessment',
        description: 'Color by syndromic classification'
      }
    ],

    // Default color mode
    defaultMode: 'cluster',

    // Color schemes for HPO-based coloring
    colorSchemes: {
      clinical_group: {
        cyst_cilio: '#009688', // Teal - Cystic/Ciliopathy
        cakut: '#2196F3', // Blue - CAKUT
        glomerulopathy: '#F44336', // Red - Glomerulopathy
        complement: '#9C27B0', // Purple - Complement
        tubulopathy: '#FF9800', // Orange - Tubulopathy
        nephrolithiasis: '#795548', // Brown - Nephrolithiasis
        null: '#9E9E9E' // Grey - No classification
      },
      onset_group: {
        congenital: '#E91E63', // Pink - Congenital
        pediatric: '#FFC107', // Amber - Pediatric
        adult: '#4CAF50', // Green - Adult
        null: '#9E9E9E' // Grey - No classification
      },
      syndromic: {
        true: '#FF5722', // Deep Orange - Syndromic
        false: '#607D8B', // Blue Grey - Isolated
        null: '#9E9E9E' // Grey - Unknown
      }
    },

    // Human-readable labels for color legend
    labels: {
      clinical_group: {
        cyst_cilio: 'Cystic/Ciliopathy',
        cakut: 'CAKUT',
        glomerulopathy: 'Glomerulopathy',
        complement: 'Complement',
        tubulopathy: 'Tubulopathy',
        nephrolithiasis: 'Nephrolithiasis',
        null: 'Not Classified'
      },
      onset_group: {
        congenital: 'Congenital',
        pediatric: 'Pediatric',
        adult: 'Adult',
        null: 'Not Classified'
      },
      syndromic: {
        true: 'Syndromic',
        false: 'Isolated',
        null: 'Unknown'
      }
    }
  }
}

export default networkAnalysisConfig
