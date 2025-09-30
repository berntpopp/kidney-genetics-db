# Kidney Genetics Database - Documentation

**Modern platform for curating and exploring kidney disease-related genes**

[![Status](https://img.shields.io/badge/status-alpha-yellow)]() [![Version](https://img.shields.io/badge/version-0.1.0-blue)]() [![Python](https://img.shields.io/badge/python-3.11+-green)]() [![FastAPI](https://img.shields.io/badge/FastAPI-latest-teal)]() [![Vue](https://img.shields.io/badge/Vue-3-green)]()

## 🚀 Quick Start

**Get running in 5 minutes:**

```bash
# Clone and start development environment
git clone <repository-url>
cd kidney-genetics-db

# Start services (hybrid mode - recommended)
make hybrid-up

# In separate terminals:
make backend   # http://localhost:8000
make frontend  # http://localhost:5173
```

👉 **New to the project?** Start with [Getting Started](getting-started/)

## 📚 Documentation Structure

### 🎯 Getting Started
**New developers start here** - [Getting Started Guide](getting-started/)
- [Quick Start](getting-started/quick-start.md) - 5-minute setup
- [Installation](getting-started/installation.md) - Detailed environment setup
- [Development Workflow](getting-started/development-workflow.md) - Day-to-day operations

### 📖 Guides
**How-to guides by role** - [All Guides](guides/)
- [Developer Guides](guides/developer/) - Development best practices and workflows
- [Administrator Guides](guides/administrator/) - System administration and curation
- [Deployment Guides](guides/deployment/) - Production deployment (coming soon)

### 🏗️ Architecture
**System design and patterns** - [Architecture Overview](architecture/)
- [System Overview](architecture/overview.md) - High-level architecture
- [Backend](architecture/backend/) - FastAPI application design
- [Frontend](architecture/frontend/) - Vue.js application structure
- [Database](architecture/database/) - PostgreSQL schema and design
- [Data Sources](architecture/data-sources/) - Integration architecture

### ✨ Features
**What the system does** - [Feature Documentation](features/)
- [Annotation System](features/annotation-system.md) - 9-source annotation pipeline
- [Evidence Scoring](features/evidence-scoring.md) - Scoring methodology
- [Caching System](features/caching-system.md) - Performance optimization
- [User Authentication](features/user-authentication.md) - JWT-based auth

### 🔌 API
**REST API reference** - [API Documentation](api/)
- [API Overview](api/overview.md) - Design and conventions
- [Authentication](api/authentication.md) - Auth and authorization
- [Endpoints](api/endpoints/) - Detailed endpoint documentation
- [WebSockets](api/websockets.md) - Real-time updates

### 📋 Reference
**Technical references** - [Reference Documentation](reference/)
- [Configuration](reference/configuration.md) - System configuration
- [Logging System](reference/logging-system.md) - Unified logging
- [Environment Variables](reference/environment-variables.md) - Configuration options
- [Design System](reference/design-system.md) - UI/UX design system

### 🔧 Implementation Notes
**Development history and plans** - [Implementation Notes](implementation-notes/)
- [Completed](implementation-notes/completed/) - ✅ Finished implementations
- [Active](implementation-notes/active/) - 🚧 Current work
- [Planning](implementation-notes/planning/) - 📋 Future plans

### 🐛 Troubleshooting
**Problem solving** - [Troubleshooting Guide](troubleshooting/)
- [Common Issues](troubleshooting/common-issues.md) - FAQs and solutions
- [Fixes](troubleshooting/fixes/) - Detailed fix documentation
- [Performance Tuning](troubleshooting/performance-tuning.md) - Optimization guide

### 📊 Project Management
**Status and planning** - [Project Management](project-management/)
- [Project Status](project-management/status.md) - Current state and metrics
- [Release Notes](project-management/releases.md) - Version history
- [Roadmap](project-management/roadmap.md) - Future plans

### 📦 Archive
**Historical documentation** - [Archive](archive/)
- Preserved for historical reference
- Superseded plans and old implementations

## 🎯 Quick Access by Role

### 👨‍💻 I'm a Developer
1. [Quick Start](getting-started/quick-start.md) - Get environment running
2. [Developer Guides](guides/developer/) - Development workflows
3. [Architecture](architecture/) - Understand the system
4. [CLAUDE.md](../CLAUDE.md) - Complete development guidelines

### 👤 I'm an Administrator
1. [Admin Panel Guide](guides/administrator/admin-panel.md) - Using admin interface
2. [User Management](guides/administrator/user-management.md) - Managing users
3. [Cache Management](guides/administrator/cache-management.md) - Cache operations

### 🔍 I'm Exploring the API
1. [API Overview](api/overview.md) - API design and conventions
2. [API Endpoints](api/endpoints/) - Endpoint documentation
3. Interactive Docs: http://localhost:8000/docs (when running)

### 📈 I'm a Product Manager
1. [Project Status](project-management/status.md) - Current state
2. [Features](features/) - What's implemented
3. [Roadmap](project-management/roadmap.md) - What's planned

## 📊 Project Overview

### Current Status
**Version**: Alpha v0.1.0
**Status**: 🟢 Operational with core functionality
**Last Updated**: September 2025

### Key Metrics
- ✅ **571+ genes** with comprehensive annotations from 9 sources
- ✅ **95%+ annotation coverage** (verified in production)
- ✅ **<10ms response times** (cached)
- ✅ **100% uptime** during heavy processing
- ✅ **54,593+ publications** from PubTator

### Technology Stack
- **Backend**: FastAPI + Python 3.11+ + PostgreSQL 15+
- **Frontend**: Vue 3 + Vite + Vuetify 3
- **Package Management**: UV (backend), npm (frontend)
- **Development**: Make-based workflow with hybrid Docker/local mode

## 🔑 Key Features

### Data & Annotations
- **9 Active Data Sources**: HGNC, gnomAD, ClinVar, HPO, GTEx, Descartes, MPO/MGI, STRING PPI, PubTator
- **Evidence Scoring**: PostgreSQL-based percentile scoring (0-100%)
- **Real-time Updates**: WebSocket-based progress tracking
- **Gene Normalization**: HGNC standardization with staging workflow

### User Interface
- Professional Material Design interface
- Advanced search and filtering
- Score-based ranking
- Real-time progress updates

### Administration
- Comprehensive admin panel
- User management with RBAC (Admin, Curator, Public)
- Cache management
- Pipeline control
- Log viewer

## 💻 Development Commands

```bash
# Environment
make hybrid-up       # Start development environment
make backend         # Start backend (separate terminal)
make frontend        # Start frontend (separate terminal)
make hybrid-down     # Stop environment

# Database
make db-reset        # Complete database reset
make db-clean        # Clean data only (keep structure)
make status          # Check system status

# Quality
make lint            # Lint backend code
make test            # Run test suite
make clean-all       # Clean everything

# Help
make help            # Show all commands
```

## 🏛️ Architecture Principles

### Non-Blocking Architecture
- **Async/await throughout** - FastAPI endpoints and pipeline operations
- **Thread pools for sync operations** - Database operations that would block
- **Event loop protection** - Never block the event loop (<5ms target)
- **WebSocket stability** - Real-time updates without disconnections

### Unified Systems (MUST REUSE)
```python
# Logging - ALWAYS use this
from app.core.logging import get_logger
logger = get_logger(__name__)
await logger.info("Message", key="value")

# Caching - ALWAYS use this
from app.core.cache_service import get_cache_service
cache = get_cache_service(db_session)
await cache.set("key", value, namespace="annotations")

# Retry - ALWAYS use this
from app.core.retry_utils import retry_with_backoff
@retry_with_backoff()
async def api_call():
    return await client.get(url)
```

### Design Patterns
- **DRY**: Reuse unified logging, caching, and retry systems
- **KISS**: Use existing patterns, leverage PostgreSQL features
- **Modular**: Base classes, dependency injection, configuration-driven

## 📖 Essential Reading

### For New Developers
1. [Getting Started](getting-started/) - Environment setup
2. [Developer Guides](guides/developer/) - Development workflows
3. [Architecture Overview](architecture/) - System understanding
4. [CLAUDE.md](../CLAUDE.md) - Complete guidelines (for AI and humans)

### For Understanding the System
1. [Architecture](architecture/) - System design
2. [Features](features/) - What's implemented
3. [API Documentation](api/) - API reference
4. [Database Schema](reference/database-schema.md) - Data model

### For Contributing
1. [Developer Setup](guides/developer/setup-environment.md) - Environment
2. [Contributing Guide](guides/developer/contributing.md) - Contribution process
3. [Design System](reference/design-system.md) - UI/UX standards
4. [Testing Guide](guides/developer/testing.md) - Testing practices

## 🔗 External Resources

- **API Docs (Interactive)**: http://localhost:8000/docs (when running)
- **Frontend**: http://localhost:5173 (when running)
- **Admin Panel**: http://localhost:5173/admin (when running)

## 📞 Support

### Documentation Issues
If you find documentation issues:
1. Check if information is in the [Archive](archive/)
2. Check [Troubleshooting](troubleshooting/) for common problems
3. Review [Implementation Notes](implementation-notes/) for technical details
4. Create an issue in the repository

### Development Help
- [Troubleshooting Guide](troubleshooting/) - Common issues
- [Developer Guides](guides/developer/) - Development resources
- [CLAUDE.md](../CLAUDE.md) - Complete guidelines

## 📄 License

MIT License - see LICENSE file in project root.

---

**Documentation Version**: 2.0
**Last Major Update**: September 2025 (complete reorganization)
**Maintained By**: Development Team

👉 **Start your journey**: [Getting Started Guide](getting-started/)