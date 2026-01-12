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
        sum(COALESCE(cache_entries.data_size, pg_column_size(cache_entries.data)))
            AS total_size_bytes,
        sum(cache_entries.access_count) AS total_accesses,
        avg(cache_entries.access_count) AS avg_accesses,
        count(*) FILTER (WHERE cache_entries.expires_at IS NULL
            OR cache_entries.expires_at > now()) AS active_entries,
        count(*) FILTER (WHERE cache_entries.expires_at IS NOT NULL
            AND cache_entries.expires_at <= now()) AS expired_entries,
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
            WHEN 'PanelApp'::text THEN
                (COALESCE(jsonb_array_length(ge.evidence_data -> 'panels'::text),
                    0))::bigint
            WHEN 'HPO'::text THEN
                ((COALESCE(jsonb_array_length(ge.evidence_data -> 'hpo_terms'::text), 0)
                + COALESCE(jsonb_array_length(ge.evidence_data -> 'diseases'::text),
                    0)))::bigint
            WHEN 'PubTator'::text THEN
                (COALESCE((ge.evidence_data ->> 'publication_count'::text)::integer,
                jsonb_array_length(ge.evidence_data -> 'pmids'::text)))::bigint
            WHEN 'DiagnosticPanels'::text THEN
                (COALESCE((ge.evidence_data ->> 'panel_count'::text)::integer,
                jsonb_array_length(ge.evidence_data -> 'panels'::text)))::bigint
            WHEN 'GenCC'::text THEN
                (COALESCE(jsonb_array_length(
                    ge.evidence_data -> 'classifications'::text), 0))::bigint
            WHEN 'ClinGen'::text THEN
                (COALESCE((ge.evidence_data ->> 'assertion_count'::text)::integer,
                    1))::bigint
            WHEN 'Literature'::text THEN
                (COALESCE((ge.evidence_data ->> 'publication_count'::text)::integer,
                jsonb_array_length(ge.evidence_data -> 'publications'::text)))::bigint
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
           SUM(source_score) /
               (SELECT COUNT(DISTINCT source_name) FROM combined_evidence_scores)
               * 100 AS percentage_score,
           -- Source breakdown
           jsonb_object_agg(source_name, ROUND(source_score::numeric, 4))
               AS source_scores,
           -- Total active sources for reference
           (SELECT COUNT(DISTINCT source_name) FROM combined_evidence_scores)
               AS total_active_sources,
           -- Evidence tier classification
           CASE
               WHEN COUNT(DISTINCT source_name) >= 4 AND SUM(source_score) /
                   (SELECT COUNT(DISTINCT source_name) FROM combined_evidence_scores)
                   * 100 >= 50
                   THEN 'comprehensive_support'
               WHEN COUNT(DISTINCT source_name) >= 3 AND SUM(source_score) /
                   (SELECT COUNT(DISTINCT source_name) FROM combined_evidence_scores)
                   * 100 >= 35
                   THEN 'multi_source_support'
               WHEN COUNT(DISTINCT source_name) >= 2 AND SUM(source_score) /
                   (SELECT COUNT(DISTINCT source_name) FROM combined_evidence_scores)
                   * 100 >= 20
                   THEN 'established_support'
               WHEN SUM(source_score) /
                   (SELECT COUNT(DISTINCT source_name) FROM combined_evidence_scores)
                   * 100 >= 10
                   THEN 'preliminary_evidence'
               WHEN SUM(source_score) /
                   (SELECT COUNT(DISTINCT source_name) FROM combined_evidence_scores)
                   * 100 > 0
                   THEN 'minimal_evidence'
               ELSE 'no_evidence'
           END AS evidence_tier,
           -- Evidence group classification
           CASE
               WHEN COUNT(DISTINCT source_name) >= 2 AND SUM(source_score) /
                   (SELECT COUNT(DISTINCT source_name) FROM combined_evidence_scores)
                   * 100 >= 20
                   THEN 'well_supported'
               WHEN SUM(source_score) /
                   (SELECT COUNT(DISTINCT source_name) FROM combined_evidence_scores)
                   * 100 > 0
                   THEN 'emerging_evidence'
               ELSE 'insufficient'
           END AS evidence_group
    FROM source_scores_per_gene
    GROUP BY gene_id, approved_symbol, hgnc_id
    """,
    dependencies=["combined_evidence_scores"],
)

# STRING PPI percentiles view for global percentile calculation
string_ppi_percentiles = ReplaceableObject(
    name="string_ppi_percentiles",
    sqltext="""
    SELECT
        ga.gene_id,
        g.approved_symbol,
        CAST(ga.annotations->'ppi_score' AS FLOAT) as ppi_score,
        PERCENT_RANK() OVER (
            ORDER BY CAST(ga.annotations->'ppi_score' AS FLOAT)
        ) AS percentile_rank
    FROM gene_annotations ga
    JOIN genes g ON g.id = ga.gene_id
    WHERE ga.annotations ? 'ppi_score'
      AND ga.annotations->>'ppi_score' IS NOT NULL
      AND ga.annotations->>'ppi_score' != 'null'
      AND CAST(ga.annotations->>'ppi_score' AS FLOAT) > 0
    """,
    dependencies=[],
)


# New views for database views migration (issue #16)

gene_list_detailed = ReplaceableObject(
    name="gene_list_detailed",
    sqltext="""
    SELECT
        -- Core gene fields from simplified schema
        g.id::bigint AS gene_id,
        g.hgnc_id::text AS hgnc_id,
        g.approved_symbol::text AS gene_symbol,
        g.aliases::text[] AS alias_symbols,
        -- Score fields from gene_scores view
        COALESCE(gs.raw_score, 0.0)::float8 AS total_score,
        COALESCE(gs.percentage_score, 0.0)::float8 AS percentage_score,
        CASE
            WHEN gs.percentage_score >= 80 THEN 'High'
            WHEN gs.percentage_score >= 50 THEN 'Medium'
            WHEN gs.percentage_score >= 20 THEN 'Low'
            ELSE 'Unknown'
        END::text AS classification,
        -- Evidence counts
        COALESCE(gs.source_count, 0)::integer AS source_count,
        COALESCE(
            (SELECT array_agg(DISTINCT source_name ORDER BY source_name)
             FROM gene_evidence
             WHERE gene_id = g.id),
            '{}'::text[]
        )::text[] AS sources,
        -- Annotation counts
        COALESCE(
            (SELECT COUNT(DISTINCT source)::integer
             FROM gene_annotations
             WHERE gene_id = g.id),
            0
        )::integer AS annotation_count,
        COALESCE(
            (SELECT array_agg(DISTINCT source ORDER BY source)
             FROM gene_annotations
             WHERE gene_id = g.id),
            '{}'::text[]
        )::text[] AS annotation_sources,
        -- Timestamps
        g.created_at::timestamptz AS created_at,
        g.updated_at::timestamptz AS updated_at
    FROM genes g
    LEFT JOIN gene_scores gs ON g.id = gs.gene_id
    """,
    dependencies=["gene_scores"],
)

admin_logs_filtered = ReplaceableObject(
    name="admin_logs_filtered",
    sqltext="""
    SELECT
        sl.id::bigint,
        sl.timestamp::timestamptz,
        sl.level::text,
        sl.logger::text,
        sl.message::text,
        sl.request_id::text,
        sl.user_id::bigint,
        u.email::text AS user_email,
        sl.ip_address::text,
        sl.user_agent::text,
        sl.path::text,
        sl.method::text,
        sl.status_code::integer,
        sl.duration_ms::float8,
        sl.error_type::text,
        -- Extract additional fields from context JSONB
        sl.context->>'action' AS action,
        sl.context->>'endpoint' AS endpoint,
        -- Add commonly used computed fields
        CASE
            WHEN sl.status_code < 400 THEN 'success'
            WHEN sl.status_code < 500 THEN 'client_error'
            ELSE 'server_error'
        END::text AS status_category,
        DATE(sl.timestamp) AS log_date,
        EXTRACT(HOUR FROM sl.timestamp)::integer AS log_hour
    FROM system_logs sl
    LEFT JOIN users u ON sl.user_id = u.id
    WHERE sl.path IS NOT NULL  -- Only API logs
    """,
    dependencies=[],
)

datasource_metadata_panelapp = ReplaceableObject(
    name="datasource_metadata_panelapp",
    sqltext="""
    SELECT
        ge.gene_id::bigint,
        g.approved_symbol::text AS gene_symbol,
        ge.evidence_data->>'source'::text AS source_region,
        jsonb_array_length(COALESCE(ge.evidence_data->'panels', '[]'::jsonb))::integer
            AS panel_count,
        ge.evidence_data->'panels' AS panels,
        COALESCE((ge.evidence_data->>'confidence_level')::float, 0.0)::float8 AS max_confidence,
        ge.evidence_data->>'moi'::text AS mode_of_inheritance,
        ge.created_at::timestamptz,
        ge.updated_at::timestamptz
    FROM gene_evidence ge
    JOIN genes g ON g.id = ge.gene_id
    WHERE ge.source_name = 'PanelApp'
    """,
    dependencies=[],
)

datasource_metadata_gencc = ReplaceableObject(
    name="datasource_metadata_gencc",
    sqltext="""
    SELECT
        ge.gene_id::bigint,
        g.approved_symbol::text AS gene_symbol,
        jsonb_array_length(
            COALESCE(ge.evidence_data->'classifications', '[]'::jsonb))::integer
            AS classification_count,
        ge.evidence_data->'classifications' AS classifications,
        ge.evidence_data->>'disease_id'::text AS disease_id,
        ge.evidence_data->>'disease_title'::text AS disease_title,
        ge.created_at::timestamptz,
        ge.updated_at::timestamptz
    FROM gene_evidence ge
    JOIN genes g ON g.id = ge.gene_id
    WHERE ge.source_name = 'GenCC'
    """,
    dependencies=[],
)

genes_current = ReplaceableObject(
    name="genes_current",
    sqltext="""
    SELECT *
    FROM genes
    WHERE valid_to = 'infinity'::timestamptz
    """,
    dependencies=[],
)

gene_hpo_classifications = ReplaceableObject(
    name="gene_hpo_classifications",
    sqltext="""
    SELECT
        g.id AS gene_id,
        g.approved_symbol AS gene_symbol,
        ga.annotations->'classification'->'clinical_group'->>'primary' AS clinical_group,
        ga.annotations->'classification'->'onset_group'->>'primary' AS onset_group,
        COALESCE(
            (ga.annotations->'classification'->'syndromic_assessment'->>'is_syndromic')::boolean,
            FALSE
        ) AS is_syndromic
    FROM genes g
    LEFT JOIN gene_annotations ga ON g.id = ga.gene_id AND ga.source = 'hpo'
    """,
    dependencies=[],
)

# Dashboard source distribution views
source_distribution_hpo = ReplaceableObject(
    name="source_distribution_hpo",
    sqltext="""
    SELECT
        jsonb_array_length(evidence_data->'hpo_terms') as hpo_term_count,
        COUNT(*) as gene_count
    FROM gene_evidence
    WHERE source_name = 'HPO'
        AND evidence_data->'hpo_terms' IS NOT NULL
    GROUP BY 1
    ORDER BY 1 DESC
    """,
    dependencies=[],
)

source_distribution_gencc = ReplaceableObject(
    name="source_distribution_gencc",
    sqltext="""
    SELECT
        jsonb_array_elements_text(evidence_data->'classifications') as classification,
        COUNT(DISTINCT gene_id) as gene_count
    FROM gene_evidence
    WHERE source_name = 'GenCC'
        AND evidence_data->'classifications' IS NOT NULL
    GROUP BY 1
    ORDER BY 2 DESC
    """,
    dependencies=[],
)

source_distribution_clingen = ReplaceableObject(
    name="source_distribution_clingen",
    sqltext="""
    SELECT
        jsonb_array_elements_text(evidence_data->'classifications') as classification,
        COUNT(DISTINCT gene_id) as gene_count
    FROM gene_evidence
    WHERE source_name = 'ClinGen'
        AND evidence_data->'classifications' IS NOT NULL
    GROUP BY 1
    ORDER BY 2 DESC
    """,
    dependencies=[],
)

source_distribution_diagnosticpanels = ReplaceableObject(
    name="source_distribution_diagnosticpanels",
    sqltext="""
    SELECT
        jsonb_array_elements_text(evidence_data->'providers') as provider,
        COUNT(DISTINCT gene_id) as gene_count
    FROM gene_evidence
    WHERE source_name = 'DiagnosticPanels'
        AND evidence_data->'providers' IS NOT NULL
    GROUP BY 1
    ORDER BY 2 DESC
    """,
    dependencies=[],
)

source_distribution_panelapp = ReplaceableObject(
    name="source_distribution_panelapp",
    sqltext="""
    SELECT
        jsonb_array_elements_text(evidence_data->'evidence_levels') as evidence_level,
        COUNT(DISTINCT gene_id) as gene_count
    FROM gene_evidence
    WHERE source_name = 'PanelApp'
        AND evidence_data->'evidence_levels' IS NOT NULL
    GROUP BY 1
    ORDER BY 1 DESC
    """,
    dependencies=[],
)

source_distribution_pubtator = ReplaceableObject(
    name="source_distribution_pubtator",
    sqltext="""
    SELECT
        CAST(evidence_data->>'publication_count' AS INTEGER) as publication_count,
        COUNT(DISTINCT gene_id) as gene_count
    FROM gene_evidence
    WHERE source_name = 'PubTator'
        AND evidence_data->>'publication_count' IS NOT NULL
    GROUP BY 1
    ORDER BY 1 DESC
    LIMIT 20
    """,
    dependencies=[],
)

# Hybrid source views for DiagnosticPanels and Literature management
v_diagnostic_panel_providers = ReplaceableObject(
    name="v_diagnostic_panel_providers",
    sqltext="""
    SELECT
        jsonb_array_elements_text(evidence_data->'providers') as provider_name,
        COUNT(DISTINCT gene_id) as gene_count,
        MAX(updated_at) as last_updated
    FROM gene_evidence
    WHERE source_name = 'DiagnosticPanels'
    GROUP BY provider_name
    ORDER BY gene_count DESC
    """,
    dependencies=[],
)

v_literature_publications = ReplaceableObject(
    name="v_literature_publications",
    sqltext="""
    SELECT
        jsonb_array_elements_text(evidence_data->'publications') as pmid,
        COUNT(DISTINCT gene_id) as gene_count,
        MAX(updated_at) as last_updated
    FROM gene_evidence
    WHERE source_name = 'Literature'
    GROUP BY pmid
    ORDER BY gene_count DESC
    """,
    dependencies=[],
)

# Initial views for base migration (no dependency on later migration columns)
# Use this in 001_modern_complete_schema.py
INITIAL_VIEWS = [
    # Tier 1 (no dependencies)
    cache_stats,
    evidence_source_counts,
    evidence_classification_weights,
    string_ppi_percentiles,
    admin_logs_filtered,
    datasource_metadata_panelapp,
    datasource_metadata_gencc,
    gene_hpo_classifications,  # HPO clinical classifications for network coloring
    # Dashboard source distribution views
    source_distribution_hpo,
    source_distribution_gencc,
    source_distribution_clingen,
    source_distribution_diagnosticpanels,
    source_distribution_panelapp,
    source_distribution_pubtator,
    # Hybrid source management views
    v_diagnostic_panel_providers,
    v_literature_publications,
    # Tier 2 (depend on Tier 1)
    evidence_count_percentiles,
    evidence_normalized_scores,
    # Tier 3 (depend on Tier 2)
    combined_evidence_scores,
    evidence_summary_view,
    # Tier 4 (final aggregation)
    gene_scores,
    # Tier 5 (composite views that depend on multiple tiers)
    gene_list_detailed,
]

# Views that depend on temporal versioning columns (valid_to)
# Added by later migrations after 68b329da9893_add_temporal_versioning_to_genes
TEMPORAL_VIEWS = [
    genes_current,  # Requires valid_to column from temporal versioning migration
]

# List of all views in dependency order (for use after all migrations are applied)
ALL_VIEWS = INITIAL_VIEWS + TEMPORAL_VIEWS
