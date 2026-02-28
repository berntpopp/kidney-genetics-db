# Configuration System Architecture

## Overview
Three-tier configuration system separating secrets from business logic.

## Configuration Tiers
1. **Environment Variables** (highest priority): Secrets, credentials, deployment-specific
2. **YAML Files** (`/backend/config/`): Business logic, data sources, public settings
3. **Default Values**: Development defaults in code

## File Structure
```
backend/
├── .env                    # Local overrides (not in git)
├── .env.example           # Environment template
├── app/core/
│   ├── config.py          # Security/infrastructure settings
│   └── datasource_config.py   # YAML loader
└── config/
    ├── datasources.yaml   # Data source configs
    ├── keywords.yaml      # Filter keywords
    └── annotations.yaml   # Annotation settings
```

## Configuration Categories

### Security Settings (config.py + env)
- Database credentials
- JWT keys
- API keys
- Admin passwords
- CORS origins

**Why?** Secrets must never be in static files.

### Data Source Settings (YAML)
- API endpoints (public)
- Panel/affiliate IDs
- Scoring weights
- Cache TTLs
- Rate limits

**Why?** Non-sensitive, version-controlled business logic.

## Security Rules
1. **Never put secrets in YAML files**
2. **Always use environment variables for credentials**
3. **Validate configuration at startup with Pydantic**

## Environment Override Pattern
```bash
# Pattern: KG_<SECTION>__<PARAM>=value
export KG_PANELAPP__CACHE_TTL=7200
export KG_ANNOTATIONS__CLINVAR__REQUESTS_PER_SECOND=5.0
```

## Usage
```python
# Security settings
from app.core.config import settings
db_url = settings.DATABASE_URL

# Data source settings
from app.core.datasource_config import get_source_config
config = get_source_config("PanelApp")
```

## Adding Configuration

**Security/Infrastructure**: Add to `config.py` + `.env.example`
**Data Sources**: Add to YAML files (no code changes needed)

## Results
- 495 → 258 lines (48% reduction)
- 100% backward compatibility
- Clean separation of concerns