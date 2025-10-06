/**
 * Unified Logging Service for Kidney Genetics Database
 *
 * Provides centralized logging with privacy protection for medical/genetic data
 * Inspired by agde-frontend but adapted for kidney-genetics-db requirements
 */

import { sanitizeLogEntry } from '@/utils/logSanitizer'

/**
 * Log levels enum
 */
export const LogLevel = {
  DEBUG: 'DEBUG',
  INFO: 'INFO',
  WARN: 'WARN',
  ERROR: 'ERROR',
  CRITICAL: 'CRITICAL'
}

/**
 * Log level priority mapping for filtering
 */
const LOG_LEVEL_PRIORITY = {
  [LogLevel.DEBUG]: 0,
  [LogLevel.INFO]: 1,
  [LogLevel.WARN]: 2,
  [LogLevel.ERROR]: 3,
  [LogLevel.CRITICAL]: 4
}

/**
 * LocalStorage keys for configuration persistence
 */
const STORAGE_KEYS = {
  MAX_ENTRIES: 'kidney-genetics-log-max-entries',
  LOG_LEVEL: 'kidney-genetics-log-level',
  CONSOLE_ECHO: 'kidney-genetics-console-echo'
}

/**
 * LogService - Singleton service for centralized logging
 *
 * Features:
 * - Automatic sanitization of sensitive medical/genetic data
 * - Configurable log levels
 * - LocalStorage persistence for settings
 * - Optional console echo for development
 * - Request correlation IDs
 * - Performance tracking capabilities
 */
class LogService {
  constructor() {
    this.store = null
    this.consoleEcho = this.loadConsoleEchoFromStorage()
    this.maxEntries = this.loadMaxEntriesFromStorage()
    this.minLogLevel = this.loadLogLevelFromStorage()
    this.correlationId = null
    this.metadata = {}
  }

  /**
   * Initialize the log store (called after Pinia is available)
   * @param {Object} store - The Pinia log store
   */
  initStore(store) {
    this.store = store
  }

  /**
   * Set request correlation ID for tracking related logs
   * @param {string} id - Correlation ID
   */
  setCorrelationId(id) {
    this.correlationId = id
  }

  /**
   * Clear correlation ID
   */
  clearCorrelationId() {
    this.correlationId = null
  }

  /**
   * Set global metadata for all logs
   * @param {Object} metadata - Metadata to include in all logs
   */
  setMetadata(metadata) {
    this.metadata = { ...this.metadata, ...metadata }
  }

  /**
   * Clear global metadata
   */
  clearMetadata() {
    this.metadata = {}
  }

  /**
   * Core logging method
   * @private
   * @param {string} level - Log level
   * @param {string} message - Log message
   * @param {any} data - Optional data to log
   */
  _log(level, message, data = null) {
    // Check if log level meets minimum threshold
    if (LOG_LEVEL_PRIORITY[level] < LOG_LEVEL_PRIORITY[this.minLogLevel]) {
      return
    }

    // Sanitize the log entry to protect sensitive data
    const sanitized = sanitizeLogEntry(message, data)

    // Create log entry
    const entry = {
      timestamp: new Date().toISOString(),
      level,
      message: sanitized.message,
      data: sanitized.data,
      correlationId: this.correlationId,
      metadata: this.metadata,
      url: window.location.href,
      userAgent: navigator.userAgent
    }

    // Echo to console if enabled (development)
    if (this.consoleEcho) {
      this._consoleEcho(level, message, data)
    }

    // Add to store if available
    if (this.store) {
      try {
        this.store.addLogEntry(entry, this.maxEntries)
      } catch (error) {
        // Fallback to console if store fails
        console.error('Failed to add log to store:', error)
      }
    }
  }

  /**
   * Echo log to console with appropriate method
   * @private
   */
  _consoleEcho(level, message, data) {
    const prefix = `[${level}]`
    const args = data ? [prefix, message, data] : [prefix, message]

    switch (level) {
      case LogLevel.DEBUG:
        console.debug(...args)
        break
      case LogLevel.INFO:
        console.info(...args)
        break
      case LogLevel.WARN:
        console.warn(...args)
        break
      case LogLevel.ERROR:
      case LogLevel.CRITICAL:
        console.error(...args)
        break
      default:
        console.log(...args)
    }
  }

  /**
   * Public logging methods
   */
  debug(message, data = null) {
    this._log(LogLevel.DEBUG, message, data)
  }

  info(message, data = null) {
    this._log(LogLevel.INFO, message, data)
  }

  warn(message, data = null) {
    this._log(LogLevel.WARN, message, data)
  }

  error(message, data = null) {
    this._log(LogLevel.ERROR, message, data)
  }

  critical(message, data = null) {
    this._log(LogLevel.CRITICAL, message, data)
  }

  /**
   * Performance tracking helper
   * @param {string} operation - Operation name
   * @param {number} startTime - Start timestamp from performance.now()
   * @param {Object} data - Additional data
   */
  logPerformance(operation, startTime, data = null) {
    const duration = window.performance.now() - startTime
    const level = duration > 1000 ? LogLevel.WARN : LogLevel.DEBUG

    this._log(level, `Performance: ${operation}`, {
      ...data,
      duration_ms: Math.round(duration),
      slow: duration > 1000
    })
  }

  /**
   * Log API call
   * @param {string} method - HTTP method
   * @param {string} url - API endpoint
   * @param {number} status - Response status
   * @param {number} duration - Duration in ms
   */
  logApiCall(method, url, status, duration) {
    const level = status >= 400 ? LogLevel.ERROR : LogLevel.DEBUG
    this._log(level, `API ${method} ${url}`, {
      status,
      duration_ms: duration,
      success: status < 400
    })
  }

  /**
   * Configuration methods
   */
  setConsoleEcho(enabled) {
    this.consoleEcho = enabled
    localStorage.setItem(STORAGE_KEYS.CONSOLE_ECHO, JSON.stringify(enabled))
  }

  setMaxEntries(maxEntries) {
    this.maxEntries = maxEntries
    localStorage.setItem(STORAGE_KEYS.MAX_ENTRIES, maxEntries.toString())

    // Trim existing logs if needed
    if (this.store) {
      this.store.trimLogs(maxEntries)
    }
  }

  setMinLogLevel(level) {
    if (LOG_LEVEL_PRIORITY[level] !== undefined) {
      this.minLogLevel = level
      localStorage.setItem(STORAGE_KEYS.LOG_LEVEL, level)
    }
  }

  /**
   * Storage loading methods
   * @private
   */
  loadConsoleEchoFromStorage() {
    try {
      const stored = localStorage.getItem(STORAGE_KEYS.CONSOLE_ECHO)
      if (stored !== null) {
        return JSON.parse(stored)
      }
    } catch (error) {
      console.error('Failed to load console echo setting:', error)
    }
    // Default: true in development, false in production
    return import.meta.env.DEV
  }

  loadMaxEntriesFromStorage() {
    try {
      const stored = localStorage.getItem(STORAGE_KEYS.MAX_ENTRIES)
      if (stored !== null) {
        const parsed = parseInt(stored, 10)
        if (!isNaN(parsed) && parsed > 0) {
          return parsed
        }
      }
    } catch (error) {
      console.error('Failed to load max entries setting:', error)
    }
    // Default: 100 in development, 50 in production
    return import.meta.env.DEV ? 100 : 50
  }

  loadLogLevelFromStorage() {
    try {
      const stored = localStorage.getItem(STORAGE_KEYS.LOG_LEVEL)
      if (stored && LOG_LEVEL_PRIORITY[stored] !== undefined) {
        return stored
      }
    } catch (error) {
      console.error('Failed to load log level setting:', error)
    }
    // Default: DEBUG in development, WARN in production
    return import.meta.env.DEV ? LogLevel.DEBUG : LogLevel.WARN
  }

  /**
   * Clear all logs
   */
  clearLogs() {
    if (this.store) {
      this.store.clearLogs()
    }
  }

  /**
   * Export logs as JSON
   * @returns {Object} Exported logs data
   */
  exportLogs() {
    if (!this.store) {
      return { logs: [], exportedAt: new Date().toISOString() }
    }

    return {
      exportedAt: new Date().toISOString(),
      environment: import.meta.env.MODE,
      url: window.location.href,
      userAgent: navigator.userAgent,
      configuration: {
        maxEntries: this.maxEntries,
        minLogLevel: this.minLogLevel,
        consoleEcho: this.consoleEcho
      },
      logs: this.store.logs
    }
  }
}

// Create and export singleton instance
export const logService = new LogService()

// Also export as default for convenience
export default logService
