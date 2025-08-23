# Data Visualization Enhancement Plan for Kidney Genetics Database

## Overview
Implement comprehensive data visualization endpoints and interactive charts following the Kidney Genetics v1 approach, featuring UpSet plots for data source overlaps and bar plots for individual source statistics.

## Current Data Architecture Analysis

### Available Data Sources (6 active sources)
- **ClinGen**: Expert panels with clinical validity classifications
- **GenCC**: Gene curation submissions from consortium members  
- **HPO**: Human Phenotype Ontology phenotype terms
- **PubTator**: Literature mining from PubMed publications
- **PanelApp**: Clinical gene panels (UK/Australia)
- **DiagnosticPanels**: Commercial diagnostic laboratory panels

### Database Structure
- `genes`: Core gene information (HGNC ID, approved symbol)
- `gene_evidence`: Source-specific evidence with JSONB data
- `gene_curations`: Aggregated evidence scores and classifications

## Implementation Plan

### Phase 1: Backend Statistics API Endpoints

#### 1.1 Source Overlap Statistics Endpoint
**Endpoint**: `GET /api/statistics/source-overlaps`

**Purpose**: Generate data for UpSet plots showing gene intersections between data sources

**Response Structure**:
```json
{
  "data": {
    "sets": [
      {"name": "ClinGen", "size": 245},
      {"name": "GenCC", "size": 198}, 
      {"name": "HPO", "size": 432},
      {"name": "PubTator", "size": 1856},
      {"name": "PanelApp", "size": 167},
      {"name": "DiagnosticPanels", "size": 523}
    ],
    "intersections": [
      {"sets": ["ClinGen"], "size": 12, "genes": ["GENE1", "GENE2"]},
      {"sets": ["ClinGen", "GenCC"], "size": 89, "genes": ["GENE3", "GENE4"]},
      {"sets": ["ClinGen", "GenCC", "HPO"], "size": 177, "genes": ["HNF1B", "PKD1"]},
      // ... all possible intersections
    ],
    "total_unique_genes": 571,
    "overlap_statistics": {
      "highest_overlap_count": 6,
      "genes_in_all_sources": 177,
      "single_source_genes": 234
    }
  }
}
```

#### 1.2 Individual Source Statistics Endpoint  
**Endpoint**: `GET /api/statistics/source-distributions`

**Purpose**: Generate data for bar plots showing source count distributions

**Response Structure**:
```json
{
  "data": {
    "PanelApp": {
      "distribution": [
        {"source_count": 1, "gene_count": 38},
        {"source_count": 2, "gene_count": 45}, 
        {"source_count": 30, "gene_count": 2}
      ],
      "metadata": {
        "total_panels": 30,
        "max_panels_per_gene": 30,
        "avg_panels_per_gene": 3.2
      }
    },
    "PubTator": {
      "distribution": [
        {"source_count": 1, "gene_count": 914},
        {"source_count": 1221, "gene_count": 1}
      ],
      "metadata": {
        "total_publications": 1221,
        "max_publications_per_gene": 1221,
        "avg_publications_per_gene": 12.4
      }
    }
    // ... other sources
  }
}
```

#### 1.3 Enhanced Evidence Composition Endpoint
**Endpoint**: `GET /api/statistics/evidence-composition`

**Purpose**: Detailed breakdown of evidence types and quality scores

**Response Structure**:
```json
{
  "data": {
    "evidence_quality_distribution": [
      {"score_range": "0.9-1.0", "gene_count": 45, "label": "High Confidence"},
      {"score_range": "0.7-0.9", "gene_count": 123, "label": "Medium Confidence"},
      {"score_range": "0.5-0.7", "gene_count": 234, "label": "Low Confidence"}
    ],
    "source_contribution_weights": {
      "ClinGen": 0.35,
      "GenCC": 0.25, 
      "PanelApp": 0.20,
      "HPO": 0.10,
      "PubTator": 0.05,
      "DiagnosticPanels": 0.05
    }
  }
}
```

### Phase 2: Frontend Visualization Components

#### 2.1 Technology Stack Selection

**Primary Libraries**:
- **UpSet.js** (`@upsetjs/vue`) - UpSet plots for source intersections (specialized tool)
- **vue-data-ui** (`vue-data-ui`) - All other visualizations (bar charts, compositions, dashboards)

**Benefits of This Stack**:
- Single library (vue-data-ui) handles 90% of visualizations
- Specialized UpSet.js only for the one visualization vue-data-ui cannot create
- Consistent styling and theming across components
- Built-in export capabilities (PDF, PNG, CSV) in vue-data-ui
- Reduced complexity compared to multiple charting libraries

**Component Architecture**:
```
frontend/src/components/statistics/
├── UpSetPlot.vue           # Source intersection visualization
├── SourceDistribution.vue  # Bar charts for individual sources
├── EvidenceComposition.vue # Evidence quality breakdown
├── StatisticsOverview.vue  # Summary dashboard component
└── shared/
    ├── ChartContainer.vue  # Reusable chart wrapper with Vuetify styling
    └── ExportControls.vue  # PDF/PNG/SVG export functionality
```

#### 2.2 UpSet Plot Component (`UpSetPlot.vue`)

**Features**:
- Interactive set intersection visualization
- Hover highlighting with gene lists
- Drill-down to specific gene intersections
- Export capabilities (PNG/PDF/SVG)

**Implementation**:
```vue
<template>
  <ChartContainer title="Data Source Overlaps" :loading="loading">
    <UpSetVue 
      :sets="upsetData.sets"
      :intersections="upsetData.intersections"
      :width="chartWidth"
      :height="600"
      @selection="onIntersectionSelect"
      @hover="onIntersectionHover"
    />
    <template #export>
      <ExportControls @export="handleExport" />
    </template>
  </ChartContainer>
</template>
```

#### 2.3 Source Distribution Component (`SourceDistribution.vue`)

**Features**:
- Individual source bar charts using vue-data-ui
- Source count vs gene count visualizations  
- Interactive tooltips with detailed statistics
- Built-in export capabilities (PDF, PNG, CSV)
- Comparative view between sources

**Implementation**:
```vue
<template>
  <v-row>
    <v-col v-for="source in sources" :key="source.name" cols="12" md="6">
      <ChartContainer :title="`${source.display_name} Distribution`">
        <VueUiVerticalBar 
          :dataset="getBarChartData(source)"
          :config="barChartConfig"
          @selectLegend="onLegendSelect"
        />
      </ChartContainer>
    </v-col>
  </v-row>
</template>
```

#### 2.4 Statistics Dashboard Component (`StatisticsOverview.vue`)

**Features**:
- Comprehensive overview with multiple visualization types
- Real-time data updates via WebSocket integration
- Responsive layout for desktop and mobile
- Contextual help and explanations

### Phase 3: Advanced Visualization Features

#### 3.1 Interactive Features
- **Gene Selection**: Click on intersections/bars to view gene lists
- **Real-time Updates**: WebSocket integration for live data updates
- **Filtering**: Filter by evidence score, source type, classification
- **Drill-down**: Navigate from overview to detailed gene information

#### 3.2 Export and Sharing
- **Multiple Formats**: PNG, PDF, SVG export for all charts
- **Data Export**: CSV/JSON export of underlying statistics
- **Permalink Generation**: Shareable URLs for specific visualizations
- **Report Generation**: Combined PDF reports with multiple visualizations

#### 3.3 Performance Optimization
- **Lazy Loading**: Load chart components only when needed
- **Data Caching**: Cache statistics data with smart invalidation
- **Progressive Loading**: Stream large datasets progressively
- **Responsive Design**: Optimize for mobile and tablet viewing

### Phase 4: Implementation Steps

#### 4.1 Backend Implementation (Days 1-2)
1. Create statistics calculation functions in `backend/app/crud/statistics.py`
2. Implement new API endpoints in `backend/app/api/endpoints/statistics.py`
3. Add route registration in main API router
4. Create Pydantic schemas for statistics responses
5. Add comprehensive test coverage

#### 4.2 Frontend Setup (Day 3)
1. Install visualization libraries: `@upsetjs/vue`, `vue-data-ui`
2. Create base chart components with Vuetify styling
3. Set up routing for statistics views
4. Implement data fetching utilities

#### 4.3 Core Visualizations (Days 4-5)
1. Implement UpSet plot component with @upsetjs/vue
2. Create source distribution bar charts with vue-data-ui (`VueUiVerticalBar`)
3. Build evidence composition visualizations with vue-data-ui components
4. Add interactive features and event handling

#### 4.4 Advanced Features (Days 6-7)
1. Implement export functionality across all charts
2. Add real-time updates via WebSocket integration
3. Create comprehensive statistics dashboard
4. Add mobile responsiveness and accessibility features

#### 4.5 Testing and Documentation (Day 8)
1. Write unit tests for statistics endpoints
2. Add integration tests for visualization components
3. Create user documentation with examples
4. Performance testing and optimization

## Technical Specifications

### API Endpoint Requirements
- **Performance**: Sub-500ms response times for all statistics endpoints
- **Caching**: Redis-based caching with smart invalidation
- **Pagination**: Support for large dataset handling
- **Error Handling**: Comprehensive error responses with fallback data

### Frontend Requirements  
- **Accessibility**: WCAG 2.1 AA compliance for all visualizations
- **Performance**: Sub-2s initial load time for statistics page
- **Responsiveness**: Support for screen sizes 320px+ width
- **Browser Support**: Modern browsers (Chrome 90+, Firefox 88+, Safari 14+)

### Data Processing Requirements
- **Real-time Calculation**: Generate statistics on-demand from current data
- **Scalability**: Support for 10,000+ genes and 50,000+ evidence records
- **Accuracy**: Exact counts with proper handling of duplicates and overlaps

## Success Metrics

### User Experience
- **Engagement**: 40% of users interact with visualizations beyond initial load
- **Utility**: Users spend average 3+ minutes exploring statistics
- **Discoverability**: 70% of users discover new insights about gene overlaps

### Technical Performance
- **Response Time**: 95th percentile < 1s for all API calls
- **Uptime**: 99.9% availability for statistics endpoints
- **Error Rate**: < 0.1% error rate for visualization rendering

### Data Insights
- **Coverage Analysis**: Clear identification of data source gaps
- **Quality Assessment**: Evidence strength visualization across sources
- **Research Value**: Enable hypothesis generation about gene-disease relationships

## Risk Assessment & Mitigation

### Technical Risks
- **Performance**: Large dataset visualization performance → Use data sampling and progressive loading
- **Compatibility**: Library version conflicts → Pin exact versions and test thoroughly
- **Complexity**: UpSet.js integration complexity → Start with simple implementation, add features incrementally

### Data Risks  
- **Accuracy**: Statistical calculation errors → Comprehensive unit testing and validation
- **Consistency**: Source data format changes → Robust error handling and fallback strategies
- **Privacy**: Sensitive gene information exposure → Implement proper access controls

### User Experience Risks
- **Usability**: Complex visualizations confusing users → Progressive disclosure and contextual help
- **Performance**: Slow chart loading → Implement loading states and progressive enhancement
- **Mobile**: Poor mobile experience → Mobile-first responsive design approach

## Future Enhancements

### Advanced Analytics (Phase 5)
- **Predictive Modeling**: ML-based gene prioritization visualizations
- **Network Analysis**: Gene interaction network graphs using vue-data-ui
- **Temporal Analysis**: Evidence evolution over time

### Integration Enhancements (Phase 6)  
- **External APIs**: Real-time data from additional genomic databases
- **Export Integration**: Direct export to analysis tools (R, Python)
- **Collaboration**: Shared annotation and curation workflows

### Alternative Overlap Visualizations (vue-data-ui only option)

If UpSet plots are not required, vue-data-ui offers alternative overlap visualizations:

- **VueUiChord** - Interactive chord diagrams showing source relationships
- **VueUiHeatmap** - Gene × Source matrix with color-coded presence
- **VueUiNestedDonuts** - Hierarchical breakdown of source combinations
- **VueUiTreemap** - Proportional representation of source overlaps
- **VueUiCirclePack** - Nested circles showing gene groupings by sources

This plan provides a comprehensive roadmap for implementing sophisticated data visualizations that match and exceed the capabilities of Kidney Genetics v1, using a streamlined two-library approach with vue-data-ui handling most visualizations and UpSet.js providing the specialized set intersection plots essential for genomic data analysis.