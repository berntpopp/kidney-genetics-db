# Flexible Gene Curation Workflow Plan

**GitHub Issue**: #26
**Status**: Planning
**Priority**: Medium-High
**Effort**: 7-10 days

## Problem Statement

Current system lacks structured expert curation:
- No distinction between automated pipeline data and manual curation
- Missing structured evidence tracking (genetic, functional, clinical)
- No workflow states (draft → review → published)
- No gene-disease association support
- No curator attribution or review process

**Need**: Balance automated aggregation with expert manual curation. ClinGen-inspired but adapted for kidney genetics research.

## Proposed Solution

**Dual-Track Curation System**

### Design Philosophy

- **Automated track**: Pipeline data (current) remains fast
- **Manual track**: Expert curation overlay for quality control
- **Flexible schema**: JSONB evidence, extensible structure
- **ClinGen-inspired**: Use concepts (evidence tiers, validity) without strict compliance
- **Template-driven**: Curators define their own evidence structures

## Architecture

```
┌─────────────────────────────────────────┐
│  Automated Pipeline (Current)           │
│  - PanelApp, ClinGen, GenCC, etc.       │
│  - Runs nightly, updates genes          │
└─────────────────┬───────────────────────┘
                  │
                  ↓
┌─────────────────────────────────────────┐
│  Gene Table (Base Data)                 │
│  - HGNC info, basic annotations         │
└─────────────────┬───────────────────────┘
                  │
                  ↓
┌─────────────────────────────────────────┐
│  Gene-Disease Associations (Manual)     │
│  - Curator creates association          │
│  - Flexible JSONB evidence              │
│  - Workflow: draft → review → published │
│  - Curator + reviewer attribution       │
└─────────────────────────────────────────┘
```

## Database Schema

### Core Model: Gene-Disease Association

```sql
-- File: backend/alembic/versions/XXXX_add_gene_curation.py

CREATE TABLE gene_disease_associations (
    id BIGSERIAL PRIMARY KEY,

    -- Core relationship
    gene_id BIGINT NOT NULL REFERENCES genes(id),
    disease_name VARCHAR(200) NOT NULL,
    disease_id VARCHAR(50),  -- MONDO:xxx, OMIM:xxx, HPO:xxx, or null

    -- Flexible JSONB evidence
    evidence_summary JSONB,  -- Start simple: {"genetic": 5, "functional": 3, "total": 8}

    -- Workflow
    curation_source VARCHAR(20) DEFAULT 'manual',  -- automated/manual/hybrid
    status VARCHAR(20) DEFAULT 'draft',  -- draft/in_review/published
    evidence_strength VARCHAR(20),  -- Definitive/Strong/Moderate/Limited

    -- Attribution
    curator_id INTEGER REFERENCES users(id),
    reviewer_id INTEGER REFERENCES users(id),

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    submitted_at TIMESTAMPTZ,
    published_at TIMESTAMPTZ,

    -- Metadata
    notes TEXT,
    references JSONB,  -- Array of PMIDs, URLs

    UNIQUE(gene_id, disease_name, disease_id)
);

CREATE INDEX idx_gene_disease_gene ON gene_disease_associations(gene_id);
CREATE INDEX idx_gene_disease_status ON gene_disease_associations(status);
CREATE INDEX idx_gene_disease_curator ON gene_disease_associations(curator_id);
CREATE INDEX idx_gene_disease_evidence ON gene_disease_associations USING gin(evidence_summary);

-- Comment threads
CREATE TABLE curation_comments (
    id BIGSERIAL PRIMARY KEY,
    association_id BIGINT REFERENCES gene_disease_associations(id),
    user_id INTEGER REFERENCES users(id),
    comment_text TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    resolved BOOLEAN DEFAULT FALSE
);

-- Curation templates
CREATE TABLE curation_templates (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    evidence_schema JSONB,  -- Defines structure for evidence_summary
    created_by_id INTEGER REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Example Evidence Structures

**Simple scoring:**
```json
{
  "genetic": 8,
  "functional": 4,
  "total": 12
}
```

**Detailed ClinGen-like:**
```json
{
  "genetic": {
    "case_level": 5,
    "segregation": 2,
    "case_control": 1
  },
  "experimental": {
    "functional": 2,
    "model": 2
  },
  "total": 12,
  "classification": "Strong"
}
```

**Custom kidney-specific:**
```json
{
  "genetic_evidence": {
    "pathogenic_variants": 10,
    "segregation_studies": 5,
    "population_data": 2
  },
  "functional_evidence": {
    "expression_kidney": 3,
    "mouse_model_phenotype": 4,
    "protein_interaction": 2
  },
  "clinical_evidence": {
    "kidney_phenotype_specificity": 5,
    "age_of_onset_consistency": 3
  },
  "total": 34,
  "validity": "Definitive"
}
```

## Backend Implementation

### 1. Models

```python
# backend/app/models/gene_disease_association.py

from sqlalchemy import Column, BigInteger, String, Text, Integer, ForeignKey, DateTime, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.db.database import Base

class GeneDiseaseAssociation(Base):
    __tablename__ = "gene_disease_associations"

    id = Column(BigInteger, primary_key=True)

    # Relationship
    gene_id = Column(BigInteger, ForeignKey("genes.id"), nullable=False)
    disease_name = Column(String(200), nullable=False)
    disease_id = Column(String(50))  # Optional ontology ID

    # Evidence (flexible JSONB)
    evidence_summary = Column(JSONB)

    # Workflow
    curation_source = Column(String(20), default="manual")
    status = Column(String(20), default="draft")
    evidence_strength = Column(String(20))

    # Attribution
    curator_id = Column(Integer, ForeignKey("users.id"))
    reviewer_id = Column(Integer, ForeignKey("users.id"))

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    submitted_at = Column(DateTime(timezone=True))
    published_at = Column(DateTime(timezone=True))

    # Metadata
    notes = Column(Text)
    references = Column(JSONB)  # PMIDs, URLs, etc.

    # Relationships
    gene = relationship("Gene", back_populates="disease_associations")
    curator = relationship("User", foreign_keys=[curator_id])
    reviewer = relationship("User", foreign_keys=[reviewer_id])
    comments = relationship("CurationComment", back_populates="association")

class CurationComment(Base):
    __tablename__ = "curation_comments"

    id = Column(BigInteger, primary_key=True)
    association_id = Column(BigInteger, ForeignKey("gene_disease_associations.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    comment_text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved = Column(Boolean, default=False)

    association = relationship("GeneDiseaseAssociation", back_populates="comments")
    user = relationship("User")

class CurationTemplate(Base):
    __tablename__ = "curation_templates"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    evidence_schema = Column(JSONB)
    created_by_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

### 2. Curation Service

```python
# backend/app/services/curation_service.py

from sqlalchemy.orm import Session
from app.models.gene_disease_association import GeneDiseaseAssociation
from datetime import datetime

class CurationService:
    def __init__(self, db: Session):
        self.db = db

    async def create_association(
        self,
        gene_id: int,
        disease_name: str,
        disease_id: str | None,
        curator_id: int,
        evidence_summary: dict = None
    ) -> GeneDiseaseAssociation:
        """Create new gene-disease association"""

        association = GeneDiseaseAssociation(
            gene_id=gene_id,
            disease_name=disease_name,
            disease_id=disease_id,
            curator_id=curator_id,
            evidence_summary=evidence_summary or {},
            status="draft",
            curation_source="manual"
        )

        self.db.add(association)
        self.db.commit()
        self.db.refresh(association)

        return association

    async def submit_for_review(self, association_id: int) -> GeneDiseaseAssociation:
        """Submit association for review"""

        association = self.db.query(GeneDiseaseAssociation).get(association_id)

        if association.status != "draft":
            raise ValueError("Only draft associations can be submitted")

        association.status = "in_review"
        association.submitted_at = datetime.now()

        self.db.commit()
        return association

    async def publish_association(
        self,
        association_id: int,
        reviewer_id: int
    ) -> GeneDiseaseAssociation:
        """Publish association (reviewer action)"""

        association = self.db.query(GeneDiseaseAssociation).get(association_id)

        if association.status != "in_review":
            raise ValueError("Only associations in review can be published")

        association.status = "published"
        association.reviewer_id = reviewer_id
        association.published_at = datetime.now()

        self.db.commit()
        return association

    async def update_evidence(
        self,
        association_id: int,
        evidence_summary: dict
    ) -> GeneDiseaseAssociation:
        """Update evidence summary"""

        association = self.db.query(GeneDiseaseAssociation).get(association_id)

        if association.status == "published":
            raise ValueError("Cannot modify published associations")

        association.evidence_summary = evidence_summary
        self.db.commit()

        return association
```

## API Endpoints

```python
# backend/app/api/endpoints/curation.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.auth import get_current_curator, get_current_reviewer
from app.services.curation_service import CurationService

router = APIRouter()

@router.post("/associations")
async def create_association(
    gene_id: int,
    disease_name: str,
    disease_id: str | None = None,
    evidence_summary: dict = {},
    db: Session = Depends(get_db),
    current_user = Depends(get_current_curator)
):
    """Create new gene-disease association (curator only)"""
    service = CurationService(db)
    return await service.create_association(
        gene_id, disease_name, disease_id, current_user.id, evidence_summary
    )

@router.get("/associations")
async def list_associations(
    status: str | None = None,
    curator_id: int | None = None,
    db: Session = Depends(get_db)
):
    """List associations with filters"""
    query = db.query(GeneDiseaseAssociation)

    if status:
        query = query.filter_by(status=status)
    if curator_id:
        query = query.filter_by(curator_id=curator_id)

    return query.all()

@router.get("/associations/{id}")
async def get_association(id: int, db: Session = Depends(get_db)):
    """Get association details"""
    association = db.query(GeneDiseaseAssociation).get(id)
    if not association:
        raise HTTPException(404)
    return association

@router.put("/associations/{id}")
async def update_association(
    id: int,
    evidence_summary: dict,
    notes: str = "",
    db: Session = Depends(get_db),
    current_user = Depends(get_current_curator)
):
    """Update association (curator only)"""
    service = CurationService(db)
    association = await service.update_evidence(id, evidence_summary)
    association.notes = notes
    db.commit()
    return association

@router.post("/associations/{id}/submit")
async def submit_association(
    id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_curator)
):
    """Submit for review (curator only)"""
    service = CurationService(db)
    return await service.submit_for_review(id)

@router.post("/associations/{id}/publish")
async def publish_association(
    id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_reviewer)
):
    """Publish association (reviewer only)"""
    service = CurationService(db)
    return await service.publish_association(id, current_user.id)

@router.post("/associations/{id}/comments")
async def add_comment(
    id: int,
    comment_text: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_curator)
):
    """Add comment to association"""
    comment = CurationComment(
        association_id=id,
        user_id=current_user.id,
        comment_text=comment_text
    )
    db.add(comment)
    db.commit()
    return comment
```

## Frontend Implementation

### 1. Curation Form

```vue
<!-- frontend/src/views/CurationFormPage.vue -->
<template>
  <v-container>
    <h1 class="text-h4 mb-4">Create Gene-Disease Association</h1>

    <v-form v-model="valid" @submit.prevent="saveAssociation">
      <!-- Gene Selection -->
      <v-autocomplete
        v-model="form.gene_id"
        :items="genes"
        item-title="approved_symbol"
        item-value="id"
        label="Gene"
        required
      />

      <!-- Disease Info -->
      <v-text-field v-model="form.disease_name" label="Disease Name" required />
      <v-text-field v-model="form.disease_id" label="Disease ID (MONDO/OMIM/HPO)" />

      <!-- Evidence Template Selection -->
      <v-select
        v-model="selectedTemplate"
        :items="templates"
        item-title="name"
        item-value="id"
        label="Evidence Template"
        @update:model-value="loadTemplate"
      />

      <!-- Evidence Entry (Template-based) -->
      <div v-if="templateSchema">
        <h3 class="text-h6 mt-4 mb-2">Evidence Summary</h3>

        <div v-for="(field, key) in templateSchema" :key="key" class="mb-4">
          <v-label>{{ field.label }}</v-label>

          <!-- Slider for numeric scores -->
          <v-slider
            v-if="field.type === 'number'"
            v-model="form.evidence_summary[key]"
            :min="field.min || 0"
            :max="field.max || 10"
            :step="field.step || 1"
            thumb-label
          >
            <template #append>
              <v-text-field
                v-model="form.evidence_summary[key]"
                type="number"
                style="width: 80px"
                density="compact"
                hide-details
              />
            </template>
          </v-slider>

          <!-- Text input for nested objects -->
          <v-text-field
            v-else-if="field.type === 'text'"
            v-model="form.evidence_summary[key]"
            :hint="field.description"
          />
        </div>
      </div>

      <!-- Notes -->
      <v-textarea v-model="form.notes" label="Curation Notes" rows="3" />

      <!-- References -->
      <v-combobox
        v-model="form.references"
        label="References (PMIDs, URLs)"
        multiple
        chips
      />

      <!-- Actions -->
      <v-card-actions>
        <v-btn type="submit" color="primary">Save Draft</v-btn>
        <v-btn @click="submitForReview" :disabled="!valid" color="success">Submit for Review</v-btn>
        <v-btn to="/curation" variant="text">Cancel</v-btn>
      </v-card-actions>
    </v-form>
  </v-container>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '@/services/api'

const valid = ref(false)
const form = ref({
  gene_id: null,
  disease_name: '',
  disease_id: '',
  evidence_summary: {},
  notes: '',
  references: []
})

const genes = ref([])
const templates = ref([])
const selectedTemplate = ref(null)
const templateSchema = ref(null)

onMounted(async () => {
  genes.value = (await api.get('/genes')).data.items
  templates.value = (await api.get('/curation/templates')).data
})

function loadTemplate(templateId) {
  const template = templates.value.find(t => t.id === templateId)
  if (template) {
    templateSchema.value = template.evidence_schema
    form.value.evidence_summary = {}
  }
}

async function saveAssociation() {
  await api.post('/curation/associations', form.value)
  // Navigate to list
}

async function submitForReview() {
  const association = await api.post('/curation/associations', form.value)
  await api.post(`/curation/associations/${association.data.id}/submit`)
  // Navigate to list
}
</script>
```

## Implementation Timeline

### Week 1: Database & Backend Foundation (3-4 days)
- [ ] Create migration for association tables
- [ ] `GeneDiseaseAssociation` model
- [ ] `CurationComment` model
- [ ] `CurationTemplate` model
- [ ] `CurationService` implementation

### Week 2: API & Workflow (2-3 days)
- [ ] CRUD endpoints for associations
- [ ] Workflow endpoints (submit, publish)
- [ ] Comment endpoints
- [ ] Template endpoints
- [ ] Role enforcement (curator/reviewer)

### Week 3: Frontend (3-4 days)
- [ ] Curation form component
- [ ] Template-based evidence entry
- [ ] Association list view
- [ ] Review interface for reviewers
- [ ] Comment threads
- [ ] Pinia store for curation state

## Acceptance Criteria

**Database**:
- [ ] Tables created with proper indexes
- [ ] JSONB evidence column flexible
- [ ] Workflow states enforced
- [ ] Attribution tracking (curator + reviewer)

**Backend**:
- [ ] CurationService with create/submit/publish
- [ ] API endpoints with role enforcement
- [ ] Audit trail (timestamps, user IDs)
- [ ] Support for templates

**Frontend**:
- [ ] Curation form with gene/disease selection
- [ ] Template-based evidence entry (sliders)
- [ ] Workflow buttons (save/submit/publish)
- [ ] Comment threads functional

**Flexibility**:
- [ ] Ontology IDs optional (MONDO, OMIM, HPO, or free text)
- [ ] JSONB allows simple or complex structures
- [ ] Templates user-definable

## Future Enhancements

- [ ] ClinGen-specific scoring matrices
- [ ] More workflow states (needs_revision, rejected)
- [ ] External ontology integration (MONDO API)
- [ ] Bulk import from ClinGen JSON
- [ ] Evidence file attachments
- [ ] Version history tracking
- [ ] Automated evidence extraction from literature

## References

- **ClinGen Gene-Disease Validity**: https://clinicalgenome.org/curation-activities/gene-disease-validity/
- **MONDO Disease Ontology**: https://mondo.monarchinitiative.org/
- **HPO Terms**: https://hpo.jax.org/
- **GitHub Issue**: #26
