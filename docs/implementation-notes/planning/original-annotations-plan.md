# Gene Annotation Methods

## Overview

This document describes the comprehensive annotation pipeline implemented in the kidney-genetics-v1 project (`C_AnnotateMergedTable.R`) that enriches gene data with multiple biological and clinical annotations. These methods provide the foundation for implementing similar annotations in the kidney-genetics-db backend.

## Data Sources and Annotations

### 1. HPO Ontology Classification

**Purpose**: Classify genes based on phenotype associations using Human Phenotype Ontology (HPO) terms.

**Data Sources**:
- **HPO OBO file**: Download from https://hpo.jax.org/app/data/ontology
- **Phenotype annotations (phenotype.hpoa)**: Download from HPO downloads page
- **Access Type**: Direct file download
- **Update Frequency**: Monthly

**Method**:
- Downloads HPO OBO file (monthly updates)
- Traverses ontology tree to identify kidney-related phenotypes (HP:0010935 - Abnormality of the upper urinary tract)
- Computes relative frequency of HPO terms per gene/disease combination
- Generates probability scores for clinical classification

**Key Classifications**:
- **Kidney Disease Groups**: Identifies genes associated with specific kidney phenotypes
- **Onset Groups**: 
  - Adult onset (HP:0003581)
  - Antenatal/Congenital (HP:0030674/HP:0003577)
  - Neonatal/Pediatric (HP:0003623/HP:0410280)
- **Syndromic Features**:
  - Growth abnormality (HP:0001507)
  - Skeletal system abnormality (HP:0000924)
  - Neurologic abnormality (HP:0000707)
  - Head and neck abnormality (HP:0000152)

### 2. Clinical Disease Groups

**Purpose**: Categorize genes into specific kidney disease groups based on expert panel curation.

**Data Sources**:
- **PanelApp UK**: REST API - https://panelapp.genomicsengland.co.uk/api/v1/panels/
- **PanelApp Australia**: REST API - https://panelapp.agha.umccr.org/api/v1/panels/
- **ClinGen**: Web scraping from https://www.clinicalgenome.org/affiliation/
- **ClinGen Gene Curation**: REST API - https://search.clinicalgenome.org/api/
- **Access Type**: REST APIs and web scraping
- **Update Frequency**: Real-time API queries

**Categories**:
1. **Complement-Mediated Kidney Diseases** (PanelApp Panel 224)
2. **Congenital Anomalies of Kidney and Urinary Tract (CAKUT)** (PanelApp Panel 234)
3. **Glomerulopathy** (ClinGen GCEP)
4. **Kidney Cystic and Ciliopathy Disorders** (ClinGen GCEP)
5. **Tubulopathy** (ClinGen GCEP)
6. **Hereditary Cancer** (ClinGen GCEP)
7. **Nephrocalcinosis/Nephrolithiasis** (PanelApp Panel 149)

**Scoring Method**:
- Calculates relative frequency of kidney-specific HPO terms for each disease group
- Generates probability scores (0-1) for group membership
- Format: `OMIM:123456 (cakut: 0.75 | glomerulopathy: 0.25)`

### 3. Mouse Model Phenotypes (MGI)

**Purpose**: Identify genes with kidney phenotypes in mouse models.

**Data Sources**:
- **MPO OBO file**: Download from http://www.informatics.jax.org/downloads/reports/
- **MouseMine database**: REST API via InterMineR - https://www.mousemine.org/mousemine/
- **Access Type**: File download (MPO) + REST API (MouseMine)
- **Update Frequency**: Monthly download, real-time API queries

**Method**:
- Downloads Mammalian Phenotype Ontology (MPO) OBO file
- Identifies renal/urinary system phenotypes (MP:0005367)
- Queries MouseMine database via InterMineR API
- Compares human gene symbols with mouse orthologs
- Returns kidney-related phenotypes observed in knockout models

**Output**: Boolean indicator for presence of kidney phenotypes in mouse models

### 4. Protein-Protein Interactions (STRING)

**Purpose**: Quantify protein interaction networks with known kidney disease genes.

**Data Sources**:
- **STRING database**: Download from https://string-db.org/
- **File**: 9606.protein.physical.links.v12.0.txt.gz
- **Access Type**: Direct file download
- **Update Frequency**: Per STRING version release

**Method**:
- Downloads STRING database protein interaction data (physical links)
- Maps genes to STRING protein IDs
- Calculates interaction scores with high-evidence kidney genes
- Normalizes scores using percentile ranking

**Scoring**:
- **0 points**: Below one standard deviation (< 16th percentile)
- **0.5 points**: Within normal range (16-84th percentile)
- **1 point**: Above one standard deviation (> 84th percentile)

**Output**: 
- `interaction_score`: Categorical score (0, 0.5, 1)
- `stringdb_interaction_sum_score`: Raw sum of interaction scores
- `stringdb_interaction_normalized_score`: Percentile-normalized score
- `stringdb_interaction_string`: List of interacting proteins with scores

### 5. Expression Analysis

**Purpose**: Assess kidney-specific gene expression levels.

**Data Sources**:
- **GTEx Portal**: REST API - https://gtexportal.org/api/v2/
- **Descartes**: File download/API - https://descartes.brotmanbaty.org/
- **Access Type**: REST APIs
- **Update Frequency**: Real-time API queries

**Scoring Thresholds**:

**GTEx Categories**:
- Low: < 98 TPM (0 points)
- Medium: 98-2100 TPM (0.5 points)
- High: > 2100 TPM (1 point)

**Descartes/EBI Categories**:
- Low: < 10 TPM (0 points)
- Medium: 10-1000 TPM (0.5 points)
- High: > 1000 TPM (1 point)

**Output**:
- `expression_score`: Maximum score across all tissues
- `gtex_kidney_medulla`: Median TPM in kidney medulla
- `gtex_kidney_cortex`: Median TPM in kidney cortex
- `descartes_kidney_tpm`: TPM in embryonic kidney

### 6. ClinVar Variant Counts

**Purpose**: Quantify pathogenic variant burden per gene.

**Data Sources**:
- **ClinVar**: FTP download from ftp://ftp.ncbi.nlm.nih.gov/pub/clinvar/
- **File**: variant_summary.txt.gz
- **Access Type**: FTP file download
- **Update Frequency**: Weekly updates available

**Method**:
- Parses ClinVar summary file
- Counts pathogenic/likely pathogenic variants
- Excludes benign and VUS classifications

**Output**: Total count of P/LP variants per gene

### 7. gnomAD Constraint Scores

**Purpose**: Assess evolutionary constraint and mutation intolerance.

**Data Sources**:
- **gnomAD**: Download from https://gnomad.broadinstitute.org/downloads
- **File**: gnomad.v2.1.1.lof_metrics.by_gene.txt.bgz
- **Access Type**: Direct file download (integrated via HGNC)
- **Update Frequency**: Per gnomAD release

**Metrics**:
- **pLI**: Probability of loss-of-function intolerance (0-1)
- **oe_lof**: Observed/expected ratio for LoF variants
- **lof_z**: Z-score for LoF constraint
- **mis_z**: Z-score for missense constraint

### 8. OMIM Disease Associations

**Purpose**: Link genes to OMIM disease entries with inheritance patterns.

**Data Sources**:
- **OMIM**: Download from https://www.omim.org/downloads (requires license)
- **File**: genemap2.txt
- **Access Type**: Direct file download (requires registration)
- **Update Frequency**: Daily updates available

**Method**:
- Parses OMIM genemap2 file
- Extracts disease-gene associations
- Maps inheritance patterns to HPO terms
- Provides disease names and OMIM IDs

**Output**: 
- Disease ontology IDs (OMIM:xxxxxx)
- Disease names
- Inheritance patterns (AD, AR, XL, etc.)

## Implementation Workflow

### 1. Data Preparation
- Load merged gene table from previous analyses
- Filter for high-evidence genes (>1 source)
- Load HGNC annotation table for gene identifiers

### 2. Ontology Processing
- Download and parse HPO/MPO OBO files
- Build ontology trees for term relationships
- Cache processed ontology data (1-month expiry)

### 3. API Integration
- Query PanelApp APIs for gene panels
- Scrape ClinGen websites for expert-curated lists
- Access GTEx and MouseMine via REST APIs

### 4. Score Calculation
- Compute relative frequencies for phenotype associations
- Normalize interaction and expression scores
- Apply categorical thresholds for scoring

### 5. Data Integration
- Join all annotation sources by HGNC ID
- Add unique curation IDs (cur_XXX format)
- Generate final annotated table

## Output Format

Final table includes:
- **Gene identifiers**: approved_symbol, hgnc_id
- **Evidence metrics**: evidence_count, source_count_percentile
- **Constraint scores**: pLI, oe_lof, lof_z, mis_z
- **Clinical summaries**: OMIM, GenCC, ClinGen, ClinVar
- **Disease groups**: clinical_groups_p, onset_groups_p, syndromic_groups_p
- **Functional annotations**: mgi_phenotype, interaction_score, expression_score
- **Curation fields**: cur_id, publication_score (empty for manual entry)

## Caching Strategy

- **Ontology files**: 1-month cache
- **API results**: 1-month cache for expensive computations
- **Expression data**: Cached per gene batch
- **File format**: CSV with gzip compression
- **Naming convention**: `{analysis_name}.{date}.csv.gz`

## Future Enhancements

Planned improvements identified in the original implementation:
- Use MONDO ontology instead of OMIM for disease classification
- Add GeneReviews publication annotations
- Implement phenopackets format for phenotype data
- Enhance publication scoring (screening: 1pt, clinical: 2pts, replication: 3pts)
- Move hardcoded values to configuration files
- Add automated evidence category assignment (Limited/Moderate/Definitive)

## Data Access Summary

| Data Source | Access Type | Update Frequency | Authentication |
|-------------|------------|------------------|----------------|
| HPO Ontology | File Download | Monthly | None |
| MPO Ontology | File Download | Monthly | None |
| PanelApp UK/AU | REST API | Real-time | None |
| ClinGen | REST API + Scraping | Real-time | None |
| MouseMine/MGI | REST API | Real-time | None |
| STRING | File Download | Per release | None |
| GTEx | REST API | Real-time | None |
| Descartes | API/Download | Real-time | None |
| ClinVar | FTP Download | Weekly | None |
| gnomAD | File Download | Per release | None |
| OMIM | File Download | Daily | License required |
| HGNC | REST API | Real-time | None |

## Configuration Requirements

Required configuration parameters:
- HPO OBO URL: https://hpo.jax.org/app/data/ontology
- MPO OBO URL: http://www.informatics.jax.org/downloads/reports/
- OMIM download credentials (requires registration)
- PanelApp API endpoints (UK and Australia)
- GTEx API access: https://gtexportal.org/api/v2/
- STRING database version and download URL
- File paths and working directories

## Dependencies

- R libraries: tidyverse, jsonlite, rvest, readr, tools, R.utils, config, ontologyIndex
- External APIs: HGNC, HPO, PanelApp, GTEx, MouseMine, STRING
- Local functions: hgnc-functions.R, hpo-functions.R, gtex-functions.R, mpo-mousemine-functions.R