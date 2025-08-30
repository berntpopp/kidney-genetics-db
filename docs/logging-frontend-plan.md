# Frontend Unified Logging System Implementation Plan

## Executive Summary

This document outlines a comprehensive plan to implement a unified logging system for the kidney-genetics-db frontend application. The system is inspired by the excellent logging architecture in the agde-frontend project but adapted to follow our style guide and specific requirements.

## Current State Analysis

### Problems Identified
- **18 files** with scattered `console.log/error/warn/debug` calls
- **No unified system** for managing log levels or configuration
- **No privacy protection** for sensitive genetic/medical data
- **No structured logging** with consistent formats
- **No UI visibility** for debugging in production
- **No persistence** or export capabilities

### Files Requiring Updates
```
frontend/src/views/admin/AdminAnnotations.vue (multiple console.log)
frontend/src/views/admin/AdminGeneStaging.vue (console.log, console.error)
frontend/src/views/admin/AdminPipeline.vue (console.log, console.error)
frontend/src/views/admin/AdminLogViewer.vue (console.error)
frontend/src/views/admin/AdminCacheManagement.vue (console.log, console.error)
frontend/src/views/GeneDetail.vue (console.error)
frontend/src/components/DataSourceProgress.vue (console.log)
frontend/src/api/auth.js (console.error)
frontend/src/services/websocket.js (console.log, console.error)
frontend/src/views/admin/AdminDashboard.vue (console.log)
frontend/src/views/admin/AdminUserManagement.vue (console.error)
frontend/src/stores/auth.js (console.error)
frontend/src/components/GeneTable.vue (console.error)
frontend/src/components/visualizations/*.vue (console.error)
frontend/src/views/Home.vue (console.error)
frontend/src/views/DataSources.vue (console.log)
```

## Proposed Architecture

### Core Components

#### 1. LogService (`frontend/src/services/logService.js`)
**Purpose**: Centralized singleton service for all logging operations

**Key Features**:
- Log levels: DEBUG, INFO, WARN, ERROR, CRITICAL
- Automatic sanitization of sensitive data
- Performance tracking with timing decorators
- Configurable console echo
- LocalStorage persistence for settings
- Request correlation IDs
- Structured metadata support

**Implementation Details**:
```javascript
// Lines 1-50: Import dependencies and constants
// Lines 51-100: LogLevel enum and configuration
// Lines 101-200: Core LogService class
// Lines 201-300: Private logging methods
// Lines 301-400: Public API methods (debug, info, warn, error, critical)
// Lines 401-450: Configuration management
// Lines 451-500: Export singleton instance
```

#### 2. LogStore (`frontend/src/stores/logStore.js`)
**Purpose**: Reactive Pinia store for log state management

**Key Features**:
- Reactive log entries array
- LogViewer visibility control
- Log filtering and search capabilities
- Statistics and counts
- Efficient memory management with configurable limits
- Export functionality

**Implementation Details**:
```javascript
// Lines 1-30: Imports and store setup
// Lines 31-80: State definitions
// Lines 81-150: Actions for log management
// Lines 151-200: Getters for filtering and statistics
// Lines 201-250: Export and persistence methods
```

#### 3. LogSanitizer (`frontend/src/utils/logSanitizer.js`)
**Purpose**: Privacy protection for sensitive medical/genetic data

**Sensitive Data Patterns to Redact**:
- Patient identifiers (names, DOB, MRN)
- Genetic variants (HGVS notation)
- Medical diagnoses
- Authentication tokens
- API keys
- Email addresses
- Phone numbers

**Implementation Details**:
```javascript
// Lines 1-50: Sensitive key patterns
// Lines 51-100: Regex patterns for values
// Lines 101-200: Recursive sanitization function
// Lines 201-250: Export utilities
```

#### 4. LogViewer Component (`frontend/src/components/admin/LogViewer.vue`)
**Purpose**: Admin UI for viewing and managing logs

**UI Features Following Style Guide**:
- Vuetify Material Design components
- Compact density for data display
- Top-accessible controls (no scrolling required)
- Chip sizes: x-small for metadata, small for categories
- Color coding per log level
- Search and filter capabilities
- Export to JSON functionality
- Memory usage indicators

**Layout Structure**:
```vue
<!-- Lines 1-50: Navigation drawer setup -->
<!-- Lines 51-100: Toolbar with controls -->
<!-- Lines 101-150: Filter controls (search, level, date) -->
<!-- Lines 151-200: Statistics display -->
<!-- Lines 201-400: Log entries list -->
<!-- Lines 401-450: Style definitions -->
```

#### 5. Performance Decorators (`frontend/src/utils/logDecorators.js`)
**Purpose**: Automatic performance monitoring

**Decorators**:
- `@timed_operation` - Track method execution time
- `@api_endpoint` - Monitor API call performance
- `@database_query` - Track data fetching
- `@component_lifecycle` - Monitor Vue lifecycle

## Implementation Strategy

### Phase 1: Core Infrastructure (Priority: HIGH)

#### Step 1.1: Create LogService
**File**: `frontend/src/services/logService.js`
**Actions**:
1. Create new file with LogLevel enum (lines 1-20)
2. Implement LogService class (lines 21-400)
3. Add sanitization integration (lines 401-450)
4. Export singleton instance (lines 451-460)

#### Step 1.2: Create LogStore
**File**: `frontend/src/stores/logStore.js`
**Actions**:
1. Create new Pinia store (lines 1-30)
2. Define reactive state (lines 31-60)
3. Implement actions (lines 61-150)
4. Add getters for filtering (lines 151-200)
5. Export store (lines 201-210)

#### Step 1.3: Create LogSanitizer
**File**: `frontend/src/utils/logSanitizer.js`
**Actions**:
1. Define sensitive patterns for medical data (lines 1-100)
2. Implement sanitization logic (lines 101-300)
3. Add genetic variant detection (lines 301-350)
4. Export utilities (lines 351-360)

### Phase 2: Integration (Priority: HIGH)

#### Step 2.1: Update main.js
**File**: `frontend/src/main.js`
**Changes**:
- Line 15: Import logService and logStore
- Lines 25-30: Initialize logging after Pinia
- Lines 31-35: Configure global availability
- Lines 36-40: Log application startup

#### Step 2.2: Replace Console Calls
**Strategy**: Systematic replacement in all 18 identified files

**Pattern Replacements**:
```javascript
// OLD: console.log('message', data)
// NEW: logService.info('message', data)

// OLD: console.error('error', err)
// NEW: logService.error('error', { error: err })

// OLD: console.warn('warning')
// NEW: logService.warn('warning')

// OLD: console.debug('debug', obj)
// NEW: logService.debug('debug', obj)
```

### Phase 3: UI Components (Priority: MEDIUM)

#### Step 3.1: Create LogViewer Component
**File**: `frontend/src/components/admin/LogViewer.vue`
**Implementation**:
1. Create drawer component (lines 1-50)
2. Add toolbar with controls (lines 51-100)
3. Implement filters (lines 101-200)
4. Display log entries (lines 201-400)
5. Add styling per style guide (lines 401-450)

#### Step 3.2: Add Admin Menu Integration
**File**: `frontend/src/layouts/AdminLayout.vue`
**Changes**:
- Add menu item for Log Viewer
- Add keyboard shortcut (Ctrl+Shift+L)
- Add badge for error count

### Phase 4: Advanced Features (Priority: LOW)

#### Step 4.1: Performance Decorators
**File**: `frontend/src/utils/logDecorators.js`
**Implementation**:
1. Create decorator utilities (lines 1-100)
2. Add to critical components (GeneTable, DataSources)
3. Monitor API calls automatically

#### Step 4.2: Error Boundary Component
**File**: `frontend/src/components/ErrorBoundary.vue`
**Implementation**:
1. Create Vue error boundary (lines 1-100)
2. Log errors automatically
3. Display user-friendly error messages

## Configuration

### Environment Variables
```env
# .env.development
VITE_LOG_LEVEL=DEBUG
VITE_LOG_CONSOLE_ECHO=true
VITE_LOG_MAX_ENTRIES=100

# .env.production
VITE_LOG_LEVEL=WARN
VITE_LOG_CONSOLE_ECHO=false
VITE_LOG_MAX_ENTRIES=50
```

### LocalStorage Keys
```javascript
const LOG_STORAGE_KEYS = {
  MAX_ENTRIES: 'kidney-genetics-log-max-entries',
  LOG_LEVEL: 'kidney-genetics-log-level',
  CONSOLE_ECHO: 'kidney-genetics-console-echo'
}
```

## Privacy & Security Considerations

### Sensitive Data Patterns
```javascript
const GENETIC_PATTERNS = [
  /c\.\d+[ACGT]>[ACGT]/g,  // DNA variants
  /p\.[A-Z][a-z]{2}\d+[A-Z][a-z]{2}/g,  // Protein variants
  /chr\d+:\d+-\d+/g,  // Genomic coordinates
]

const MEDICAL_PATTERNS = [
  'diagnosis', 'symptom', 'phenotype',
  'treatment', 'medication', 'allergy'
]

const PATIENT_PATTERNS = [
  'patient', 'firstname', 'lastname',
  'dob', 'mrn', 'email', 'phone'
]
```

### Redaction Strategy
1. Replace patient names with `[REDACTED_NAME]`
2. Replace genetic variants with `[REDACTED_VARIANT]`
3. Replace medical terms with `[REDACTED_MEDICAL]`
4. Hash IDs for correlation without exposure

## Testing Strategy

### Unit Tests
```javascript
// frontend/tests/unit/logService.test.js
describe('LogService', () => {
  test('sanitizes patient data', () => {})
  test('respects log levels', () => {})
  test('manages memory limits', () => {})
})

// frontend/tests/unit/logSanitizer.test.js
describe('LogSanitizer', () => {
  test('redacts genetic variants', () => {})
  test('protects patient identifiers', () => {})
})
```

### Integration Tests
```javascript
// frontend/tests/integration/logging.test.js
describe('Logging System', () => {
  test('logs appear in UI', () => {})
  test('export functionality works', () => {})
  test('filters work correctly', () => {})
})
```

## Migration Checklist

### Pre-Implementation
- [ ] Review and approve plan
- [ ] Create feature branch `feature/unified-logging-frontend`
- [ ] Set up test environment

### Implementation
- [ ] Create core services (LogService, LogStore, LogSanitizer)
- [ ] Update main.js initialization
- [ ] Replace console calls systematically
- [ ] Create LogViewer component
- [ ] Add admin menu integration
- [ ] Implement decorators
- [ ] Add error boundaries

### Testing
- [ ] Unit test all services
- [ ] Integration test UI components
- [ ] Test sanitization thoroughly
- [ ] Verify performance impact
- [ ] Test export functionality

### Documentation
- [ ] Update README with logging instructions
- [ ] Document configuration options
- [ ] Create troubleshooting guide
- [ ] Add JSDoc comments

### Deployment
- [ ] Test in staging environment
- [ ] Verify production configuration
- [ ] Monitor initial rollout
- [ ] Gather user feedback

## Performance Considerations

### Memory Management
- Default limit: 50 entries in production
- Automatic trimming of old entries
- Efficient array operations (slice, not splice)
- Lazy loading of LogViewer component

### Optimization Techniques
```javascript
// Use computed properties for filtering
const filteredLogs = computed(() => {
  // Memoized filtering logic
})

// Debounce search inputs
const debouncedSearch = debounce(search, 300)

// Virtual scrolling for large log lists
<v-virtual-scroll :items="logs" :item-height="48" />
```

## Success Metrics

### Technical Metrics
- Zero console.* calls in production code
- < 50ms impact on page load time
- 100% sanitization of sensitive data
- < 10MB memory usage for logs

### User Experience Metrics
- Reduced debugging time by 50%
- Increased error detection rate
- Improved production issue resolution
- Enhanced security compliance

## Rollback Plan

If issues arise:
1. Feature flag to disable new logging
2. Fallback to console methods
3. Preserve existing console calls during migration
4. Gradual rollout by component

## Timeline

### Week 1
- Days 1-2: Core infrastructure (LogService, LogStore, LogSanitizer)
- Days 3-4: Integration and console replacement
- Day 5: Testing and refinement

### Week 2
- Days 1-2: LogViewer component
- Days 3-4: Advanced features (decorators, error boundaries)
- Day 5: Documentation and deployment preparation

## Conclusion

This unified logging system will provide:
1. **Centralized control** over all application logging
2. **Privacy protection** for sensitive medical/genetic data
3. **Enhanced debugging** capabilities for developers
4. **Production visibility** for administrators
5. **Performance monitoring** through decorators
6. **Clean, maintainable** code following best practices

The implementation follows our style guide principles of:
- Single path to action (one logging API)
- Information hierarchy (log levels)
- Density optimization (compact UI)
- Professional trust (medical-grade privacy)
- Accessibility first (keyboard shortcuts, visible controls)

By adopting this system, we'll transform our logging from scattered console calls into a robust, enterprise-grade solution suitable for a medical genetics platform.