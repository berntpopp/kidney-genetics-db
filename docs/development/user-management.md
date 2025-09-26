# User Management Documentation

## Overview

This document describes the unified user management approach for the Kidney Genetics Database application. All user creation and authentication follows a single source of truth defined in the configuration.

## Configuration-Driven Approach

All admin user credentials are centrally defined in `backend/app/core/config.py`:

```python
# Default Admin (for initial setup only)
ADMIN_USERNAME: str = "admin"
ADMIN_EMAIL: str = "admin@kidney-genetics.local"
ADMIN_PASSWORD: str = "ChangeMe!Admin2024"  # Change immediately after first login
```

## Admin User Creation Flow

The admin user is automatically created during database initialization:

```
make db-reset
  ↓
Runs migrations
  ↓
Initializes annotation sources
  ↓
Runs initialize_database.py
  ↓
Calls database_init.create_default_admin()
  ↓
Creates admin user using config values
```

### Key Components

1. **`app/core/database_init.py`** - Contains `create_default_admin()` function
   - Reads credentials from `config.py`
   - Creates admin user if not exists
   - Updates existing admin to match config

2. **`scripts/initialize_database.py`** - Database initialization script
   - Calls `database_init.initialize_database()`
   - Creates views, admin user, clears cache
   - Runs on every `make db-reset`

3. **`scripts/create_admin_user.py`** - Standalone admin creation script
   - Uses same config values
   - Can be run independently if needed
   - Updates existing admin to match config

## Unified Password Management

### Single Source of Truth

All scripts and functions use the same configuration values from `app/core/config.py`:
- No hardcoded passwords in any scripts
- All components reference `settings.ADMIN_PASSWORD`
- Consistent credentials across the application

### Previous Issues (Fixed)

We previously had multiple inconsistent password definitions:
- ~~`database_init.py` - hardcoded "admin123"~~ ✅ Fixed
- ~~`create_admin_user.py` - hardcoded "admin123"~~ ✅ Fixed
- ~~`create_default_users.py` - used different password~~ ✅ Removed
- **Now: All use `settings.ADMIN_PASSWORD = "ChangeMe!Admin2024"`**

## Usage

### Automatic Creation

Admin user is automatically created when running:
```bash
make db-reset
```

Output will show:
```
🎯 Running full database initialization (includes admin user)...
✅ Initialization complete:
   Admin created: True
```

### Manual Creation

If needed, you can manually create/update the admin user:
```bash
cd backend
uv run python scripts/create_admin_user.py
```

This will:
- Create admin if not exists
- Update existing admin to match config values
- Display the current credentials

### Login Credentials

After database initialization:
- **Username**: `admin`
- **Email**: `admin@kidney-genetics.local`
- **Password**: `ChangeMe!Admin2024`

⚠️ **Security Note**: Change the admin password immediately after first login!

## Authentication System

### JWT-Based Authentication

The application uses JWT tokens for authentication:
- Access tokens expire in 30 minutes (configurable)
- Refresh tokens for extended sessions
- Role-based access control (admin, curator, public)

### Login Endpoint

```bash
POST /api/auth/login
Content-Type: application/x-www-form-urlencoded

username=admin&password=ChangeMe!Admin2024
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

## Security Best Practices

1. **Change Default Password**: The default password should be changed immediately after deployment
2. **Use Environment Variables**: In production, override config values with environment variables
3. **Password Requirements**: Implement strong password policies for production
4. **Regular Updates**: Rotate admin credentials periodically
5. **Audit Logging**: All admin actions are logged in the system_logs table

## Roles and Permissions

### Admin Role
- Full system access
- User management
- Data modification
- Pipeline control
- Cache management

### Curator Role
- Gene data modification
- Evidence curation
- Cannot manage users

### Public Access
- Read-only access to all data
- No authentication required for GET requests

## Troubleshooting

### Admin User Already Exists
If you see "Admin user already exists", the system will automatically update the existing admin to match the current configuration.

### Password Not Working
1. Check `app/core/config.py` for current password
2. Ensure database was properly initialized
3. Run `scripts/create_admin_user.py` to reset admin

### Multiple Admin Users
The system prevents duplicate admin users by checking both username and email before creation.

## Development vs Production

### Development
- Uses default credentials from config
- Automatic admin creation on db-reset
- Debug logging enabled

### Production
- Override credentials via environment variables:
  ```bash
  export ADMIN_USERNAME="prodadmin"
  export ADMIN_EMAIL="admin@yourdomain.com"
  export ADMIN_PASSWORD="SecurePassword123!"
  ```
- Disable automatic admin creation
- Use secrets management system

## Related Files

- `backend/app/core/config.py` - Configuration and credentials
- `backend/app/core/database_init.py` - Admin creation logic
- `backend/scripts/initialize_database.py` - Database initialization
- `backend/scripts/create_admin_user.py` - Manual admin creation
- `backend/app/core/security.py` - Password hashing and JWT handling
- `backend/app/api/endpoints/auth.py` - Authentication endpoints

## Changelog

### 2025-09-26
- Unified all user creation to use config values
- Removed duplicate/redundant scripts
- Fixed password inconsistencies
- Simplified Makefile to avoid duplicate admin creation
- Added comprehensive documentation