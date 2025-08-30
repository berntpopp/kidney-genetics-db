/**
 * Log Sanitization Utility for Kidney Genetics Database
 *
 * Provides privacy protection for sensitive medical and genetic data in logs
 * Specifically designed for kidney disease genetic research data
 */

/**
 * Sensitive keys that should be redacted from logs
 * Includes medical, genetic, and patient-specific patterns
 */
const SENSITIVE_KEYS = [
  // Patient identifiers
  'patientname',
  'firstname',
  'lastname',
  'fullname',
  'name',
  'dob',
  'dateofbirth',
  'birthdate',
  'mrn',
  'medicalnumber',
  'medicalrecordnumber',
  'patientid',
  'patient_id',
  'subject_id',
  'email',
  'emailaddress',
  'phone',
  'phonenumber',
  'telephone',
  'address',
  'streetaddress',
  'homeaddress',
  'ssn',
  'socialsecurity',
  'socialsecuritynumber',

  // Authentication and security
  'token',
  'accesstoken',
  'authtoken',
  'jwt',
  'password',
  'passwd',
  'pwd',
  'key',
  'apikey',
  'api_key',
  'secretkey',
  'secret_key',
  'privatekey',
  'private_key',
  'secret',
  'apisecret',
  'api_secret',
  'authorization',
  'bearer',
  'credential',
  'credentials',

  // Medical information
  'diagnosis',
  'diagnoses',
  'condition',
  'conditions',
  'symptom',
  'symptoms',
  'phenotype',
  'phenotypes',
  'medication',
  'medications',
  'prescription',
  'prescriptions',
  'drug',
  'drugs',
  'allergy',
  'allergies',
  'treatment',
  'treatments',
  'procedure',
  'procedures',
  'kidney_disease',
  'renal_disease',
  'nephropathy',
  'dialysis',
  'transplant',

  // Genetic data
  'variant',
  'variants',
  'mutation',
  'mutations',
  'genotype',
  'genotypes',
  'chromosome',
  'chromosomes',
  'dna',
  'rna',
  'hgvs',
  'hgvs_notation',
  'genomic',
  'genomic_position',
  'transcript',
  'transcripts',
  'allele',
  'alleles',
  'nucleotide',
  'amino_acid',
  'protein_change',
  'cdna_change',
  'exon',
  'intron',
  'snp',
  'cnv',
  'deletion',
  'insertion',
  'duplication',
  'frameshift'
]

/**
 * Regex patterns for sensitive values
 */
const SENSITIVE_VALUE_PATTERNS = [
  // Email patterns
  /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/g,

  // Phone patterns (international formats)
  /\b(?:\+?[1-9]\d{0,2}[\s.-]?)?\(?\d{1,4}\)?[\s.-]?\d{1,4}[\s.-]?\d{1,9}\b/g,

  // SSN patterns
  /\b\d{3}-?\d{2}-?\d{4}\b/g,

  // Credit card patterns
  /\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b/g,

  // JWT token patterns
  /\b[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\b/g,

  // API key patterns (common formats)
  /\b[A-Za-z0-9]{32,}\b/g,

  // HGVS notation for genetic variants (DNA)
  /\bc\.\d+[ACGT]>[ACGT]\b/g,
  /\bc\.\d+_\d+del[ACGT]*\b/g,
  /\bc\.\d+_\d+ins[ACGT]+\b/g,
  /\bc\.\d+_\d+dup[ACGT]*\b/g,
  /\bc\.\d+[+-]\d+[ACGT]>[ACGT]\b/g,

  // HGVS notation for genetic variants (Protein)
  /\bp\.[A-Z][a-z]{2}\d+[A-Z][a-z]{2}\b/g,
  /\bp\.[A-Z][a-z]{2}\d+\*/g,
  /\bp\.[A-Z][a-z]{2}\d+fs/g,
  /\bp\.[A-Z][a-z]{2}\d+del/g,
  /\bp\.[A-Z][a-z]{2}\d+_[A-Z][a-z]{2}\d+/g,

  // Genomic coordinates
  /\bchr\d{1,2}:\d+-\d+\b/g,
  /\bchrX:\d+-\d+\b/g,
  /\bchrY:\d+-\d+\b/g,

  // RefSeq identifiers (might contain patient-specific data)
  /\bNM_\d+\.\d+\b/g,
  /\bNP_\d+\.\d+\b/g,
  /\bNG_\d+\.\d+\b/g,

  // Medical Record Numbers (various formats)
  /\b[A-Z]{2,3}\d{6,10}\b/g,
  /\b\d{3}-\d{2}-\d{4}\b/g
]

/**
 * Genetic-specific patterns for kidney disease research
 */
const GENETIC_PATTERNS = {
  // Common kidney disease genes that might appear with patient data
  sensitiveGenes: [
    'PKD1',
    'PKD2',
    'PKHD1',
    'COL4A3',
    'COL4A4',
    'COL4A5',
    'NPHS1',
    'NPHS2',
    'WT1',
    'LAMB2',
    'PLCE1'
  ],

  // Patterns that might reveal patient genetic information
  isGeneticIdentifier: str => {
    const patterns = [
      /^rs\d+$/i, // SNP IDs
      /^g\.\d+/, // Genomic notation
      /^m\.\d+/, // Mitochondrial notation
      /^n\.\d+/ // Non-coding notation
    ]
    return patterns.some(pattern => pattern.test(str))
  }
}

/**
 * Sanitizes an object for logging by redacting sensitive information
 *
 * @param {any} obj - The object to sanitize
 * @param {number} maxDepth - Maximum recursion depth
 * @returns {any} - Sanitized copy of the object
 */
export function sanitizeForLogging(obj, maxDepth = 5) {
  // Handle max depth
  if (maxDepth <= 0) {
    return '[MAX_DEPTH_EXCEEDED]'
  }

  // Handle null/undefined
  if (obj === null || obj === undefined) {
    return obj
  }

  // Handle primitives
  if (typeof obj !== 'object') {
    return sanitizeValue(obj)
  }

  // Handle arrays
  if (Array.isArray(obj)) {
    return obj.map(item => sanitizeForLogging(item, maxDepth - 1))
  }

  // Handle objects
  const sanitized = {}

  for (const [key, value] of Object.entries(obj)) {
    const lowerKey = key.toLowerCase().replace(/[_-]/g, '')

    // Check if key is sensitive
    const isSensitiveKey = SENSITIVE_KEYS.some(sensitiveKey =>
      lowerKey.includes(sensitiveKey.toLowerCase().replace(/[_-]/g, ''))
    )

    // Check if key might contain genetic data
    const isGeneticKey =
      lowerKey.includes('gene') ||
      lowerKey.includes('variant') ||
      lowerKey.includes('mutation') ||
      lowerKey.includes('hgvs') ||
      lowerKey.includes('genomic')

    if (isSensitiveKey) {
      sanitized[key] = '[REDACTED_SENSITIVE]'
    } else if (isGeneticKey && typeof value === 'string') {
      // Special handling for genetic data
      sanitized[key] = sanitizeGeneticValue(value)
    } else if (typeof value === 'object' && value !== null) {
      // Recursively sanitize nested objects
      sanitized[key] = sanitizeForLogging(value, maxDepth - 1)
    } else {
      // Sanitize primitive values
      sanitized[key] = sanitizeValue(value)
    }
  }

  return sanitized
}

/**
 * Sanitizes primitive values by checking against sensitive patterns
 *
 * @param {any} value - The value to sanitize
 * @returns {any} - Sanitized value
 */
function sanitizeValue(value) {
  if (typeof value !== 'string') {
    return value
  }

  let sanitized = value

  // Apply regex patterns to detect and redact sensitive values
  SENSITIVE_VALUE_PATTERNS.forEach(pattern => {
    const matches = sanitized.match(pattern)
    if (matches) {
      matches.forEach(match => {
        // Determine redaction type based on pattern
        if (match.includes('@')) {
          sanitized = sanitized.replace(match, '[REDACTED_EMAIL]')
        } else if (match.startsWith('chr')) {
          sanitized = sanitized.replace(match, '[REDACTED_COORDINATE]')
        } else if (match.startsWith('c.') || match.startsWith('p.')) {
          sanitized = sanitized.replace(match, '[REDACTED_VARIANT]')
        } else if (match.match(/^\d{3}-?\d{2}-?\d{4}$/)) {
          sanitized = sanitized.replace(match, '[REDACTED_SSN]')
        } else if (match.includes('.') && match.split('.').length === 3) {
          sanitized = sanitized.replace(match, '[REDACTED_TOKEN]')
        } else {
          sanitized = sanitized.replace(match, '[REDACTED]')
        }
      })
    }
  })

  return sanitized
}

/**
 * Special sanitization for genetic values
 *
 * @param {string} value - The genetic value to sanitize
 * @returns {string} - Sanitized genetic value
 */
function sanitizeGeneticValue(value) {
  // Check if value contains known sensitive gene names with variants
  for (const gene of GENETIC_PATTERNS.sensitiveGenes) {
    if (
      value.includes(gene) &&
      (value.includes(':') || value.includes('c.') || value.includes('p.'))
    ) {
      return `[REDACTED_${gene}_VARIANT]`
    }
  }

  // Check for genetic identifiers
  if (GENETIC_PATTERNS.isGeneticIdentifier(value)) {
    return '[REDACTED_GENETIC_ID]'
  }

  // Default sanitization
  return sanitizeValue(value)
}

/**
 * Sanitizes log entry message and data
 *
 * @param {string} message - Log message
 * @param {any} data - Optional data object
 * @returns {Object} - Sanitized message and data
 */
export function sanitizeLogEntry(message, data = null) {
  return {
    message: sanitizeValue(message || ''),
    data: data ? sanitizeForLogging(data) : null
  }
}

/**
 * Quick check to determine if a value contains potentially sensitive data
 * Used for performance optimization
 *
 * @param {any} value - Value to check
 * @returns {boolean} - True if value might contain sensitive data
 */
export function containsSensitiveData(value) {
  if (!value) return false

  const str = typeof value === 'string' ? value : JSON.stringify(value)
  const lowerStr = str.toLowerCase()

  // Quick check for common sensitive patterns
  const quickPatterns = [
    'patient',
    'email',
    'phone',
    'password',
    'token',
    'variant',
    'mutation',
    'hgvs',
    'diagnosis',
    'symptom'
  ]

  return (
    quickPatterns.some(pattern => lowerStr.includes(pattern)) ||
    SENSITIVE_VALUE_PATTERNS.some(pattern => pattern.test(str))
  )
}

/**
 * Development helper to add custom sensitive keys
 * Only works in development mode
 *
 * @param {string[]} keys - Additional sensitive keys to add
 */
export function addSensitiveKeys(keys) {
  if (import.meta.env.DEV) {
    SENSITIVE_KEYS.push(...keys.map(k => k.toLowerCase()))
    console.info('Added sensitive keys for development:', keys)
  }
}

/**
 * Get a summary of redacted items for debugging
 * Only available in development mode
 *
 * @param {any} obj - Object to analyze
 * @returns {Object} - Summary of what would be redacted
 */
export function getRedactionSummary(obj) {
  if (!import.meta.env.DEV) {
    return null
  }

  const summary = {
    sensitiveKeys: [],
    redactedValues: [],
    geneticData: []
  }

  const analyze = (item, path = '') => {
    if (!item || typeof item !== 'object') return

    Object.entries(item).forEach(([key, value]) => {
      const fullPath = path ? `${path}.${key}` : key
      const lowerKey = key.toLowerCase().replace(/[_-]/g, '')

      if (SENSITIVE_KEYS.some(sk => lowerKey.includes(sk.toLowerCase().replace(/[_-]/g, '')))) {
        summary.sensitiveKeys.push(fullPath)
      }

      if (typeof value === 'string') {
        SENSITIVE_VALUE_PATTERNS.forEach(pattern => {
          if (pattern.test(value)) {
            summary.redactedValues.push({ path: fullPath, pattern: pattern.toString() })
          }
        })

        if (value.match(/\b[cp]\.\d+/)) {
          summary.geneticData.push({ path: fullPath, type: 'HGVS notation' })
        }
      }

      if (typeof value === 'object' && value !== null) {
        analyze(value, fullPath)
      }
    })
  }

  analyze(obj)
  return summary
}

// Export for testing
export const _testing = {
  SENSITIVE_KEYS,
  SENSITIVE_VALUE_PATTERNS,
  GENETIC_PATTERNS
}
