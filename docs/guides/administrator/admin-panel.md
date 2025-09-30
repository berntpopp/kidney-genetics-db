# Admin Panel System

## Overview
Comprehensive admin panel for system administration and data management, following Material Design 3 principles and Vue 3 Composition API.

## Current Status
✅ **Fully Implemented** (August 30, 2025)

## Components

### Admin Dashboard
Central hub at `/admin` with:
- System statistics cards
- Navigation to all admin functions
- Real-time status indicators
- Quick action buttons

### User Management
**Location**: `/admin/users`
- Full CRUD operations for user accounts
- Role assignment (Admin, Curator, Viewer)
- Account status management
- Email verification control
- Login attempt tracking

### Cache Management
**Location**: `/admin/cache`
- Real-time cache metrics
- Namespace-specific clearing
- Cache warming functionality
- Performance monitoring charts
- Health status indicators

### Log Viewer
**Location**: `/admin/logs`
- Filterable log table with severity levels
- Date range selection
- Log statistics dashboard
- Export functionality
- Real-time log streaming

### Pipeline Control
**Location**: `/admin/pipeline`
- Source status cards with WebSocket updates
- Manual trigger controls for each source
- Progress monitoring with percentage
- Schedule management
- Error recovery actions

### Gene Staging
**Location**: `/admin/staging`
- Review pending gene normalizations
- Approve/reject staging records
- Normalization statistics
- Bulk operations
- History view

### Annotations Management
**Location**: `/admin/annotations`
- Source configuration
- Manual update triggers
- Schedule management
- Statistics and coverage metrics
- Validation tools

## Technical Implementation

### Frontend Architecture
- **Framework**: Vue 3 with Composition API
- **UI Library**: Vuetify 3 (Material Design)
- **State Management**: Pinia stores
- **Real-time**: WebSocket connections
- **Routing**: Vue Router with guards

### File Structure
```
frontend/src/
├── views/admin/
│   ├── AdminDashboard.vue
│   ├── AdminUserManagement.vue
│   ├── AdminCacheManagement.vue
│   ├── AdminLogViewer.vue
│   ├── AdminPipeline.vue
│   ├── AdminGeneStaging.vue
│   └── AdminAnnotations.vue
├── components/admin/
│   ├── AdminHeader.vue
│   ├── AdminStatsCard.vue
│   ├── UserTable.vue
│   ├── CacheMetrics.vue
│   ├── LogTable.vue
│   ├── PipelineStatus.vue
│   └── StagingReview.vue
└── stores/admin/
    ├── adminUsers.js
    ├── adminCache.js
    ├── adminLogs.js
    ├── adminPipeline.js
    └── adminStaging.js
```

## API Integration

### User Management
- `GET /api/auth/users` - List users
- `POST /api/auth/register` - Create user (Admin only)
- `PUT /api/auth/users/{id}` - Update user
- `DELETE /api/auth/users/{id}` - Delete user

### Cache Management
- `GET /api/admin/cache/stats` - Statistics
- `DELETE /api/admin/cache/{namespace}` - Clear cache
- `GET /api/admin/cache/health` - Health check

### Logs Management
- `GET /api/admin/logs/` - Query logs
- `GET /api/admin/logs/statistics` - Log stats
- `DELETE /api/admin/logs/cleanup` - Clean old logs

### Pipeline/Progress
- `GET /api/progress/status` - Source statuses
- `POST /api/progress/trigger/{source}` - Trigger update
- `WS /api/progress/ws` - WebSocket updates

## WebSocket Integration
Real-time updates for:
- Pipeline progress
- Log streaming
- Cache metrics
- System status

## Security
- JWT authentication required
- Role-based access control
- Admin-only endpoints
- Audit logging for all actions

## Design Principles
- **Compact density** for data-heavy interfaces
- **Single primary action** per view
- **Progressive disclosure** of details
- **Responsive design** for all devices
- **Minimal decoration** focusing on functionality

## Performance
- Lazy loading for all admin views
- Pagination for large datasets
- Debounced search inputs
- Virtual scrolling for logs
- Cached data in Pinia stores