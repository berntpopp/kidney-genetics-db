# User Management System Refactoring Plan

## Executive Summary
Implement a comprehensive user management system with JWT authentication and role-based access control (RBAC) for the Kidney Genetics Database API, while maintaining **full public access for browsing and reading data**. Authentication is only required for data modification and administrative tasks.

## Key Design Principle
**This is a PUBLIC scientific database.** The primary use case is researchers and clinicians browsing kidney genetics data without any barriers. Authentication is ONLY for:
- **Curators**: Scientists who maintain and update the data
- **Admins**: System administrators

All read operations remain completely open - no login required for:
- Browsing genes and annotations
- Viewing statistics and dashboards  
- Exporting data
- Accessing API endpoints for research

## Architecture Overview

### Core Components
1. **Authentication**: JWT with access/refresh tokens
2. **Authorization**: Role-based (Admin, Curator, Viewer) with permissions
3. **Security**: Bcrypt password hashing, token refresh, account lockout
4. **User Management**: Registration, profile management, password reset

### User Roles & Permissions

#### Roles Hierarchy
```
Public (no auth) - Read all data
├── Curator (auth required) - Modify data + run ingestion
└── Admin (auth required) - All curator permissions + system management
```

#### Detailed Permissions
- **Public/Anonymous**: Read all genes, annotations, statistics, datasources (no login required)
- **Curator**: Create/update/delete genes and annotations, run ingestion pipelines
- **Admin**: All curator permissions + user management + cache control + system configuration

## Implementation Plan

### Phase 1: Core Security Infrastructure

#### 1.1 Create Security Module
**File**: `backend/app/core/security.py` (NEW)
```python
# Core security utilities
- Password hashing (bcrypt)
- JWT token creation/verification
- Role/permission checking utilities
- OAuth2 scheme setup
```

#### 1.2 Update Configuration
**File**: `backend/app/core/config.py` (MODIFY)
```python
# Add security settings
- JWT_SECRET_KEY (generate with: openssl rand -hex 32)
- JWT_ALGORITHM = "HS256"
- ACCESS_TOKEN_EXPIRE_MINUTES = 30
- REFRESH_TOKEN_EXPIRE_DAYS = 7
- PASSWORD_MIN_LENGTH = 8
- BCRYPT_ROUNDS = 12
```

#### 1.3 Enhanced User Model
**File**: `backend/app/models/user.py` (MODIFY)
```python
class User(Base, TimestampMixin):
    # Existing fields
    id: int
    email: str
    hashed_password: str
    
    # New fields
    username: str (unique, indexed)
    full_name: str (optional)
    role: str (default="viewer")
    permissions: JSON (computed from role)
    is_active: bool (default=True)
    is_verified: bool (default=False)
    last_login: datetime (nullable)
    failed_login_attempts: int (default=0)
    locked_until: datetime (nullable)
    
    # Token fields
    refresh_token: str (nullable)
    password_reset_token: str (nullable)
    password_reset_expires: datetime (nullable)
    email_verification_token: str (nullable)
```

### Phase 2: Authentication System

#### 2.1 Authentication Schemas
**File**: `backend/app/schemas/auth.py` (NEW)
```python
# Pydantic models
- Token (access_token, token_type, refresh_token)
- TokenData (username, roles, permissions, exp)
- UserLogin (username/email, password)
- UserRegister (email, username, password, full_name)
- UserResponse (public user data)
- PasswordReset (email)
- PasswordResetConfirm (token, new_password)
```

#### 2.2 Authentication Endpoints
**File**: `backend/app/api/endpoints/auth.py` (NEW)
```python
# Public endpoints
POST /api/auth/login - Login (returns access + refresh tokens)
POST /api/auth/refresh - Refresh access token
POST /api/auth/logout - Logout (invalidate refresh token)
POST /api/auth/forgot-password - Request password reset
POST /api/auth/reset-password - Complete password reset

# Protected endpoints (Admin only - to control who can be curator)
POST /api/auth/register - User registration (Admin only)
POST /api/auth/verify-email - Email verification
GET  /api/auth/me - Get current user info (Authenticated users)
GET  /api/auth/users - List all users (Admin only)
PUT  /api/auth/users/{id} - Update user role (Admin only)
DELETE /api/auth/users/{id} - Delete user (Admin only)
```

#### 2.3 User Service
**File**: `backend/app/services/user_service.py` (NEW)
```python
class UserService:
    - create_user()
    - authenticate_user()
    - get_user_by_email()
    - get_user_by_username()
    - update_user()
    - verify_password()
    - update_password()
    - handle_failed_login()
    - clear_failed_attempts()
```

### Phase 3: Authorization System

#### 3.1 Permission Dependencies
**File**: `backend/app/core/dependencies.py` (NEW)
```python
# FastAPI dependencies
- get_current_user() - Extract user from JWT
- get_current_active_user() - Ensure user is active
- require_role(role: str) - Role-based access
- require_permission(permission: str) - Permission-based access
- require_admin() - Admin only access
- require_curator() - Curator or admin access
```

#### 3.2 Endpoint Security Matrix
**Files**: `backend/app/api/endpoints/*.py` (SELECTIVE MODIFICATIONS)

##### PUBLIC ENDPOINTS (No Authentication Required)
```python
# genes.py - All GET endpoints remain public
@router.get("/genes")  # PUBLIC - Browse genes
@router.get("/genes/{gene_id}")  # PUBLIC - View gene details
@router.get("/genes/{gene_id}/export")  # PUBLIC - Export gene data

# gene_annotations.py - All GET endpoints remain public  
@router.get("/annotations")  # PUBLIC - Browse annotations
@router.get("/annotations/{gene_id}")  # PUBLIC - View annotations

# statistics.py - All endpoints remain public
@router.get("/statistics/summary")  # PUBLIC - Dashboard data
@router.get("/statistics/classification")  # PUBLIC - Classifications

# datasources.py - All GET endpoints remain public
@router.get("/datasources")  # PUBLIC - List sources
@router.get("/datasources/{source_id}/stats")  # PUBLIC - Source stats

# gene_staging.py - GET endpoints remain public
@router.get("/staging")  # PUBLIC - View staging data
@router.get("/staging/{id}")  # PUBLIC - View specific staging

# progress.py - WebSocket remains public
@router.websocket("/progress/ws")  # PUBLIC - Watch progress
```

##### PROTECTED ENDPOINTS (Authentication Required)
```python
# genes.py - Write operations (Curator+)
@router.post("/genes")
async def create_gene(
    gene: GeneCreate,
    current_user: User = Depends(require_curator)
):
    ...

@router.put("/genes/{gene_id}")
async def update_gene(
    gene_id: int,
    gene: GeneUpdate,
    current_user: User = Depends(require_curator)
):
    ...

@router.delete("/genes/{gene_id}")
async def delete_gene(
    gene_id: int,
    current_user: User = Depends(require_admin)  # Admin only
):
    ...

# ingestion.py - All endpoints (Curator+)
@router.post("/ingestion/start")
async def start_ingestion(
    current_user: User = Depends(require_curator)
):
    ...

@router.post("/ingestion/update/{source}")
async def update_source(
    source: str,
    current_user: User = Depends(require_curator)
):
    ...

# cache.py - All modification endpoints (Admin only)
@router.delete("/admin/cache/clear")
async def clear_cache(
    current_user: User = Depends(require_admin)
):
    ...

# admin_logs.py - All endpoints (Admin only)
@router.get("/admin/logs")
async def get_logs(
    current_user: User = Depends(require_admin)
):
    ...
```

### Phase 4: Database Migrations

#### 4.1 Create Migration
**File**: `backend/alembic/versions/xxx_add_user_management.py` (NEW)
```sql
-- Add new columns to users table
ALTER TABLE users ADD COLUMN username VARCHAR(50) UNIQUE NOT NULL;
ALTER TABLE users ADD COLUMN full_name VARCHAR(255);
ALTER TABLE users ADD COLUMN role VARCHAR(20) DEFAULT 'viewer';
ALTER TABLE users ADD COLUMN permissions JSONB;
ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT TRUE;
ALTER TABLE users ADD COLUMN is_verified BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN last_login TIMESTAMP;
ALTER TABLE users ADD COLUMN failed_login_attempts INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN locked_until TIMESTAMP;
ALTER TABLE users ADD COLUMN refresh_token TEXT;
ALTER TABLE users ADD COLUMN password_reset_token VARCHAR(255);
ALTER TABLE users ADD COLUMN password_reset_expires TIMESTAMP;
ALTER TABLE users ADD COLUMN email_verification_token VARCHAR(255);

-- Create indexes
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_is_active ON users(is_active);
```

#### 4.2 Seed Default Users
**File**: `backend/app/scripts/create_default_users.py` (NEW)
```python
# Script to create default users for initial setup
# 1. Admin user (required)
#    Username: admin
#    Email: admin@kidney-genetics.local
#    Password: (from ADMIN_PASSWORD env var)
#
# 2. Example curator (optional, for testing)
#    Username: curator
#    Email: curator@kidney-genetics.local  
#    Password: (from CURATOR_PASSWORD env var)
#
# Note: In production, curators should be added by admin
```

### Phase 5: Security Enhancements

#### 5.1 Account Security
**File**: `backend/app/core/account_security.py` (NEW)
```python
class AccountSecurity:
    - is_account_locked()
    - record_failed_login()
    - clear_failed_attempts()
    - enforce_password_policy()
    - validate_password_strength()
```

#### 5.2 Audit Logging
**File**: `backend/app/models/audit_log.py` (NEW)
```python
class AuditLog(Base, TimestampMixin):
    user_id: int
    action: str
    resource_type: str
    resource_id: int
    ip_address: str
    user_agent: str
    success: bool
    details: JSON
```

### Phase 6: Frontend Integration

#### 6.1 Update API Client
**File**: `frontend/src/services/api.js` (MODIFY)
```javascript
// Conditional authentication headers (only if logged in)
// Public endpoints work without auth
// Add auth headers only for protected operations
// Handle token refresh for authenticated users
// Graceful fallback for 401 (don't break public browsing)
```

#### 6.2 Create Auth Store
**File**: `frontend/src/stores/auth.js` (NEW)
```javascript
// Vuex/Pinia store for auth state
// Handle login/logout
// Store tokens securely (httpOnly cookies preferred)
// Auto-refresh tokens for logged-in users
// Show/hide curator controls based on auth state
```

#### 6.3 UI Components
**File**: `frontend/src/components/` (NEW/MODIFY)
```javascript
// LoginModal.vue - Login form (hidden by default)
// AdminPanel.vue - Admin/curator controls (shown only when authenticated)
// Public pages remain unchanged and fully functional without auth
// Add "Login" button to navbar (optional, unobtrusive)
// Show edit/delete buttons only for authenticated curators
```

## Implementation Steps

### Step 1: Dependencies Installation
```bash
cd backend
uv add "passlib[bcrypt]" python-jose[cryptography] python-multipart email-validator
```

### Step 2: Generate Secret Keys
```bash
# Generate JWT secret
openssl rand -hex 32
# Add to .env: JWT_SECRET_KEY=<generated_key>
```

### Step 3: Implementation Order
1. Create security.py with core utilities
2. Update user model
3. Create authentication schemas
4. Implement auth endpoints
5. Add permission dependencies
6. Secure existing endpoints (incrementally)
7. Run database migration
8. Create default admin user
9. Test authentication flow
10. Update frontend

## Testing Plan

### Public Access Tests (CRITICAL)
- Verify all GET endpoints work without authentication
- Test gene browsing without login
- Confirm statistics/dashboard accessible publicly
- Validate data export works without auth
- Ensure WebSocket progress monitoring works publicly

### Unit Tests
- Password hashing/verification
- JWT creation/validation
- Permission checking
- User authentication

### Integration Tests
- Public browsing remains functional
- Login/logout flow for curators
- Token refresh mechanism
- Password reset flow
- Role-based access control
- Curator can modify data after login
- Admin can manage users

### Security Tests
- Public endpoints reject POST/PUT/DELETE
- Account lockout after failed attempts
- Password strength validation
- Token expiration handling
- SQL injection prevention
- CORS configuration validation

## Security Checklist

- [x] Bcrypt for password hashing (12+ rounds)
- [x] JWT with short expiration (30 min access, 7 day refresh)
- [x] Account lockout after failed attempts
- [x] Password complexity requirements
- [x] Secure token storage (HttpOnly cookies for web)
- [x] CORS properly configured
- [x] Rate limiting on auth endpoints
- [x] Audit logging for security events
- [x] Email verification for new accounts
- [x] Secure password reset flow

## Environment Variables

Add to `.env`:
```bash
# Security
JWT_SECRET_KEY=<generate with: openssl rand -hex 32>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Default Admin (first run only)
ADMIN_USERNAME=admin
ADMIN_EMAIL=admin@kidney-genetics.local
ADMIN_PASSWORD=<generate secure password>
```

## Migration from Current System

1. **Backup existing data**
2. **Add username to existing users** (use email prefix)
3. **Assign default roles** (existing is_admin → admin role, others → viewer)
4. **Force password reset** for all existing users
5. **Generate email verification tokens**

## Rollback Plan

1. Keep backup of database before migration
2. Feature flag for new auth system
3. Parallel run both systems initially
4. Quick rollback via alembic downgrade

## Timeline Estimate

- Phase 1-2: 2-3 days (Core auth system)
- Phase 3: 1-2 days (Securing endpoints)
- Phase 4-5: 1 day (Migration & security)
- Phase 6: 1-2 days (Frontend integration)
- Testing: 2 days

**Total: 7-10 days**

## Notes

- **Public-first approach**: Ensure no disruption to public data access
- **Unobtrusive UI**: Login button should be subtle (e.g., small icon in navbar)
- **Progressive enhancement**: Public features work without JavaScript/auth
- Start with minimal implementation, add features incrementally
- Use existing logging system for audit trail
- Consider adding 2FA in future iteration for admin accounts
- Monitor failed login attempts for security alerts
- Regular security audits recommended
- Consider API keys for programmatic access (future enhancement)

## References

- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [JWT Best Practices](https://tools.ietf.org/html/rfc8725)
- [OWASP Authentication Cheatsheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
- Reference Implementation: `laborberlin/agde-api`