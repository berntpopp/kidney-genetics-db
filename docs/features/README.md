# Features

**User-facing feature documentation**

## Overview

The Kidney Genetics Database provides comprehensive gene annotation, curation, and exploration features powered by multiple authoritative data sources.

## Core Features

### Data & Annotations
- **[Annotation System](annotation-system.md)** - 9-source annotation pipeline
- **[Annotation Pipeline](annotation-pipeline.md)** - Pipeline architecture and operations
- **[Evidence Scoring](evidence-scoring.md)** - Scoring methodology and calculations
- **[PubTator Updates](pubtator-updates.md)** - Intelligent literature mining

### Infrastructure
- **[Caching System](caching-system.md)** - Multi-layer cache for performance
- **[User Authentication](user-authentication.md)** - JWT-based auth with RBAC

### Administration
- See [Administrator Guides](../guides/administrator/) for:
  - Admin panel usage
  - User management
  - Cache management

## Feature Status

### ✅ Implemented & Production-Ready

**Annotation Sources (9 active)**
- HGNC - Gene nomenclature
- gnomAD - Constraint scores
- ClinVar - Variant data
- HPO - Phenotype ontology
- GTEx - Expression data
- Descartes - Single-cell expression
- MPO/MGI - Mouse phenotypes
- STRING PPI - Protein interactions
- PubTator - Literature mining

**Core Systems**
- Evidence scoring with percentiles (0-100%)
- Real-time progress tracking via WebSocket
- Gene normalization with HGNC
- Unified caching (L1 + L2)
- JWT authentication with roles

**User Interface**
- Professional Material Design UI
- Advanced search and filtering
- Real-time updates
- Admin panel

### 🚧 In Development

- Email verification
- Password reset flow
- CSV/JSON export
- Diagnostic panel scraping

### 📋 Planned

- GraphQL API
- Advanced search filters
- Data visualization
- Collaborative curation

## Key Metrics

- **571+ genes** with comprehensive annotations
- **95%+ annotation coverage** (verified in production)
- **<10ms response times** (cached)
- **100% reliability** with safeguards
- **54,593+ publications** from PubTator

## Quick Links

### For Users
- [Getting Started](../getting-started/) - Quick start guide
- [API Documentation](../api/) - API reference
- [Troubleshooting](../troubleshooting/) - Common issues

### For Administrators
- [Admin Guides](../guides/administrator/) - Administration
- [User Management](../guides/administrator/user-management.md) - User management

### For Developers
- [Architecture](../architecture/) - System design
- [Implementation Notes](../implementation-notes/) - Technical details
- [Developer Guides](../guides/developer/) - Development guides

## Related Documentation

- [Project Status](../project-management/status.md) - Current state
- [Architecture](../architecture/) - Technical architecture
- [API Reference](../api/) - API documentation