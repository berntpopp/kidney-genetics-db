"""
Database view definitions as ReplaceableObjects.
All views are defined here for centralized management and migration squashing.
"""

from app.db.replaceable_objects import ReplaceableObject

# Tier 1: Base Views (no dependencies)

cache_stats = ReplaceableObject(
    name="cache_stats",
    sqltext="""
    SELECT cache_entries.namespace,
        count(*) AS total_entries,
        sum(COALESCE(cache_entries.data_size, pg_column_size(cache_entries.data))) AS total_size_bytes,
        sum(cache_entries.access_count) AS total_accesses,
        avg(cache_entries.access_count) AS avg_accesses,
        count(*) FILTER (WHERE cache_entries.expires_at IS NULL OR cache_entries.expires_at > now()) AS active_entries,
        count(*) FILTER (WHERE cache_entries.expires_at IS NOT NULL AND cache_entries.expires_at <= now()) AS expired_entries,
        max(cache_entries.last_accessed) AS last_access_time,
        min(cache_entries.created_at) AS oldest_entry,
        max(cache_entries.created_at) AS newest_entry
    FROM cache_entries
    GROUP BY cache_entries.namespace
    """,
    dependencies=[],
)

evidence_source_counts = ReplaceableObject(
    name="evidence_source_counts",
    sqltext="""
    SELECT ge.id AS evidence_id,
        ge.gene_id,
        g.approved_symbol,
        ge.source_name,
        CASE ge.source_name
            WHEN 'PanelApp'::text THEN (COALESCE(jsonb_array_length(ge.evidence_data -> 'panels'::text), 0))::bigint
            WHEN 'HPO'::text THEN ((COALESCE(jsonb_array_length(ge.evidence_data -> 'hpo_terms'::text), 0) + COALESCE(jsonb_array_length(ge.evidence_data -> 'diseases'::text), 0)))::bigint
            WHEN 'PubTator'::text THEN (COALESCE((ge.evidence_data ->> 'publication_count'::text)::integer, jsonb_array_length(ge.evidence_data -> 'pmids'::text)))::bigint
            WHEN 'DiagnosticPanels'::text THEN (COALESCE((ge.evidence_data ->> 'panel_count'::text)::integer,
                                                jsonb_array_length(ge.evidence_data -> 'panels'::text)))::bigint
            WHEN 'GenCC'::text THEN (COALESCE(jsonb_array_length(ge.evidence_data -> 'classifications'::text), 0))::bigint
            WHEN 'ClinGen'::text THEN (COALESCE((ge.evidence_data ->> 'assertion_count'::text)::integer, 1))::bigint
            WHEN 'Literature'::text THEN (COALESCE((ge.evidence_data ->> 'publication_count'::text)::integer, jsonb_array_length(ge.evidence_data -> 'publications'::text)))::bigint
            ELSE (0)::bigint
        END AS source_count
    FROM gene_evidence ge
    JOIN genes g ON ge.gene_id = g.id
    """,
    dependencies=[],
)

evidence_classification_weights = ReplaceableObject(
    name="evidence_classification_weights",
    sqltext="""
    WITH gencc_weighted AS (
        SELECT ge.id AS evidence_id,
            g.id AS gene_id,
            g.approved_symbol,
            ge.source_name,
            -- Simple MAX approach - take the best classification
            COALESCE(
                (SELECT MAX(
                    CASE lower(replace(elem.value::text, '"', ''))
                        WHEN 'definitive' THEN 1.0
                        WHEN 'strong' THEN 0.8
                        WHEN 'moderate' THEN 0.6
                        WHEN 'supportive' THEN 0.5
                        WHEN 'limited' THEN 0.4
                        WHEN 'disputed evidence' THEN 0.2
                        WHEN 'no known disease relationship' THEN 0.0
                        ELSE 0.0  -- Unknown = no evidence
                    END
                ) FROM jsonb_array_elements(ge.evidence_data -> 'classifications') elem),
                0.0
            ) AS classification_weight
        FROM gene_evidence ge
        JOIN genes g ON ge.gene_id = g.id
        WHERE ge.source_name::text = 'GenCC'::text
    ), clingen_weights AS (
        SELECT ge.id AS evidence_id,
            g.id AS gene_id,
            g.approved_symbol,
            ge.source_name,
            CASE
                WHEN jsonb_typeof(ge.evidence_data -> 'classifications'::text) = 'array'::text THEN
                    CASE (ge.evidence_data -> 'classifications'::text) ->> 0
                        WHEN 'Definitive'::text THEN 1.0
                        WHEN 'Strong'::text THEN 0.8
                        WHEN 'Moderate'::text THEN 0.6
                        WHEN 'Limited'::text THEN 0.4
                        WHEN 'Disputed'::text THEN 0.2
                        WHEN 'No Known Disease Relationship'::text THEN 0.0
                        WHEN 'No Known Disease Relationship*'::text THEN 0.0
                        ELSE 0.0  -- Unknown = no evidence
                    END
                WHEN (ge.evidence_data ->> 'classification'::text) IS NOT NULL THEN
                    CASE ge.evidence_data ->> 'classification'::text
                        WHEN 'Definitive'::text THEN 1.0
                        WHEN 'Strong'::text THEN 0.8
                        WHEN 'Moderate'::text THEN 0.6
                        WHEN 'Limited'::text THEN 0.4
                        WHEN 'Disputed'::text THEN 0.2
                        WHEN 'No Known Disease Relationship'::text THEN 0.0
                        WHEN 'No Known Disease Relationship*'::text THEN 0.0
                        ELSE 0.0  -- Unknown = no evidence
                    END
                ELSE 0.0  -- Unknown = no evidence
            END AS classification_weight
        FROM gene_evidence ge
        JOIN genes g ON ge.gene_id = g.id
        WHERE ge.source_name::text = 'ClinGen'::text
    )
    SELECT clingen_weights.evidence_id,
        clingen_weights.gene_id,
        clingen_weights.approved_symbol,
        clingen_weights.source_name,
        clingen_weights.classification_weight
    FROM clingen_weights
    UNION ALL
    SELECT gencc_weighted.evidence_id,
        gencc_weighted.gene_id,
        gencc_weighted.approved_symbol,
        gencc_weighted.source_name,
        gencc_weighted.classification_weight
    FROM gencc_weighted
    """,
    dependencies=[],
)

# static_evidence_counts removed - no longer needed after refactor

# Tier 2: Views dependent on Tier 1

evidence_count_percentiles = ReplaceableObject(
    name="evidence_count_percentiles",
    sqltext="""
    SELECT evidence_source_counts.evidence_id,
        evidence_source_counts.gene_id,
        evidence_source_counts.approved_symbol,
        evidence_source_counts.source_name,
        evidence_source_counts.source_count,
        percent_rank() OVER (
            PARTITION BY evidence_source_counts.source_name
            ORDER BY LN(1.0 + evidence_source_counts.source_count)
        ) AS percentile_score
    FROM evidence_source_counts
    WHERE evidence_source_counts.source_count > 0
    """,
    dependencies=["evidence_source_counts"],
)

# static_evidence_scores removed - no longer needed after refactor

evidence_normalized_scores = ReplaceableObject(
    name="evidence_normalized_scores",
    sqltext="""
    SELECT evidence_count_percentiles.evidence_id,
        evidence_count_percentiles.gene_id,
        evidence_count_percentiles.approved_symbol,
        evidence_count_percentiles.source_name,
        evidence_count_percentiles.percentile_score AS normalized_score
    FROM evidence_count_percentiles
    WHERE evidence_count_percentiles.source_name NOT IN ('ClinGen', 'GenCC')
    UNION ALL
    SELECT evidence_classification_weights.evidence_id,
        evidence_classification_weights.gene_id,
        evidence_classification_weights.approved_symbol,
        evidence_classification_weights.source_name,
        evidence_classification_weights.classification_weight AS normalized_score
    FROM evidence_classification_weights
    WHERE evidence_classification_weights.source_name::text = 'ClinGen'::text
    UNION ALL
    SELECT evidence_classification_weights.evidence_id,
        evidence_classification_weights.gene_id,
        evidence_classification_weights.approved_symbol,
        evidence_classification_weights.source_name,
        evidence_classification_weights.classification_weight AS normalized_score
    FROM evidence_classification_weights
    WHERE evidence_classification_weights.source_name::text = 'GenCC'::text
    """,
    dependencies=["evidence_count_percentiles", "evidence_classification_weights"],
)

# Tier 3: Views dependent on Tier 2

combined_evidence_scores = ReplaceableObject(
    name="combined_evidence_scores",
    sqltext="""
    SELECT evidence_normalized_scores.evidence_id,
        evidence_normalized_scores.gene_id,
        evidence_normalized_scores.approved_symbol,
        evidence_normalized_scores.source_name,
        evidence_normalized_scores.source_name AS display_name,
        evidence_normalized_scores.normalized_score,
        'pipeline'::text AS source_type
    FROM evidence_normalized_scores
    """,
    dependencies=["evidence_normalized_scores"],
)

evidence_summary_view = ReplaceableObject(
    name="evidence_summary_view",
    sqltext="""
    SELECT ge.id,
        ge.gene_id,
        g.approved_symbol,
        g.hgnc_id,
        ge.source_name,
        ge.evidence_data,
        COALESCE(ces.normalized_score, 0::double precision) AS normalized_score,
        gc.classification,
        gc.updated_at AS last_curated
    FROM gene_evidence ge
    JOIN genes g ON ge.gene_id = g.id
    LEFT JOIN combined_evidence_scores ces ON ge.id = ces.evidence_id
    LEFT JOIN gene_curations gc ON g.id = gc.gene_id
    """,
    dependencies=["combined_evidence_scores"],
)

# Tier 4: Final aggregation view

gene_scores = ReplaceableObject(
    name="gene_scores",
    sqltext="""
    WITH source_scores_per_gene AS (
        SELECT g.id AS gene_id,
               g.approved_symbol,
               g.hgnc_id,
               ces.source_name,
               MAX(ces.normalized_score) AS source_score
        FROM genes g
        INNER JOIN combined_evidence_scores ces ON g.id = ces.gene_id
        GROUP BY g.id, g.approved_symbol, g.hgnc_id, ces.source_name
    )
    SELECT gene_id,
           approved_symbol,
           hgnc_id,
           COUNT(DISTINCT source_name) AS source_count,
           COUNT(DISTINCT source_name) AS evidence_count,  -- Alias for backward compatibility
           SUM(source_score) AS raw_score,
           -- Sum of scores divided by total possible sources, as percentage
           SUM(source_score) / (SELECT COUNT(DISTINCT source_name) FROM combined_evidence_scores) * 100 AS percentage_score,
           -- Source breakdown
           jsonb_object_agg(source_name, ROUND(source_score::numeric, 4)) AS source_scores,
           -- Total active sources for reference
           (SELECT COUNT(DISTINCT source_name) FROM combined_evidence_scores) AS total_active_sources
    FROM source_scores_per_gene
    GROUP BY gene_id, approved_symbol, hgnc_id
    """,
    dependencies=["combined_evidence_scores"],
)


# List of all views in dependency order
ALL_VIEWS = [
    # Tier 1 (no dependencies)
    cache_stats,
    evidence_source_counts,
    evidence_classification_weights,
    # Tier 2 (depend on Tier 1)
    evidence_count_percentiles,
    evidence_normalized_scores,
    # Tier 3 (depend on Tier 2)
    combined_evidence_scores,
    evidence_summary_view,
    # Tier 4 (final aggregation)
    gene_scores,
]
