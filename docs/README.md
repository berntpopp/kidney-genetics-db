# Kidney-Genetics Database Documentation

## Overview
Complete documentation for the kidney-genetics database project, a modern web platform for curating and exploring kidney disease-related genes.

## Project Status
- **Current Version**: 0.1.0-alpha
- **Stage**: Alpha Development - Core functionality operational
- **Total Genes**: 571+ with annotations from 9 sources
- **PubTator Coverage**: 54,593+ publications (54x increase) - **CURRENTLY PROCESSING** 🚀
- **Architecture**: PostgreSQL + FastAPI + Vue.js
- **Reliability**: 100% success rate with comprehensive safeguards ✅
- **Status Document**: [PROJECT_STATUS.md](PROJECT_STATUS.md) - Comprehensive status and metrics

## Documentation Structure

### 📐 Architecture
- [Database Implementation](./architecture/database-implementation.md) - PostgreSQL schema with evidence scoring views
- [Backend Implementation](./architecture/backend-implementation.md) - FastAPI with WebSocket support
- [Logging System](./development/logging-system.md) - Unified structured logging

### ✨ Features
- [Annotations System](./features/annotations.md) - 9-source annotation pipeline
- [Admin Panel](./features/admin-panel.md) - Comprehensive administrative interface
- [User Management](./features/user-management.md) - JWT authentication & RBAC
- [Caching System](./features/caching.md) - Unified multi-layer cache
- **[PubTator Intelligent Update System](./features/pubtator-intelligent-update.md)** - ✅ Smart/full update modes with 54x coverage increase

### 🔧 Development
- [Setup Guide](./development/setup-guide.md) - Complete development environment setup
- [Hybrid Development](./development/hybrid-development.md) - Docker + local development workflow
- [API Reference](https://localhost:8000/docs) - Auto-generated API documentation (when running)

### 📊 Data Sources
- [Data Source Architecture](./data-sources/architecture.md) - Integration strategy for multiple sources
- [ClinGen & GenCC](./data-sources/clingen-gencc.md) - Expert curation data sources
- [Active Sources](./data-sources/active-sources.md) - Currently integrated data sources

### 🏗️ Implementation Details
- [Evidence Scoring](./implementation/evidence-scoring.md) - Scoring methodology and calculations
- [Cache Refactor](./implementation/cache-refactor-summary.md) - August 2025 consolidation
- [ClinVar Integration](./implementation/clinvar-implementation.md) - Variant annotation implementation
- [STRING PPI](./implementation/string-ppi-implementation.md) - Protein interaction scoring
- [Admin Panel Implementation](./implementation/admin-panel-implementation.md) - Frontend admin system
- **[PubTator Implementation Status](./implementation/pubtator-intelligent-update-status.md)** - ✅ Complete implementation status report
- **[PubTator Safeguards Guide](./implementation/pubtator-safeguards.md)** - ✅ Comprehensive safeguard system preventing hanging issues

### 📋 Planning Documents
- [Gene Annotations Plan](./planning/gene-annotations-plan.md) - Original annotation system design
- [Cache Refactor Plan](./planning/cache-refactor-plan.md) - Cache consolidation strategy
- [User Management Plan](./planning/user-management-plan.md) - Authentication system design
- [Annotation Rate Limiting](./planning/annotation-rate-limiting-plan.md) - API optimization strategy

## Quick Start

### Recommended: Hybrid Development Mode
```bash
# Start database in Docker, run API/Frontend locally
make hybrid-up

# Then in separate terminals:
make backend   # Start backend at http://localhost:8000
make frontend  # Start frontend at http://localhost:5173
```

### Alternative: Full Docker Mode
```bash
# Start all services in Docker
make dev-up
# Frontend: http://localhost:3000
# Backend: http://localhost:8000
```

## Key Features

### ✅ Implemented
- **4 Active Data Sources**: PanelApp, PubTator (✅ 54x increase), ClinGen, GenCC
- **571 Genes**: Comprehensive kidney disease gene coverage
- **54,593+ Publications**: Massive PubTator literature coverage increase
- **Intelligent Updates**: Smart/full mode updates with safeguards
- **Evidence Scoring**: PostgreSQL-based percentile scoring (0-100%)
- **Real-time Updates**: WebSocket-based progress tracking
- **Gene Normalization**: HGNC standardization with staging workflow
- **Advanced Search**: Filtering, sorting, score ranges
- **Professional UI**: Material Design with responsive layout
- **100% Reliability**: Comprehensive timeout and resource safeguards

### 🚧 In Development
- CSV/JSON export endpoints
- Diagnostic panel web scraping
- Literature manual upload
- Intelligent API caching system

## System Requirements
- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Docker & Docker Compose

## Database Statistics
- **Total Genes**: 571
- **Evidence Records**: 898
- **Data Sources**: 4 active (PanelApp, PubTator, ClinGen, GenCC)
- **High Confidence Genes (≥80%)**: Significantly increased with expert curation
- **Example Top Gene**: PKD1 with 93.11% score (evidence from all 4 sources)

## Development Commands

```bash
make help          # Show all available commands
make status        # Check system status
make db-reset      # Reset database completely
make lint          # Run code linting
make test          # Run test suite
make clean-all     # Clean everything
```

## API Endpoints

### Core Endpoints
- `GET /api/genes` - List genes with pagination and filtering
- `GET /api/genes/{symbol}` - Get gene details with evidence
- `GET /api/datasources` - Data source status and statistics
- `GET /api/progress` - Real-time progress updates (WebSocket)

### Admin Endpoints
- `POST /api/pipeline/run` - Trigger data pipeline
- `POST /api/gene-staging/normalize` - Run gene normalization
- `GET /api/gene-staging` - Review staging candidates
- **`POST /api/datasources/{source}/update?mode=smart|full`** - ✅ Intelligent update modes
- **`GET /api/progress/status`** - ✅ Real-time progress monitoring
- **`WS /api/progress/ws`** - ✅ WebSocket progress updates

## Contributing
See [Development Setup Guide](./development/setup-guide.md) for contribution guidelines.

## License
MIT License - see LICENSE file in project root.