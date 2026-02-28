/**
 * Wildcard Pattern Matcher
 *
 * Utility for matching strings against wildcard patterns.
 * Supports:
 * - * (asterisk): matches zero or more characters
 * - ? (question mark): matches exactly one character
 *
 * Examples:
 * - "COL*" matches "COL4A1", "COLQ", "COL1A1"
 * - "PKD?" matches "PKD1", "PKD2" but not "PKD10"
 * - "*A1" matches "COL4A1", "NPHS1"
 *
 * @module utils/wildcardMatcher
 */

/** Result of a wildcard pattern validation */
export interface PatternValidationResult {
  isValid: boolean
  error: string | null
}

/**
 * Convert wildcard pattern to regular expression
 *
 * @param pattern - Wildcard pattern (e.g., "COL*", "PKD?")
 * @returns Case-insensitive regular expression
 *
 * @example
 * const regex = wildcardToRegex("COL*")
 * regex.test("COL4A1") // true
 */
export function wildcardToRegex(pattern: string): RegExp {
  if (!pattern) {
    return /.*/i // Match everything if no pattern
  }

  // Escape special regex characters except * and ?
  // Characters that need escaping: . + ^ $ { } ( ) | [ ] \
  const escaped = pattern.replace(/[.+^${}()|[\]\\]/g, '\\$&')

  // Convert wildcards to regex patterns
  const regexPattern = escaped
    .replace(/\*/g, '.*') // * → match zero or more characters
    .replace(/\?/g, '.') // ? → match exactly one character

  // Return case-insensitive regex with anchors (^ and $)
  // Anchors ensure full string match, not partial
  return new RegExp(`^${regexPattern}$`, 'i')
}

/**
 * Test if a value matches a wildcard pattern
 *
 * @param value - Value to test (e.g., "COL4A1")
 * @param pattern - Wildcard pattern (e.g., "COL*")
 * @returns True if value matches pattern
 *
 * @example
 * matchesWildcard("COL4A1", "COL*") // true
 * matchesWildcard("PKD1", "COL*")   // false
 * matchesWildcard("col4a1", "COL*") // true (case-insensitive)
 */
export function matchesWildcard(value: string, pattern: string): boolean {
  if (!value || !pattern) {
    return false
  }

  const regex = wildcardToRegex(pattern)
  return regex.test(value)
}

/**
 * Find all values that match a wildcard pattern
 *
 * @param values - Array of values to search
 * @param pattern - Wildcard pattern
 * @returns Matched values
 *
 * @example
 * const genes = ["COL4A1", "COL4A2", "PKD1", "NPHS1"]
 * findMatches(genes, "COL*") // ["COL4A1", "COL4A2"]
 */
export function findMatches(values: string[], pattern: string): string[] {
  if (!Array.isArray(values) || !pattern) {
    return []
  }

  const regex = wildcardToRegex(pattern)
  return values.filter(value => value && regex.test(value))
}

/**
 * Validate wildcard pattern syntax
 *
 * @param pattern - Pattern to validate
 * @returns Validation result with isValid and error properties
 *
 * @example
 * validatePattern("COL*")     // { isValid: true, error: null }
 * validatePattern("")         // { isValid: false, error: "Pattern cannot be empty" }
 */
export function validatePattern(pattern: string): PatternValidationResult {
  if (!pattern || pattern.trim() === '') {
    return {
      isValid: false,
      error: 'Pattern cannot be empty'
    }
  }

  // Check for potential performance issues with patterns like "***"
  if (/\*{3,}/.test(pattern)) {
    return {
      isValid: false,
      error: 'Too many consecutive wildcards (*)'
    }
  }

  return {
    isValid: true,
    error: null
  }
}
