-- Fix HPO scoring in evidence_source_counts view
-- The view was looking for 'phenotypes' and 'disease_associations' 
-- but HPO stores 'hpo_terms' and 'diseases'

DROP VIEW IF EXISTS gene_scores CASCADE;
DROP VIEW IF EXISTS evidence_normalized_scores CASCADE;
DROP VIEW IF EXISTS evidence_count_percentiles CASCADE;
DROP VIEW IF EXISTS evidence_classification_weights CASCADE;
DROP VIEW IF EXISTS evidence_source_counts CASCADE;

-- Recreate evidence_source_counts with correct HPO field names
CREATE VIEW evidence_source_counts AS
SELECT 
    ge.id AS evidence_id,
    ge.gene_id,
    g.approved_symbol,
    ge.source_name,
    CASE ge.source_name
        WHEN 'PanelApp' THEN COALESCE(jsonb_array_length(ge.evidence_data -> 'panels'), 0)
        WHEN 'HPO' THEN COALESCE(jsonb_array_length(ge.evidence_data -> 'hpo_terms'), 0) 
            + COALESCE(jsonb_array_length(ge.evidence_data -> 'diseases'), 0)
        WHEN 'PubTator' THEN COALESCE((ge.evidence_data ->> 'publication_count')::integer, 
            jsonb_array_length(ge.evidence_data -> 'pmids'))
        WHEN 'Literature' THEN COALESCE(jsonb_array_length(ge.evidence_data -> 'references'), 0)
        ELSE 0
    END AS source_count
FROM gene_evidence ge
JOIN genes g ON ge.gene_id = g.id
WHERE ge.source_name IN ('PanelApp', 'HPO', 'PubTator', 'Literature');

-- Recreate evidence_count_percentiles
CREATE VIEW evidence_count_percentiles AS
SELECT 
    evidence_id,
    gene_id,
    approved_symbol,
    source_name,
    source_count,
    percent_rank() OVER (PARTITION BY source_name ORDER BY source_count) AS percentile_score
FROM evidence_source_counts
WHERE source_count > 0;

-- Recreate evidence_classification_weights
CREATE VIEW evidence_classification_weights AS
SELECT 
    ge.id AS evidence_id,
    ge.gene_id,
    g.approved_symbol,
    ge.source_name,
    CASE 
        WHEN ge.source_name = 'ClinGen' THEN 
            CASE ge.evidence_data ->> 'classification'
                WHEN 'Definitive' THEN 1.0
                WHEN 'Strong' THEN 0.9
                WHEN 'Moderate' THEN 0.7
                WHEN 'Limited' THEN 0.5
                WHEN 'Disputed' THEN 0.2
                WHEN 'Refuted' THEN 0.1
                ELSE 0.3
            END
        WHEN ge.source_name = 'GenCC' THEN
            CASE ge.evidence_data ->> 'classification'
                WHEN 'definitive' THEN 1.0
                WHEN 'strong' THEN 0.8
                WHEN 'moderate' THEN 0.6
                WHEN 'limited' THEN 0.4
                WHEN 'disputed' THEN 0.2
                WHEN 'refuted' THEN 0.1
                ELSE 0.3
            END
        ELSE 0.5
    END AS classification_weight
FROM gene_evidence ge
JOIN genes g ON ge.gene_id = g.id
WHERE ge.source_name IN ('ClinGen', 'GenCC');

-- Recreate evidence_normalized_scores
CREATE VIEW evidence_normalized_scores AS
SELECT 
    evidence_id,
    gene_id,
    approved_symbol,
    source_name,
    percentile_score AS normalized_score
FROM evidence_count_percentiles
UNION ALL
SELECT 
    evidence_id,
    gene_id,
    approved_symbol,
    source_name,
    classification_weight AS normalized_score
FROM evidence_classification_weights;

-- Recreate gene_scores
CREATE VIEW gene_scores AS
WITH active_sources AS (
    SELECT COUNT(DISTINCT source_name) AS total_count
    FROM gene_evidence
),
gene_source_scores AS (
    SELECT 
        g.id AS gene_id,
        g.approved_symbol,
        g.hgnc_id,
        COUNT(DISTINCT ens.source_name) AS source_count,
        COUNT(ens.*) AS evidence_count,
        COALESCE(SUM(ens.normalized_score), 0) AS raw_score,
        jsonb_object_agg(
            ens.source_name, 
            ROUND(ens.normalized_score::numeric, 3)
        ) FILTER (WHERE ens.source_name IS NOT NULL) AS source_scores
    FROM genes g
    LEFT JOIN evidence_normalized_scores ens ON g.id = ens.gene_id
    GROUP BY g.id, g.approved_symbol, g.hgnc_id
)
SELECT 
    gss.gene_id,
    gss.approved_symbol,
    gss.hgnc_id,
    gss.source_count,
    gss.evidence_count,
    gss.raw_score,
    CASE 
        WHEN ac.total_count > 0 THEN 
            ROUND((gss.raw_score / ac.total_count * 100)::numeric, 2)
        ELSE 0
    END AS percentage_score,
    ac.total_count AS total_active_sources,
    COALESCE(gss.source_scores, '{}'::jsonb) AS source_scores
FROM gene_source_scores gss
CROSS JOIN active_sources ac
ORDER BY percentage_score DESC NULLS LAST, gss.approved_symbol;