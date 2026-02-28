/**
 * Log type definitions
 *
 * LogEntry and LogLevel types used by logStore and logService.
 *
 * @module types/log
 */

/** Valid log severity levels */
export type LogLevel = 'DEBUG' | 'INFO' | 'WARN' | 'ERROR' | 'CRITICAL'

/** A single structured log entry stored in the Pinia log store */
export interface LogEntry {
  timestamp: string
  level: LogLevel
  message: string
  data?: unknown
  correlationId?: string | null
  metadata?: Record<string, unknown>
  url?: string
  userAgent?: string
}
