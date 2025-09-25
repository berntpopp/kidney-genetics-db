# Frontend Admin Panel Implementation Plan

## Overview
Implement a comprehensive admin panel system for the Kidney Genetics Database following Material Design 3 principles, Vue 3 Composition API best practices, and our established style guide. The implementation will be modular, minimal, and focused on functionality over decoration.

## Architecture Principles
- **Single Responsibility**: Each admin module handles one domain (users, cache, logs, etc.)
- **Composition API**: Use `<script setup>` syntax throughout
- **State Management**: Centralized Pinia stores for each admin domain
- **Compact Density**: Data-heavy interfaces with x-small/small component sizing
- **Single Primary Action**: One clear action per view/section
- **Progressive Disclosure**: Details accessible but not prominent

## File Structure

```
frontend/src/
├── views/admin/
│   ├── AdminDashboard.vue          # Main admin hub (NEW)
│   ├── AdminUserManagement.vue     # User CRUD operations (NEW)
│   ├── AdminCacheManagement.vue    # Cache monitoring & control (NEW)
│   ├── AdminLogViewer.vue          # System logs interface (NEW)
│   ├── AdminPipeline.vue           # Data pipeline control (NEW)
│   ├── AdminAnnotations.vue        # Annotation management (NEW)
│   └── AdminGeneStaging.vue        # Gene normalization review (NEW)
├── components/admin/
│   ├── AdminHeader.vue             # Consistent admin header (NEW)
│   ├── AdminStatsCard.vue          # Reusable stats display (NEW)
│   ├── UserTable.vue               # User management table (NEW)
│   ├── CacheMetrics.vue            # Cache performance charts (NEW)
│   ├── LogTable.vue                # Log viewer table (NEW)
│   ├── PipelineStatus.vue          # Pipeline status cards (NEW)
│   └── StagingReview.vue           # Gene staging review card (NEW)
├── stores/admin/
│   ├── adminUsers.js               # User management store (NEW)
│   ├── adminCache.js               # Cache management store (NEW)
│   ├── adminLogs.js                # Log management store (NEW)
│   ├── adminPipeline.js            # Pipeline control store (NEW)
│   └── adminStaging.js             # Gene staging store (NEW)
├── api/admin/
│   ├── users.js                    # User API client (NEW)
│   ├── cache.js                    # Cache API client (NEW)
│   ├── logs.js                     # Logs API client (NEW)
│   ├── pipeline.js                 # Pipeline API client (NEW)
│   └── staging.js                  # Staging API client (NEW)
└── router/
    └── index.js                     # Add admin routes (MODIFY - lines 50-58)
```

## Implementation Details

### 1. Admin Dashboard (`views/admin/AdminDashboard.vue`)
**Purpose**: Central hub for all admin functions with card-based navigation

```vue
<template>
  <v-container fluid class="pa-4">
    <!-- Admin Header -->
    <AdminHeader 
      title="Admin Dashboard" 
      subtitle="System administration and management"
    />
    
    <!-- Stats Overview -->
    <v-row class="mb-4">
      <v-col cols="12" md="3">
        <AdminStatsCard
          title="Active Users"
          :value="stats.activeUsers"
          icon="mdi-account-check"
          color="success"
        />
      </v-col>
      <v-col cols="12" md="3">
        <AdminStatsCard
          title="Cache Hit Rate"
          :value="`${stats.cacheHitRate}%`"
          icon="mdi-speedometer"
          color="info"
        />
      </v-col>
      <v-col cols="12" md="3">
        <AdminStatsCard
          title="Pipeline Jobs"
          :value="stats.pipelineJobs"
          icon="mdi-pipe"
          color="warning"
        />
      </v-col>
      <v-col cols="12" md="3">
        <AdminStatsCard
          title="Pending Staging"
          :value="stats.pendingStaging"
          icon="mdi-clock-alert"
          color="error"
        />
      </v-col>
    </v-row>
    
    <!-- Admin Function Cards -->
    <v-row>
      <v-col cols="12" lg="4" md="6" v-for="section in adminSections" :key="section.id">
        <v-card 
          @click="navigateTo(section.route)"
          hover
          class="pa-4"
        >
          <div class="d-flex align-center mb-3">
            <v-icon :icon="section.icon" size="x-large" :color="section.color" />
            <div class="ml-4">
              <h3 class="text-h6">{{ section.title }}</h3>
              <p class="text-caption text-medium-emphasis">{{ section.description }}</p>
            </div>
          </div>
          <v-divider class="my-3" />
          <div class="text-body-2">
            <div v-for="feature in section.features" :key="feature" class="d-flex align-center mb-1">
              <v-icon icon="mdi-check" size="small" color="success" class="mr-2" />
              {{ feature }}
            </div>
          </div>
          <v-btn
            :color="section.color"
            variant="tonal"
            size="small"
            class="mt-3"
          >
            Manage
            <v-icon icon="mdi-arrow-right" end />
          </v-btn>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
// Lines 90-140: Setup logic with stats fetching and navigation
</script>
```

### 2. User Management (`views/admin/AdminUserManagement.vue`)
**Purpose**: Full CRUD operations for user accounts with role management

```vue
<template>
  <v-container fluid class="pa-4">
    <AdminHeader 
      title="User Management" 
      subtitle="Manage user accounts, roles, and permissions"
      :back-route="'/admin'"
    />
    
    <!-- Actions Bar -->
    <v-row class="mb-4">
      <v-col cols="12" md="6">
        <v-text-field
          v-model="search"
          prepend-inner-icon="mdi-magnify"
          label="Search users by name, email, or username"
          density="compact"
          variant="outlined"
          clearable
        />
      </v-col>
      <v-col cols="12" md="6" class="text-right">
        <v-btn
          color="primary"
          @click="showCreateDialog = true"
          prepend-icon="mdi-account-plus"
          size="small"
        >
          Add User
        </v-btn>
      </v-col>
    </v-row>
    
    <!-- User Table -->
    <UserTable
      :users="filteredUsers"
      :loading="loading"
      @edit="editUser"
      @delete="deleteUser"
      @toggle-status="toggleUserStatus"
      @toggle-verified="toggleUserVerified"
    />
    
    <!-- Create/Edit Dialog -->
    <v-dialog v-model="showCreateDialog" max-width="600">
      <!-- Lines 45-120: User form with validation -->
    </v-dialog>
  </v-container>
</template>

<script setup>
// Lines 125-200: User management logic with API calls
// Handles UserResponse interface with full_name, permissions, is_verified fields
</script>
```

### 3. Cache Management (`views/admin/AdminCacheManagement.vue`)
**Purpose**: Monitor and control cache performance

Key Features:
- Real-time cache metrics display
- Namespace-specific cache clearing
- Cache warming functionality
- Performance monitoring charts
- Health status indicators

**Lines to implement**: 
- Template: Lines 1-150
- Script: Lines 151-250

### 4. Log Viewer (`views/admin/AdminLogViewer.vue`)
**Purpose**: System log browsing and analysis

Key Features:
- Filterable log table with severity levels
- Date range selection
- Log statistics dashboard
- Export functionality
- Real-time log streaming option

**Lines to implement**:
- Template: Lines 1-180
- Script: Lines 181-280

### 5. Pipeline Control (`views/admin/AdminPipeline.vue`)
**Purpose**: Data pipeline management and monitoring

Key Features:
- Source status cards with real-time WebSocket updates
- Manual trigger controls for each data source
- Progress monitoring with percentage display
- Schedule management for automated runs
- Error recovery actions
- Event-driven updates (no polling needed)

**Lines to implement**:
- Template: Lines 1-160
- Script: Lines 161-260
- WebSocket connection management: Lines 261-300

### 6. Gene Staging (`views/admin/AdminGeneStaging.vue`)
**Purpose**: Review and approve gene normalization attempts

Key Features:
- Pending normalizations table
- Approve/reject actions
- Normalization statistics
- Bulk operations
- History view

**Lines to implement**:
- Template: Lines 1-140
- Script: Lines 141-240

## Component Specifications

### AdminHeader Component (`components/admin/AdminHeader.vue`)
**Lines 1-40**: Reusable header with back navigation
```vue
<template>
  <div class="mb-6">
    <div class="d-flex align-center">
      <v-btn
        v-if="backRoute"
        icon="mdi-arrow-left"
        variant="text"
        @click="$router.push(backRoute)"
        class="mr-3"
      />
      <div>
        <h1 class="text-h4 font-weight-medium">{{ title }}</h1>
        <p class="text-body-2 text-medium-emphasis">{{ subtitle }}</p>
      </div>
    </div>
  </div>
</template>
```

### AdminStatsCard Component (`components/admin/AdminStatsCard.vue`)
**Lines 1-35**: Compact stats display card
```vue
<template>
  <v-card class="pa-3">
    <div class="d-flex align-center justify-space-between">
      <div>
        <p class="text-caption text-medium-emphasis mb-1">{{ title }}</p>
        <p class="text-h5 font-weight-medium">{{ value }}</p>
      </div>
      <v-icon :icon="icon" :color="color" size="large" />
    </div>
  </v-card>
</template>
```

## Pinia Store Structure

### Admin Users Store (`stores/admin/adminUsers.js`)
**Lines 1-120**: State management for user operations
```javascript
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as usersApi from '@/api/admin/users'

export const useAdminUsersStore = defineStore('adminUsers', () => {
  // State
  const users = ref([]) // Array of UserResponse
  const loading = ref(false)
  const error = ref(null)
  
  // Getters
  const activeUsers = computed(() => 
    users.value.filter(u => u.is_active).length
  )
  
  const usersByRole = computed(() => {
    const grouped = {}
    users.value.forEach(user => {
      if (!grouped[user.role]) grouped[user.role] = []
      grouped[user.role].push(user)
    })
    return grouped
  })
  
  // Actions
  async function fetchUsers() {
    loading.value = true
    try {
      const response = await usersApi.getUsers()
      users.value = response.data
    } catch (err) {
      error.value = err.message
    } finally {
      loading.value = false
    }
  }
  
  async function createUser(userData) {
    // Lines 45-60: Create user implementation
  }
  
  async function updateUser(userId, updates) {
    // Lines 61-75: Update user implementation
  }
  
  async function deleteUser(userId) {
    // Lines 76-90: Delete user implementation
  }
  
  return {
    users,
    loading,
    error,
    activeUsers,
    usersByRole,
    fetchUsers,
    createUser,
    updateUser,
    deleteUser
  }
})
```

## API Client Structure

### Users API Client (`api/admin/users.js`)
**Lines 1-60**: API calls for user management
```javascript
import apiClient from '@/api/client'

export const getUsers = () => 
  apiClient.get('/api/auth/users')

export const createUser = (userData) =>
  apiClient.post('/api/auth/register', userData)

export const updateUser = (userId, updates) =>
  apiClient.put(`/api/auth/users/${userId}`, updates)

export const deleteUser = (userId) =>
  apiClient.delete(`/api/auth/users/${userId}`)

export const toggleUserStatus = (userId, isActive) =>
  apiClient.patch(`/api/auth/users/${userId}/status`, { is_active: isActive })
```

## Router Configuration

### Update Router (`router/index.js`)
**Modify lines 50-58**: Add admin routes with auth guards
```javascript
// Admin routes (protected)
{
  path: '/admin',
  name: 'admin',
  component: () => import('../views/admin/AdminDashboard.vue'),
  meta: { requiresAuth: true, requiresAdmin: true }
},
{
  path: '/admin/users',
  name: 'admin-users',
  component: () => import('../views/admin/AdminUserManagement.vue'),
  meta: { requiresAuth: true, requiresAdmin: true }
},
{
  path: '/admin/cache',
  name: 'admin-cache',
  component: () => import('../views/admin/AdminCacheManagement.vue'),
  meta: { requiresAuth: true, requiresAdmin: true }
},
{
  path: '/admin/logs',
  name: 'admin-logs',
  component: () => import('../views/admin/AdminLogViewer.vue'),
  meta: { requiresAuth: true, requiresAdmin: true }
},
{
  path: '/admin/pipeline',
  name: 'admin-pipeline',
  component: () => import('../views/admin/AdminPipeline.vue'),
  meta: { requiresAuth: true, requiresAdmin: true }
},
{
  path: '/admin/staging',
  name: 'admin-staging',
  component: () => import('../views/admin/AdminGeneStaging.vue'),
  meta: { requiresAuth: true, requiresAdmin: true }
}
```

## Navigation Guards

### Add Auth Guards (`router/index.js`)
**Add after line 100**: Route protection
```javascript
router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()
  
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next('/login?redirect=' + to.fullPath)
  } else if (to.meta.requiresAdmin && !authStore.isAdmin) {
    next('/')
  } else {
    next()
  }
})
```

## WebSocket Implementation for Real-time Updates

### WebSocket Service (`services/websocket.js`)
**Lines 1-80**: Reusable WebSocket connection manager
```javascript
import { ref } from 'vue'

class WebSocketService {
  constructor() {
    this.ws = null
    this.reconnectInterval = 5000
    this.shouldReconnect = true
    this.messageHandlers = new Map()
  }
  
  connect(url = 'ws://localhost:8000/api/progress/ws') {
    if (this.ws?.readyState === WebSocket.OPEN) return
    
    this.ws = new WebSocket(url)
    
    this.ws.onopen = () => {
      console.log('WebSocket connected')
    }
    
    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      this.handleMessage(data)
    }
    
    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error)
    }
    
    this.ws.onclose = () => {
      if (this.shouldReconnect) {
        setTimeout(() => this.connect(url), this.reconnectInterval)
      }
    }
  }
  
  handleMessage(message) {
    // Dispatch to registered handlers based on message type
    const handlers = this.messageHandlers.get(message.type) || []
    handlers.forEach(handler => handler(message.data))
  }
  
  subscribe(messageType, handler) {
    if (!this.messageHandlers.has(messageType)) {
      this.messageHandlers.set(messageType, [])
    }
    this.messageHandlers.get(messageType).push(handler)
  }
  
  unsubscribe(messageType, handler) {
    const handlers = this.messageHandlers.get(messageType) || []
    const index = handlers.indexOf(handler)
    if (index > -1) {
      handlers.splice(index, 1)
    }
  }
  
  disconnect() {
    this.shouldReconnect = false
    this.ws?.close()
  }
}

export const wsService = new WebSocketService()
```

### Usage in Pipeline Store (`stores/admin/adminPipeline.js`)
```javascript
import { wsService } from '@/services/websocket'

export const useAdminPipelineStore = defineStore('adminPipeline', () => {
  const sources = ref([])
  
  // Subscribe to WebSocket updates
  const handleProgressUpdate = (data) => {
    const index = sources.value.findIndex(s => s.source_name === data.source_name)
    if (index > -1) {
      sources.value[index] = { ...sources.value[index], ...data }
    }
  }
  
  onMounted(() => {
    wsService.connect()
    wsService.subscribe('progress_update', handleProgressUpdate)
    wsService.subscribe('task_completed', handleProgressUpdate)
    wsService.subscribe('task_failed', handleProgressUpdate)
  })
  
  onUnmounted(() => {
    wsService.unsubscribe('progress_update', handleProgressUpdate)
    wsService.unsubscribe('task_completed', handleProgressUpdate)
    wsService.unsubscribe('task_failed', handleProgressUpdate)
  })
  
  return { sources }
})
```

## Styling Guidelines

### Component Density
- Tables: `density="compact"`
- Form fields: `density="compact"`
- Buttons in tables: `size="x-small"`
- Primary actions: `size="small"`
- Cards: Minimal padding (`pa-3` or `pa-4`)

### Color Usage
```scss
// Admin section colors
$admin-users: #0EA5E9;     // Primary blue
$admin-cache: #8B5CF6;     // Secondary violet
$admin-logs: #F59E0B;      // Warning amber
$admin-pipeline: #10B981;  // Success emerald
$admin-staging: #EF4444;   // Error red
```

### Responsive Breakpoints
- Mobile: Stack all cards vertically
- Tablet: 2 columns for cards
- Desktop: 3-4 columns for dashboard cards
- Data tables: Horizontal scroll on mobile

## Implementation Order

1. **Phase 1: Foundation** (Lines to implement)
   - AdminDashboard.vue (1-140)
   - AdminHeader.vue (1-40)
   - AdminStatsCard.vue (1-35)
   - Router configuration (50-100)
   - Base API clients (1-60 each)

2. **Phase 2: User Management**
   - AdminUserManagement.vue (1-200)
   - UserTable.vue (1-150)
   - adminUsers.js store (1-120)
   - users.js API client (1-60)

3. **Phase 3: Cache Management**
   - AdminCacheManagement.vue (1-250)
   - CacheMetrics.vue (1-120)
   - adminCache.js store (1-100)
   - cache.js API client (1-80)

4. **Phase 4: Logs & Monitoring**
   - AdminLogViewer.vue (1-280)
   - LogTable.vue (1-180)
   - adminLogs.js store (1-100)
   - logs.js API client (1-60)

5. **Phase 5: Pipeline & Staging**
   - AdminPipeline.vue (1-260)
   - AdminGeneStaging.vue (1-240)
   - PipelineStatus.vue (1-100)
   - StagingReview.vue (1-120)
   - Corresponding stores and API clients

## Testing Checklist

- [ ] All admin routes require authentication
- [ ] Admin-only routes enforce admin role
- [ ] API error handling shows user-friendly messages
- [ ] Loading states are properly displayed
- [ ] Empty states have appropriate messages
- [ ] Responsive design works on all breakpoints
- [ ] Keyboard navigation is functional
- [ ] Form validation provides clear feedback
- [ ] Confirmation dialogs for destructive actions
- [ ] Real-time updates where applicable

## Performance Considerations

1. **Lazy Loading**: All admin views use dynamic imports
2. **Pagination**: Implement for tables with >50 rows
3. **Debouncing**: Search inputs debounced at 300ms
4. **Caching**: Store frequently accessed data in Pinia
5. **Virtual Scrolling**: For large log tables

## Security Notes

1. All admin endpoints require JWT authentication
2. Role-based access control enforced on backend
3. Sensitive operations require confirmation
4. Audit logging for all admin actions
5. No sensitive data in frontend code

## Success Metrics

- Page load time < 1 second
- Time to first meaningful paint < 500ms
- Accessibility score > 95
- All CRUD operations < 2 seconds
- Error rate < 0.1%

## API Response Structures (Verified from Backend Implementation)

### User Management (auth.py)
```typescript
interface UserResponse {
  id: number
  email: string
  username: string
  full_name: string | null
  role: string // 'admin' | 'curator' | 'viewer'
  permissions: string[]
  is_active: boolean
  is_verified: boolean
  last_login: string | null // ISO datetime
  created_at: string // ISO datetime
  updated_at: string // ISO datetime
}

interface UserUpdate {
  email?: string
  full_name?: string | null
  role?: string
  is_active?: boolean
  is_verified?: boolean
}

interface Token {
  access_token: string
  refresh_token?: string
  token_type: string // "bearer"
  expires_in: number // seconds
}
```

### Cache Management (cache.py)
```typescript
interface CacheStatsResponse {
  namespace: string | null
  total_entries: number
  memory_entries: number
  db_entries: number
  hits: number
  misses: number
  hit_rate: number // 0.0 to 1.0
  total_size_bytes: number
  total_size_mb: number
}

interface NamespaceStatsResponse {
  namespace: string
  entry_count: number
  size_bytes: number
  size_mb: number
  oldest_entry: string | null // ISO datetime
  newest_entry: string | null // ISO datetime
  ttl_seconds: number | null
}

interface CacheHealthResponse {
  healthy: boolean
  memory_cache: {
    available: boolean
    entry_count: number
  }
  db_cache: {
    available: boolean
    entry_count: number
  }
  last_check: string // ISO datetime
}
```

### Logs Management (admin_logs.py)
```typescript
interface LogEntry {
  id: number
  timestamp: string // ISO datetime
  level: string // "INFO" | "WARNING" | "ERROR"
  source: string
  message: string
  request_id: string | null
  user_id: number | null
  extra_data: Record<string, any> | null
}

interface LogQueryResponse {
  logs: LogEntry[]
  pagination: {
    total: number
    limit: number
    offset: number
    has_more: boolean
  }
}

interface LogStatistics {
  time_range: {
    start: string // ISO datetime
    end: string // ISO datetime
    hours: number
  }
  level_distribution: Array<{
    level: string
    count: number
  }>
  top_sources: Array<{
    source: string
    count: number
  }>
  error_timeline: Array<{
    hour: string // ISO datetime
    errors: number
    total: number
    error_rate: number // percentage
  }>
  storage: {
    table_size: string // e.g., "25 MB"
    total_rows: number
  }
}
```

### Progress/Pipeline (progress.py)
```typescript
interface DataSourceProgress {
  source_name: string
  status: "idle" | "running" | "completed" | "failed" | "paused"
  progress_percentage: number
  current_operation: string
  items_processed: number
  items_added: number
  items_updated: number
  items_failed: number
  current_page: number | null
  total_pages: number | null
  current_item: number | null
  total_items: number | null
  last_error: string | null
  started_at: string | null // ISO datetime
  completed_at: string | null // ISO datetime
  last_update_at: string | null // ISO datetime
  estimated_completion: string | null // ISO datetime
  metadata: Record<string, any>
  category: "data_source" | "internal_process" | "other"
}

interface DashboardData {
  summary: {
    total_sources: number
    running: number
    completed: number
    failed: number
    total_items_processed: number
    total_items_added: number
    total_items_updated: number
    total_items_failed: number
  }
  sources: DataSourceProgress[]
}

// WebSocket message types
interface WSProgressUpdate {
  type: "progress_update" | "task_started" | "task_completed" | "task_failed" | "initial_status" | "ping"
  data: any
}
```

### Gene Staging (gene_staging.py)
```typescript
interface GeneNormalizationStagingResponse {
  id: number
  original_text: string
  source_name: string
  original_data: Record<string, any>
  normalization_log: Record<string, any>
  status: "pending" | "approved" | "rejected"
  priority_score: number
  requires_expert_review: boolean
  created_at: string // ISO datetime
  updated_at: string // ISO datetime
}

interface StagingStatsResponse {
  total_pending: number
  total_approved: number
  total_rejected: number
  by_source: Record<string, number>
}

interface NormalizationStatsResponse {
  total_attempts: number
  successful_attempts: number
  success_rate: number // 0.0 to 1.0
  by_source: Record<string, {
    attempts: number
    successes: number
    rate: number
  }>
}

interface GeneNormalizationLogResponse {
  id: number
  original_text: string
  source_name: string
  success: boolean
  approved_symbol: string | null
  hgnc_id: string | null
  normalization_log: Record<string, any>
  api_calls_made: number
  processing_time_ms: number
  created_at: string // ISO datetime
}
```

### Annotations Management (gene_annotations.py)
```typescript
interface AnnotationSource {
  source_name: string
  display_name: string
  description: string
  is_active: boolean
  last_update: string | null // ISO datetime
  next_update: string | null // ISO datetime
  update_frequency: string
  config: Record<string, any>
}

interface AnnotationStatistics {
  total_genes_with_annotations: number
  genes_with_both_sources: number
  sources: Array<{
    source: string
    gene_count: number
    annotation_count: number
    last_update: string | null // ISO datetime
  }>
  materialized_view: {
    name: string
    description: string
  }
}

interface PipelineStatus {
  sources: Array<{
    source: string
    is_active: boolean
    update_due: boolean
    last_update: string | null
    next_update: string | null
  }>
  pipeline_ready: boolean
  updates_due: string[]
}

interface ScheduledJob {
  id: string
  name: string
  next_run: string // ISO datetime
  last_run: string | null // ISO datetime
  status: "scheduled" | "running" | "completed" | "failed"
  enabled: boolean
}

interface SchedulerResponse {
  scheduler_running: boolean
  jobs: ScheduledJob[]
  total_jobs: number
}
```

### Common Response Wrapper
```typescript
interface ApiResponse<T> {
  data: T
  meta?: {
    [key: string]: any
  }
  error?: {
    message: string
    field?: string
    code?: string
  }
}
```

## API Endpoint Mapping

### User Management
- `GET /api/auth/users` - List all users
- `POST /api/auth/register` - Create new user (admin only)
- `PUT /api/auth/users/{id}` - Update user
- `DELETE /api/auth/users/{id}` - Delete user
- `POST /api/auth/login` - User login
- `POST /api/auth/refresh` - Refresh token

### Cache Management  
- `GET /api/admin/cache/stats` - Get cache statistics
- `GET /api/admin/cache/namespaces` - List cache namespaces
- `GET /api/admin/cache/namespace/{name}` - Get namespace details
- `DELETE /api/admin/cache` - Clear all cache
- `DELETE /api/admin/cache/{namespace}` - Clear namespace
- `POST /api/admin/cache/warm` - Warm cache
- `GET /api/admin/cache/health` - Cache health check

### Logs Management
- `GET /api/admin/logs/` - Query logs with filters
- `GET /api/admin/logs/statistics` - Get log statistics
- `DELETE /api/admin/logs/cleanup` - Clean old logs

### Progress/Pipeline
- `GET /api/progress/status` - Get all source statuses
- `GET /api/progress/status/{source}` - Get specific source status
- `POST /api/progress/trigger/{source}` - Trigger source update
- `POST /api/progress/pause/{source}` - Pause source
- `POST /api/progress/resume/{source}` - Resume source
- `GET /api/progress/dashboard` - Get dashboard data
- `WS /api/progress/ws` - WebSocket for real-time updates

### Gene Staging
- `GET /api/staging/staging/pending` - Get pending reviews
- `POST /api/staging/staging/{id}/approve` - Approve staging record
- `POST /api/staging/staging/{id}/reject` - Reject staging record
- `GET /api/staging/staging/stats` - Get staging statistics
- `GET /api/staging/normalization/stats` - Get normalization stats
- `GET /api/staging/normalization/logs` - Get normalization logs
- `POST /api/staging/normalization/test` - Test normalization

### Annotations
- `GET /api/annotations/sources` - List annotation sources
- `GET /api/annotations/statistics` - Get annotation statistics
- `POST /api/annotations/pipeline/update` - Trigger pipeline update
- `GET /api/annotations/pipeline/status` - Get pipeline status
- `POST /api/annotations/pipeline/validate` - Validate annotations
- `GET /api/annotations/scheduler/jobs` - List scheduled jobs
- `POST /api/annotations/scheduler/trigger/{job_id}` - Trigger job
- `POST /api/annotations/refresh-view` - Refresh materialized view