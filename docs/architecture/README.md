# Architecture

**System design and technical architecture**

## Overview

The Kidney Genetics Database uses a modern, scalable architecture with FastAPI backend, Vue.js frontend, and PostgreSQL database. The system emphasizes non-blocking operations, unified utilities, and modular design.

## Documentation in This Section

### System Components
- **[Overview](overview.md)** - High-level architecture
- **[Backend](backend/)** - FastAPI application architecture
- **[Frontend](frontend/)** - Vue.js application architecture
- **[Database](database/)** - PostgreSQL schema and design
- **[Data Sources](data-sources/)** - Data integration architecture

## Key Architectural Principles

### Non-Blocking Architecture
- **Async/await throughout**: All FastAPI endpoints and pipeline operations are async
- **Thread pools for sync operations**: Database operations use ThreadPoolExecutor
- **Event loop protection**: Never block the event loop (target: <5ms blocking)
- **WebSocket stability**: Real-time updates without disconnections

### Unified Systems (MUST REUSE)
- **Logging**: `UnifiedLogger` with sync/async methods
- **Caching**: `CacheService` with L1 (memory) + L2 (PostgreSQL)
- **Retry Logic**: `retry_with_backoff` with exponential backoff
- **HTTP Clients**: `RetryableHTTPClient` with circuit breaker

### Modular Design
- **Base classes**: `BaseAnnotationSource` for all data sources
- **Dependency injection**: Services passed as parameters
- **Configuration-driven**: Behavior controlled by config files
- **Layered architecture**: Clear separation of concerns

## System Architecture Diagram

```
┌─────────────────────────────────────┐
│      Frontend (Vue.js + Vuetify)    │
│     Real-time updates via WebSocket │
└──────────────┬──────────────────────┘
               │ REST API + WebSocket
┌──────────────▼──────────────────────┐
│       Backend (FastAPI)              │
│  ┌──────────────────────────────┐   │
│  │   API Layer (Endpoints)      │   │
│  ├──────────────────────────────┤   │
│  │   Business Logic (Services)  │   │
│  ├──────────────────────────────┤   │
│  │   Core Utilities             │   │
│  │   (Cache, Retry, Logging)    │   │
│  ├──────────────────────────────┤   │
│  │   Data Access (CRUD/ORM)     │   │
│  └──────────────────────────────┘   │
└──────────────┬──────────────────────┘
               │ SQLAlchemy (sync)
┌──────────────▼──────────────────────┐
│      PostgreSQL Database             │
│  Hybrid relational + JSONB storage   │
│  Views for evidence scoring          │
└──────────────────────────────────────┘
```

## Technology Stack

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **ORM**: SQLAlchemy (sync with thread pools)
- **Migrations**: Alembic
- **Package Manager**: UV (not pip/poetry)
- **Testing**: Pytest

### Frontend
- **Framework**: Vue 3 + Vite
- **UI Library**: Vuetify 3 (Material Design)
- **State Management**: Pinia
- **HTTP Client**: Axios

### Database
- **DBMS**: PostgreSQL 15+
- **Design**: Hybrid relational + JSONB
- **Features**: Views, indexes, JSONB queries

### Infrastructure
- **Development**: Docker + local hybrid mode
- **Commands**: Make-based workflow
- **Caching**: L1 memory + L2 PostgreSQL
- **Logging**: Dual output (console + database)

## Performance Architecture

```
Request → FastAPI (async) → Thread Pool (sync DB) → PostgreSQL
           ↓                      ↓
        WebSocket            Never blocks event loop
        (real-time)          (<5ms target latency)
```

### Performance Targets (Achieved)
- **API Response**: <10ms (cached), <100ms (uncached)
- **Event Loop Blocking**: <1ms (eliminated with thread pools)
- **WebSocket Stability**: 100% uptime during heavy processing
- **Cache Hit Rate**: 75-95%
- **Annotation Coverage**: 95%+

## Design Patterns

### DRY (Don't Repeat Yourself)
- Unified logging, caching, and retry systems
- Base classes for common functionality
- Configuration over code

### KISS (Keep It Simple, Stupid)
- Use existing patterns and utilities
- Leverage PostgreSQL features (JSONB, views)
- Thread pools over complex async migrations

### Modularization & Reusability
- Inheritance hierarchy for annotation sources
- Composition of services from smaller utilities
- Dependency injection throughout

## Related Documentation

- [Backend Architecture](backend/) - Detailed backend design
- [Database Design](database/) - Schema and data model
- [Data Sources](data-sources/) - Integration patterns
- [Reference](../reference/) - Technical references
- [CLAUDE.md](../../CLAUDE.md) - Complete guidelines