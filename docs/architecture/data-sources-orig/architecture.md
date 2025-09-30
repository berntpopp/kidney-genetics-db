# Data Source Architecture

## Overview

Smart separation of stable API sources from brittle web scraping, with unified ingestion through APIs. This architecture ensures the main pipeline remains stable even when external websites change.

## Source Classification

### Tier 1: Stable API Sources (Direct Integration)
Sources with official APIs that rarely break.

| Source | Type | Integration Method | Update Frequency |
|--------|------|-------------------|------------------|
| PanelApp UK | REST API | Direct API calls | Daily |
| PanelApp Australia | REST API | Direct API calls | Daily |
| HPO | REST API | Direct API calls | Weekly |
| PubTator | REST API | Direct API calls | Weekly |
| HGNC | REST API | Direct API calls | Monthly |

### Tier 2: Brittle Web Sources (Scraping Service)
Websites that frequently change structure, handled by separate scraping services.

| Source | Type | Integration Method | Update Frequency |
|--------|------|-------------------|------------------|
| Blueprint Genetics | Web scraping | Scraping service → API | Manual trigger |
| Invitae | Web scraping | Scraping service → API | Manual trigger |
| GeneDx | Web scraping | Scraping service → API | Manual trigger |
| CeGaT | Web scraping | Scraping service → API | Manual trigger |

### Tier 3: Manual Sources (Upload API)
Data requiring human curation or verification.

| Source | Type | Integration Method | Update Frequency |
|--------|------|-------------------|------------------|
| Literature Excel | Manual upload | Upload API endpoint | As needed |
| Custom gene lists | Manual entry | Form submission | As needed |
| Clinical updates | Manual curation | Admin interface | As needed |

## Architecture Design

```
┌─────────────────────────────────────────────────────────────┐
│                     Main Pipeline (Stable)                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐     ┌──────────────┐                   │
│  │ PanelApp API │────▶│              │                   │
│  └──────────────┘     │              │                   │
│                       │   Pipeline   │                   │
│  ┌──────────────┐     │   Ingestion  │                   │
│  │   HPO API    │────▶│    Engine    │───▶ PostgreSQL   │
│  └──────────────┘     │              │                   │
│                       │              │                   │
│  ┌──────────────┐     │              │                   │
│  │ PubTator API │────▶│              │                   │
│  └──────────────┘     └──────────────┘                   │
│                              ▲                            │
└──────────────────────────────┼────────────────────────────┘
                               │
                               │ Unified API
                               │
┌──────────────────────────────┼────────────────────────────┐
│           External Services  │   (Can fail independently) │
├──────────────────────────────┴────────────────────────────┤
│                                                            │
│  ┌─────────────────────────────────────┐                 │
│  │   Scraping Service (Separate)       │                 │
│  ├─────────────────────────────────────┤                 │
│  │  • Blueprint Genetics scraper       │                 │
│  │  • Invitae scraper                  │────▶ /api/ingest│
│  │  • GeneDx scraper                   │                 │
│  │  • CeGaT scraper                    │                 │
│  └─────────────────────────────────────┘                 │
│                                                            │
│  ┌─────────────────────────────────────┐                 │
│  │   Manual Upload Interface           │                 │
│  ├─────────────────────────────────────┤                 │
│  │  • Literature Excel upload          │────▶ /api/upload│
│  │  • Custom gene list forms           │                 │
│  └─────────────────────────────────────┘                 │
└────────────────────────────────────────────────────────────┘
```

## Implementation Details

### 1. Stable API Sources (app/pipeline/sources/)

```python
# app/pipeline/sources/panelapp.py
from typing import List, Dict
import httpx
from app.core.config import settings

class PanelAppSource:
    """Stable API integration for PanelApp."""
    
    def __init__(self):
        self.uk_base_url = settings.PANELAPP_UK_URL
        self.au_base_url = settings.PANELAPP_AU_URL
        
    async def fetch(self) -> List[Dict]:
        """Fetch kidney-related panels from both PanelApp instances."""
        results = []
        
        # Fetch from UK PanelApp
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.uk_base_url}/panels/")
            panels = response.json()["results"]
            
            for panel in panels:
                if self._is_kidney_related(panel["name"]):
                    panel_detail = await client.get(
                        f"{self.uk_base_url}/panels/{panel['id']}/"
                    )
                    results.extend(self._extract_genes(panel_detail.json()))
        
        return results
    
    def _is_kidney_related(self, name: str) -> bool:
        """Check if panel name is kidney-related."""
        keywords = ["kidney", "renal", "nephro", "glomerul"]
        return any(kw in name.lower() for kw in keywords)
```

### 2. Data Ingestion API (app/api/endpoints/ingestion.py)

```python
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime
from app.api.deps import get_current_admin_user

router = APIRouter()

class GeneEvidence(BaseModel):
    """Schema for ingested gene evidence."""
    gene_symbol: str
    hgnc_id: Optional[str]
    source_name: str
    source_detail: str
    evidence_type: str
    confidence_score: Optional[float] = Field(ge=0, le=1)
    metadata: Dict = {}

class IngestionRequest(BaseModel):
    """Request schema for data ingestion."""
    source_id: str
    source_version: str
    timestamp: datetime
    data: List[GeneEvidence]
    
class IngestionResponse(BaseModel):
    """Response after successful ingestion."""
    request_id: str
    status: str
    genes_processed: int
    genes_accepted: int
    genes_rejected: int
    errors: List[str] = []

@router.post("/api/ingest", response_model=IngestionResponse)
async def ingest_data(
    request: IngestionRequest,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(verify_api_key)
):
    """
    Unified ingestion endpoint for external data sources.
    Used by scraping services and manual uploads.
    """
    # Validate source
    if request.source_id not in ALLOWED_SOURCES:
        raise HTTPException(400, f"Unknown source: {request.source_id}")
    
    # Start background processing
    request_id = str(uuid.uuid4())
    background_tasks.add_task(
        process_ingestion,
        request_id=request_id,
        data=request
    )
    
    return IngestionResponse(
        request_id=request_id,
        status="processing",
        genes_processed=len(request.data),
        genes_accepted=0,
        genes_rejected=0
    )

@router.post("/api/upload/literature")
async def upload_literature(
    file: UploadFile,
    user: User = Depends(get_current_admin_user)
):
    """Manual upload endpoint for literature Excel files."""
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(400, "Only Excel files are accepted")
    
    # Process Excel file
    df = pd.read_excel(file.file)
    
    # Transform to standard format
    genes = []
    for _, row in df.iterrows():
        genes.append(GeneEvidence(
            gene_symbol=row['Gene'],
            source_name="Literature",
            source_detail=row.get('Publication', 'Unknown'),
            evidence_type="manual_curation",
            metadata=row.to_dict()
        ))
    
    # Create ingestion request
    request = IngestionRequest(
        source_id="literature",
        source_version="manual",
        timestamp=datetime.utcnow(),
        data=genes
    )
    
    return await ingest_data(request, BackgroundTasks(), api_key="internal")
```

### 3. Scraping Service (Separate Repository/Container)

```python
# scraping-service/scrapers/blueprint_genetics.py
import asyncio
from typing import List
import httpx
from bs4 import BeautifulSoup
from datetime import datetime

class BlueprintGeneticsScraper:
    """
    Scraper for Blueprint Genetics panels.
    Runs independently and pushes results to main API.
    """
    
    def __init__(self, api_endpoint: str, api_key: str):
        self.api_endpoint = api_endpoint
        self.api_key = api_key
        self.base_url = "https://blueprintgenetics.com"
        
    async def scrape_kidney_panels(self) -> List[Dict]:
        """Scrape kidney-related panels."""
        panels = []
        
        async with httpx.AsyncClient() as client:
            # Get kidney disease panels
            response = await client.get(
                f"{self.base_url}/tests/panels/kidney-disease/"
            )
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract gene lists (implementation specific to website)
            for panel in soup.find_all('div', class_='panel-info'):
                genes = self._extract_genes(panel)
                panels.extend(genes)
        
        return panels
    
    async def push_to_api(self, data: List[Dict]):
        """Push scraped data to main API."""
        request = {
            "source_id": "blueprint_genetics",
            "source_version": "scraper_v1",
            "timestamp": datetime.utcnow().isoformat(),
            "data": data
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_endpoint}/api/ingest",
                json=request,
                headers={"X-API-Key": self.api_key}
            )
            return response.json()
    
    async def run(self):
        """Main scraping workflow."""
        try:
            # Scrape data
            data = await self.scrape_kidney_panels()
            
            # Push to API
            result = await self.push_to_api(data)
            print(f"Pushed {len(data)} genes: {result}")
            
        except Exception as e:
            print(f"Scraping failed: {e}")
            # Log error but don't crash main pipeline

# Run as standalone script
if __name__ == "__main__":
    scraper = BlueprintGeneticsScraper(
        api_endpoint="http://kidney-genetics-api:8000",
        api_key=os.getenv("SCRAPER_API_KEY")
    )
    asyncio.run(scraper.run())
```

### 4. Docker Compose for Scraping Service

```yaml
# docker-compose.scrapers.yml
services:
  scraper-blueprint:
    build: ./scrapers/blueprint
    environment:
      API_ENDPOINT: http://backend:8000
      API_KEY: ${SCRAPER_API_KEY}
    depends_on:
      - backend
    restart: on-failure
    deploy:
      mode: replicated
      replicas: 1
      restart_policy:
        condition: on-failure
        delay: 1h  # Run hourly
```

## API Key Management

```python
# app/core/security.py
from typing import Optional
import secrets

class APIKeyManager:
    """Manage API keys for external services."""
    
    def __init__(self):
        self.keys = {
            # Generated keys for each service
            "scraper_blueprint": self._generate_key(),
            "scraper_invitae": self._generate_key(),
            "manual_upload": self._generate_key(),
        }
    
    def _generate_key(self) -> str:
        """Generate secure API key."""
        return secrets.token_urlsafe(32)
    
    def verify_key(self, key: str, source: Optional[str] = None) -> bool:
        """Verify API key."""
        if source:
            return self.keys.get(source) == key
        return key in self.keys.values()
```

## Monitoring and Error Handling

```python
# app/services/ingestion_monitor.py
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Dict

@dataclass
class IngestionStatus:
    source_id: str
    last_success: datetime
    last_attempt: datetime
    success_count: int
    failure_count: int
    average_genes: float
    
class IngestionMonitor:
    """Monitor health of data ingestion from all sources."""
    
    def check_source_health(self, source_id: str) -> Dict:
        """Check if a source is healthy."""
        status = self.get_status(source_id)
        
        health = {
            "source": source_id,
            "healthy": True,
            "issues": []
        }
        
        # Check last success time
        if datetime.utcnow() - status.last_success > timedelta(days=7):
            health["healthy"] = False
            health["issues"].append("No successful ingestion in 7 days")
        
        # Check failure rate
        total = status.success_count + status.failure_count
        if total > 0 and status.failure_count / total > 0.5:
            health["healthy"] = False
            health["issues"].append("High failure rate")
        
        return health
    
    def get_dashboard_stats(self) -> Dict:
        """Get stats for monitoring dashboard."""
        return {
            "total_sources": len(self.sources),
            "healthy_sources": sum(1 for s in self.sources if self.check_source_health(s)["healthy"]),
            "genes_ingested_today": self.get_today_gene_count(),
            "last_update": self.get_last_update_time()
        }
```

## Benefits of This Architecture

1. **Resilience**: Main pipeline never breaks due to website changes
2. **Flexibility**: Easy to add/remove/update scrapers independently  
3. **Monitoring**: Clear visibility into which sources are working
4. **Scalability**: Scrapers can run on separate servers/containers
5. **Maintainability**: Scraping logic isolated from core business logic
6. **Manual Override**: Can manually upload data when scrapers fail
7. **API Standardization**: All data flows through same validation

## Deployment Strategy

### Production Setup
```bash
# Main application
docker-compose up -d postgres redis backend frontend

# Scraping services (can be on different server)
docker-compose -f docker-compose.scrapers.yml up -d

# Manual upload interface
# Available through admin panel at /admin/upload
```

### Development Setup
```bash
# Run only stable sources locally
python -m app.pipeline.run --sources=panelapp,hpo,pubtator

# Test scraper independently
python scrapers/blueprint_genetics.py --test

# Test ingestion API
curl -X POST http://localhost:8000/api/ingest \
  -H "X-API-Key: test-key" \
  -H "Content-Type: application/json" \
  -d @test_data.json
```

## Fallback Strategies

When scrapers fail:

1. **Manual Upload**: Admin can upload Excel/CSV through web interface
2. **Cached Data**: Use last successful scrape (with warning)
3. **Partial Update**: Process working sources, flag missing ones
4. **Email Alerts**: Notify admin when source fails repeatedly
5. **Historical Data**: Show trends even without latest updates