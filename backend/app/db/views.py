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
    dependencies=[]
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
            WHEN 'Literature'::text THEN (COALESCE(jsonb_array_length(ge.evidence_data -> 'references'::text), 0))::bigint
            ELSE
                CASE
                    WHEN ge.source_name::text ~~ 'static_%'::text THEN (
                        SELECT count(DISTINCT ge2.source_detail) AS count
                        FROM gene_evidence ge2
                        WHERE ge2.gene_id = ge.gene_id
                        AND ge2.source_name::text = ge.source_name::text
                    )
                    ELSE (0)::bigint
                END
        END AS source_count
    FROM gene_evidence ge
    JOIN genes g ON ge.gene_id = g.id
    WHERE (ge.source_name::text = ANY (ARRAY['PanelApp'::text, 'HPO'::text, 'PubTator'::text, 'Literature'::text])) 
        OR ge.source_name::text ~~ 'static_%'::text
    """,
    dependencies=[]
)

evidence_classification_weights = ReplaceableObject(
    name="evidence_classification_weights",
    sqltext="""
    WITH gencc_weighted AS (
        SELECT ge.id AS evidence_id,
            g.id AS gene_id,
            g.approved_symbol,
            ge.source_name,
            CASE
                WHEN jsonb_array_length(ge.evidence_data -> 'classifications'::text) > 0 THEN 
                    (0.5 * (sum(power(
                        CASE
                            WHEN lower(elem.value::text) = '"definitive"'::text THEN 1.0
                            WHEN lower(elem.value::text) = '"strong"'::text THEN 0.8
                            WHEN lower(elem.value::text) = '"moderate"'::text THEN 0.6
                            WHEN lower(elem.value::text) = '"supportive"'::text THEN 0.5
                            WHEN lower(elem.value::text) = '"limited"'::text THEN 0.4
                            WHEN lower(elem.value::text) = '"disputed"'::text THEN 0.2
                            WHEN lower(elem.value::text) = '"refuted"'::text THEN 0.1
                            ELSE 0.3
                        END, 2::numeric)) / NULLIF(sum(
                        CASE
                            WHEN lower(elem.value::text) = '"definitive"'::text THEN 1.0
                            WHEN lower(elem.value::text) = '"strong"'::text THEN 0.8
                            WHEN lower(elem.value::text) = '"moderate"'::text THEN 0.6
                            WHEN lower(elem.value::text) = '"supportive"'::text THEN 0.5
                            WHEN lower(elem.value::text) = '"limited"'::text THEN 0.4
                            WHEN lower(elem.value::text) = '"disputed"'::text THEN 0.2
                            WHEN lower(elem.value::text) = '"refuted"'::text THEN 0.1
                            ELSE 0.3
                        END), 0::numeric)))::double precision 
                    + 0.3::double precision * LEAST(1.0::double precision, sqrt(jsonb_array_length(ge.evidence_data -> 'classifications'::text)::double precision / 5.0::double precision)) 
                    + 0.2::double precision * (sum(
                        CASE
                            WHEN lower(elem.value::text) = ANY (ARRAY['"definitive"'::text, '"strong"'::text]) THEN 1
                            ELSE 0
                        END)::double precision / NULLIF(jsonb_array_length(ge.evidence_data -> 'classifications'::text), 0)::double precision)
                ELSE 0.3::double precision
            END AS classification_weight
        FROM gene_evidence ge
        JOIN genes g ON ge.gene_id = g.id
        CROSS JOIN LATERAL jsonb_array_elements(ge.evidence_data -> 'classifications'::text) elem(value)
        WHERE ge.source_name::text = 'GenCC'::text
        GROUP BY ge.id, g.id, g.approved_symbol, ge.source_name, ge.evidence_data
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
                        WHEN 'Refuted'::text THEN 0.1
                        ELSE 0.3
                    END
                WHEN (ge.evidence_data ->> 'classification'::text) IS NOT NULL THEN
                    CASE ge.evidence_data ->> 'classification'::text
                        WHEN 'Definitive'::text THEN 1.0
                        WHEN 'Strong'::text THEN 0.8
                        WHEN 'Moderate'::text THEN 0.6
                        WHEN 'Limited'::text THEN 0.4
                        WHEN 'Disputed'::text THEN 0.2
                        WHEN 'Refuted'::text THEN 0.1
                        ELSE 0.3
                    END
                ELSE 0.3
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
    dependencies=[]
)

static_evidence_counts = ReplaceableObject(
    name="static_evidence_counts",
    sqltext="""
    SELECT
        ge.id as evidence_id,
        ge.gene_id,
        g.approved_symbol,
        ge.source_name,
        ss.id as source_id,
        CASE
            WHEN ss.scoring_metadata->>'field' IS NOT NULL
                 AND ge.evidence_data ? (ss.scoring_metadata->>'field') THEN
                jsonb_array_length(ge.evidence_data -> (ss.scoring_metadata->>'field'))
            ELSE 1
        END as source_count
    FROM gene_evidence ge
    JOIN genes g ON ge.gene_id = g.id
    JOIN static_sources ss ON ge.source_name = 'ingested_' || ss.id::text
    WHERE ss.is_active = true
    """,
    dependencies=[]
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
        percent_rank() OVER (PARTITION BY evidence_source_counts.source_name ORDER BY evidence_source_counts.source_count) AS percentile_score
    FROM evidence_source_counts
    WHERE evidence_source_counts.source_count > 0
    """,
    dependencies=["evidence_source_counts"]
)

static_evidence_scores = ReplaceableObject(
    name="static_evidence_scores",
    sqltext="""
    SELECT
        ge.id AS evidence_id,
        ge.gene_id,
        g.approved_symbol,
        ge.source_name,
        ss.display_name as source_display_name,
        CASE
            -- Count-based scoring
            WHEN ss.scoring_metadata->>'type' = 'count' THEN
                CASE
                    WHEN ss.scoring_metadata->>'field' IS NOT NULL
                         AND ge.evidence_data ? (ss.scoring_metadata->>'field') THEN
                        LEAST(
                            jsonb_array_length(ge.evidence_data -> (ss.scoring_metadata->>'field'))::float
                            / 10.0 * COALESCE((ss.scoring_metadata->>'weight')::numeric, 0.5),
                            1.0
                        )
                    ELSE COALESCE((ss.scoring_metadata->>'weight')::numeric, 0.5)
                END

            -- Classification-based scoring
            WHEN ss.scoring_metadata->>'type' = 'classification'
                 AND ss.scoring_metadata->>'field' IS NOT NULL THEN
                COALESCE(
                    (ss.scoring_metadata->'weight_map' ->>
                        (ge.evidence_data->>(ss.scoring_metadata->>'field'))
                    )::numeric,
                    0.3
                )

            -- Fixed scoring
            WHEN ss.scoring_metadata->>'type' = 'fixed' THEN
                COALESCE((ss.scoring_metadata->>'score')::numeric, 0.5)

            ELSE 0.5
        END AS normalized_score
    FROM gene_evidence ge
    JOIN genes g ON ge.gene_id = g.id
    JOIN static_sources ss ON ge.source_name = 'ingested_' || ss.id::text
    WHERE ss.is_active = true
    """,
    dependencies=[]
)

evidence_normalized_scores = ReplaceableObject(
    name="evidence_normalized_scores",
    sqltext="""
    WITH gencc_percentiles AS (
        SELECT evidence_classification_weights.evidence_id,
            evidence_classification_weights.gene_id,
            evidence_classification_weights.approved_symbol,
            evidence_classification_weights.source_name,
            evidence_classification_weights.classification_weight,
            percent_rank() OVER (ORDER BY evidence_classification_weights.classification_weight) AS percentile_score
        FROM evidence_classification_weights
        WHERE evidence_classification_weights.source_name::text = 'GenCC'::text
    )
    SELECT evidence_count_percentiles.evidence_id,
        evidence_count_percentiles.gene_id,
        evidence_count_percentiles.approved_symbol,
        evidence_count_percentiles.source_name,
        evidence_count_percentiles.percentile_score AS normalized_score
    FROM evidence_count_percentiles
    UNION ALL
    SELECT evidence_classification_weights.evidence_id,
        evidence_classification_weights.gene_id,
        evidence_classification_weights.approved_symbol,
        evidence_classification_weights.source_name,
        evidence_classification_weights.classification_weight AS normalized_score
    FROM evidence_classification_weights
    WHERE evidence_classification_weights.source_name::text = 'ClinGen'::text
    UNION ALL
    SELECT gencc_percentiles.evidence_id,
        gencc_percentiles.gene_id,
        gencc_percentiles.approved_symbol,
        gencc_percentiles.source_name,
        gencc_percentiles.percentile_score AS normalized_score
    FROM gencc_percentiles
    """,
    dependencies=["evidence_count_percentiles", "evidence_classification_weights"]
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
    WHERE evidence_normalized_scores.source_name::text !~~ 'static_%'::text
    UNION ALL
    SELECT min(static_evidence_scores.evidence_id) AS evidence_id,
        static_evidence_scores.gene_id,
        static_evidence_scores.approved_symbol,
        static_evidence_scores.source_name,
        max(static_evidence_scores.source_display_name::text) AS display_name,
        max(static_evidence_scores.normalized_score) AS normalized_score,
        'static'::text AS source_type
    FROM static_evidence_scores
    GROUP BY static_evidence_scores.gene_id, static_evidence_scores.approved_symbol, static_evidence_scores.source_name
    """,
    dependencies=["evidence_normalized_scores", "static_evidence_scores"]
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
        gc.curation_status,
        gc.classification,
        gc.updated_at AS last_curated
    FROM gene_evidence ge
    JOIN genes g ON ge.gene_id = g.id
    LEFT JOIN combined_evidence_scores ces ON ge.id = ces.evidence_id
    LEFT JOIN gene_curations gc ON g.id = gc.gene_id
    """,
    dependencies=["combined_evidence_scores"]
)

# Tier 4: Final aggregation view

gene_scores = ReplaceableObject(
    name="gene_scores",
    sqltext="""
    WITH source_counts AS (
        SELECT combined_evidence_scores.gene_id,
            count(DISTINCT combined_evidence_scores.source_name) AS source_count,
            count(*) AS evidence_count,
            sum(combined_evidence_scores.normalized_score) AS raw_score,
            jsonb_object_agg(COALESCE(combined_evidence_scores.display_name, combined_evidence_scores.source_name::text), round(combined_evidence_scores.normalized_score::numeric, 3)) AS source_scores
        FROM combined_evidence_scores
        GROUP BY combined_evidence_scores.gene_id
    ), total_sources AS (
        SELECT count(DISTINCT all_sources.name) AS total
        FROM (
            SELECT DISTINCT evidence_normalized_scores.source_name AS name
            FROM evidence_normalized_scores
            UNION
            SELECT DISTINCT static_evidence_scores.source_name AS name
            FROM static_evidence_scores
        ) all_sources
    )
    SELECT sc.gene_id,
        g.approved_symbol,
        g.hgnc_id,
        sc.source_count,
        sc.evidence_count,
        sc.raw_score,
        round((sc.raw_score / ts.total::double precision * 100::double precision)::numeric, 2) AS percentage_score,
        ts.total AS total_active_sources,
        sc.source_scores
    FROM source_counts sc
    CROSS JOIN total_sources ts
    JOIN genes g ON sc.gene_id = g.id
    """,
    dependencies=["combined_evidence_scores", "evidence_normalized_scores", "static_evidence_scores"]
)


# List of all views in dependency order
ALL_VIEWS = [
    # Tier 1 (no dependencies)
    cache_stats,
    evidence_source_counts,
    evidence_classification_weights,
    static_evidence_counts,
    static_evidence_scores,
    # Tier 2 (depend on Tier 1)
    evidence_count_percentiles,
    evidence_normalized_scores,
    # Tier 3 (depend on Tier 2)
    combined_evidence_scores,
    evidence_summary_view,
    # Tier 4 (final aggregation)
    gene_scores,
]
