# User Management & Authentication

## Overview
JWT-based authentication with role-based access control (RBAC) while maintaining **full public access for browsing and reading data**.

## Design Principle
**This is a PUBLIC scientific database.** Authentication is ONLY required for:
- **Curators**: Scientists who maintain and update data
- **Admins**: System administrators

All read operations remain completely open:
- ✅ Browsing genes and annotations (no login)
- ✅ Viewing statistics and dashboards (no login)
- ✅ Exporting data (no login)
- ✅ API access for research (no login)

## User Roles & Permissions

### Role Hierarchy
```
Public (no auth) - Read all data
├── Curator (auth required) - Modify data + run ingestion
└── Admin (auth required) - All curator permissions + system management
```

### Detailed Permissions
- **Public/Anonymous**: Read all data, no restrictions
- **Curator**: Create/update/delete genes and annotations, run pipelines
- **Admin**: User management, cache control, system configuration

## Current Implementation Status

### ✅ Implemented
- User model with roles and permissions
- JWT token generation and validation
- Password hashing with bcrypt
- Role-based access control
- Admin user management interface

### 🚧 Planned
- Email verification system
- Password reset flow
- Account lockout after failed attempts
- Refresh token mechanism
- Audit logging

## Database Schema

### User Model Fields
```python
id: int (primary key)
email: str (unique)
username: str (unique)
full_name: str (optional)
role: str ("admin", "curator", "viewer")
permissions: JSON (computed from role)
is_active: bool (default=True)
is_verified: bool (default=False)
last_login: datetime
created_at: datetime
updated_at: datetime
```

## API Endpoints

### Authentication (Public)
- `POST /api/auth/login` - Login (returns JWT)
- `POST /api/auth/refresh` - Refresh token
- `POST /api/auth/logout` - Logout
- `GET /api/auth/me` - Current user info

### User Management (Admin Only)
- `POST /api/auth/register` - Create new user
- `GET /api/auth/users` - List all users
- `PUT /api/auth/users/{id}` - Update user
- `DELETE /api/auth/users/{id}` - Delete user

## Protected Endpoints

### Write Operations (Curator+)
```python
# Example: Create gene
@router.post("/genes")
async def create_gene(
    gene: GeneCreate,
    current_user: User = Depends(require_curator)
):
    ...
```

### Admin Operations (Admin Only)
```python
# Example: Clear cache
@router.delete("/admin/cache/clear")
async def clear_cache(
    current_user: User = Depends(require_admin)
):
    ...
```

## Security Configuration

### JWT Settings
```python
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7
BCRYPT_ROUNDS = 12
```

### Password Policy
- Minimum length: 8 characters
- Complexity requirements enforced
- Bcrypt hashing with 12+ rounds

## Frontend Integration

### Auth Store (Pinia)
```javascript
// Handles login/logout
// Stores tokens securely
// Auto-refresh for logged-in users
// Shows/hides curator controls
```

### UI Components
- Login modal (hidden by default)
- Admin panel (shown only when authenticated)
- Edit/delete buttons (curator+ only)
- Subtle login button in navbar

## Migration Strategy

### From Current System
1. Add username to existing users
2. Assign roles based on is_admin flag
3. Force password reset for all users
4. Generate verification tokens

## Security Checklist
- ✅ Bcrypt password hashing
- ✅ JWT with short expiration
- ✅ Role-based access control
- ⬜ Account lockout mechanism
- ⬜ Email verification
- ⬜ Password reset flow
- ⬜ Rate limiting on auth endpoints
- ⬜ Audit logging