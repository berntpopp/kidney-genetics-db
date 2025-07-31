# Kidney-Genetics Database

A modern web platform for curating and exploring kidney disease-related genes. This project modernizes the original [kidney-genetics](https://github.com/halbritter-lab/kidney-genetics) R-based pipeline into a scalable Python/FastAPI + Vue.js architecture.

## Overview

A comprehensive database of ~3,000 kidney disease-associated genes aggregated from multiple genomic databases including PanelApp, HPO, diagnostic panels, and literature sources. Provides both a web interface and REST API for researchers and clinicians.

### Key Features

- **Multi-source Integration**: PanelApp, HPO, PubTator, commercial panels, and manual curation
- **Evidence Scoring**: Configurable weighting system for gene-disease associations  
- **Interactive Interface**: Searchable gene browser with filtering and visualization
- **REST API**: JSON/CSV exports with comprehensive documentation
- **Automated Updates**: Scheduled pipeline keeps data current
- **Version Tracking**: Historical data access and provenance

## Architecture

**Backend**: Python/FastAPI with PostgreSQL database and Celery task processing  
**Frontend**: Vue.js/Vuetify with interactive gene browser and data visualizations  
**Data**: PanelApp, HPO, commercial panels, literature curation, PubTator, ClinVar/OMIM

## Quick Start

```bash
# Development setup
docker-compose up -d
docker-compose exec api python -m pipeline.init_db
docker-compose exec api python -m pipeline.run_update

# API usage
curl "http://localhost:8000/api/v1/genes/?limit=20"
curl "http://localhost:8000/api/v1/genes/HGNC:5"

# Web interface
open http://localhost:3000
```

## Status

This project is **under active development** - see `PLAN.md` for implementation roadmap and current status.

Modernizes the established [kidney-genetics](https://github.com/halbritter-lab/kidney-genetics) R pipeline with improved performance, web interface, and API access for the research community.

## License

MIT License - see [LICENSE](LICENSE) file.