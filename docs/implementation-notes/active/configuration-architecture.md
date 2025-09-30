# Configuration Architecture

**Status**: ✅ Implemented (2025-09-26)
**GitHub Issue**: #17

## Overview

The Kidney-Genetics Database uses a three-tier configuration system that separates concerns between security-sensitive settings, operational parameters, and business logic configuration.

## Three-Tier Configuration System

```
┌─────────────────────────────────────────────────┐
│         Environment Variables (.env)            │  ← Secrets, deployment-specific
├─────────────────────────────────────────────────┤
│         YAML Configuration Files                │  ← Business logic, static config
├─────────────────────────────────────────────────┤
│         Pydantic Models (validated)             │  ← Type-safe defaults
└─────────────────────────────────────────────────┘
```

## Configuration Separation Rationale

### 1. Security Settings (backend/app/core/config.py)
**Why kept in Python/env vars:**
- Database credentials
- JWT secrets
- API keys
- Redis connection strings
- Session secrets

These MUST NOT be in YAML files because:
- They change per environment (dev/staging/prod)
- They contain secrets that shouldn't be in version control
- They require secure deployment patterns (K8s secrets, vault, etc.)

### 2. Business Logic Configuration (backend/config/*.yaml)
**Why moved to YAML:**
- Data source configurations
- Domain keywords
- Rate limits and retry settings
- Cache TTL values
- Panel IDs and API endpoints

These are ideal for YAML because:
- They're the same across environments
- They need to be reviewed/audited
- They benefit from version control
- They're business logic, not secrets

## File Structure

```
backend/
├── config/                      # Business logic configuration
│   ├── datasources.yaml        # Data source settings
│   ├── keywords.yaml           # Domain keywords
│   └── annotations.yaml        # Annotation source config
├── .env                        # Security settings (not in git)
└── app/core/
    ├── config.py               # Security/deployment config
    └── datasource_config.py    # Loads YAML + env overrides
```

## Loading Order

1. **Defaults**: Pydantic model defaults
2. **YAML Files**: Base configuration loaded
3. **Environment Variables**: Override any setting
4. **Validation**: Pydantic validates final config

## Usage Examples

### Security Settings (stays in Python)
```python
# backend/app/core/config.py
class Settings(BaseSettings):
    database_url: str  # From DATABASE_URL env var
    secret_key: str    # From SECRET_KEY env var
    jwt_secret: str    # From JWT_SECRET env var
```

### Business Logic (moved to YAML)
```yaml
# backend/config/datasources.yaml
datasources:
  PanelApp:
    requests_per_second: 5.0
    cache_ttl: 21600
    uk_panels: [384, 539]
```

### Environment Override
```bash
# Can override YAML values if needed
export KG_DATASOURCES__PANELAPP__REQUESTS_PER_SECOND=10.0
```

## Benefits

1. **Security**: Secrets never in version control
2. **Flexibility**: Easy configuration changes without code changes
3. **Type Safety**: Pydantic validates all configuration
4. **Documentation**: YAML is self-documenting
5. **Separation**: Clear distinction between secrets and config

## Migration from Hardcoded Values

Successfully migrated:
- 495 lines of hardcoded configuration → YAML files
- 18 duplicate keyword lists → single deduplicated list
- 31 consumer files → no changes needed (100% backward compatible)

## Best Practices

1. **Never put secrets in YAML files**
2. **Use environment variables for deployment-specific values**
3. **Use YAML for business logic configuration**
4. **Document rationale for placement decisions**
5. **Validate all configuration at startup**