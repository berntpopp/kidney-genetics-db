--
-- PostgreSQL database dump
--

\restrict jlU0eQMbtgvDcA0BmY1pn3b9FsFdbLQzWKKuYPzi87lWOIt8htpxFWZoHzpzksO

-- Dumped from database version 14.19
-- Dumped by pg_dump version 14.19

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: source_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.source_status AS ENUM (
    'idle',
    'running',
    'completed',
    'failed',
    'paused'
);


--
-- Name: extract_pubtator_metrics(jsonb); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.extract_pubtator_metrics(evidence_data jsonb) RETURNS jsonb
    LANGUAGE plpgsql IMMUTABLE
    AS $$
        BEGIN
            RETURN jsonb_build_object(
                'publication_count', COALESCE((evidence_data->>'publication_count')::int, 0),
                'total_mentions', COALESCE((evidence_data->>'total_mentions')::int, 0),
                'evidence_score', COALESCE((evidence_data->>'evidence_score')::float, 0),
                'top_pmids', COALESCE(evidence_data->'pmids', '[]'::jsonb)
            );
        END;
        $$;


--
-- Name: merge_evidence_jsonb(jsonb, jsonb); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.merge_evidence_jsonb(existing jsonb, new_data jsonb) RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
        DECLARE
            result jsonb;
            key text;
            existing_value jsonb;
            new_value jsonb;
        BEGIN
            -- Start with existing data as base
            result := existing;

            -- Iterate through new_data keys and merge intelligently
            FOR key IN SELECT jsonb_object_keys(new_data)
            LOOP
                existing_value := existing->key;
                new_value := new_data->key;

                -- Merge logic based on value types
                IF existing_value IS NULL THEN
                    -- New key, add it
                    result := jsonb_set(result, ARRAY[key], new_value);

                ELSIF jsonb_typeof(existing_value) = 'array' AND jsonb_typeof(new_value) = 'array' THEN
                    -- Merge arrays by combining unique elements
                    result := jsonb_set(result, ARRAY[key],
                        (SELECT jsonb_agg(DISTINCT value)
                         FROM (
                             SELECT jsonb_array_elements(existing_value) AS value
                             UNION
                             SELECT jsonb_array_elements(new_value) AS value
                         ) AS combined)
                    );

                ELSIF jsonb_typeof(existing_value) = 'object' AND jsonb_typeof(new_value) = 'object' THEN
                    -- Recursively merge objects
                    result := jsonb_set(result, ARRAY[key], existing_value || new_value);

                ELSIF key = 'evidence_score' OR key = 'confidence_score' THEN
                    -- For scores, keep the higher value
                    IF (new_value::text)::numeric > (existing_value::text)::numeric THEN
                        result := jsonb_set(result, ARRAY[key], new_value);
                    END IF;

                ELSIF key = 'date' OR key = 'updated_at' OR key = 'last_updated' THEN
                    -- For dates, keep the more recent
                    IF new_value::text > existing_value::text THEN
                        result := jsonb_set(result, ARRAY[key], new_value);
                    END IF;

                ELSIF new_value IS NOT NULL AND (existing_value IS NULL OR existing_value = 'null'::jsonb) THEN
                    -- Replace null with non-null value
                    result := jsonb_set(result, ARRAY[key], new_value);

                END IF;
            END LOOP;

            -- Add merge history
            result := jsonb_set(result,
                ARRAY['merge_history'],
                COALESCE(result->'merge_history', '[]'::jsonb) ||
                    jsonb_build_array(jsonb_build_object(
                        'merged_at', NOW(),
                        'source_data_keys', array_to_json(ARRAY(SELECT jsonb_object_keys(new_data)))
                    ))
            );

            RETURN result;
        END;
        $$;


--
-- Name: update_gene_curation_on_evidence_change(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.update_gene_curation_on_evidence_change() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        DECLARE
            target_gene_id INTEGER;
        BEGIN
            -- Determine which gene_id to update based on operation type
            IF TG_OP = 'DELETE' THEN
                target_gene_id := OLD.gene_id;
            ELSE
                target_gene_id := NEW.gene_id;
            END IF;

            -- Update or insert gene_curation record
            INSERT INTO gene_curations (
                gene_id,
                classification,
                evidence_score,
                evidence_count,
                source_count,
                updated_at
            )
            SELECT
                g.id,
                -- Calculate classification based on evidence score
                CASE
                    WHEN COALESCE(AVG(ge.evidence_score), 0) >= 0.8 THEN 'definitive'
                    WHEN COALESCE(AVG(ge.evidence_score), 0) >= 0.6 THEN 'strong'
                    WHEN COALESCE(AVG(ge.evidence_score), 0) >= 0.4 THEN 'moderate'
                    WHEN COALESCE(AVG(ge.evidence_score), 0) >= 0.2 THEN 'limited'
                    ELSE 'no_evidence'
                END AS classification,
                COALESCE(AVG(ge.evidence_score), 0) AS evidence_score,
                COUNT(ge.id)::INTEGER AS evidence_count,
                COUNT(DISTINCT ge.source_name)::INTEGER AS source_count,
                NOW() AS updated_at
            FROM genes g
            LEFT JOIN gene_evidence ge ON g.id = ge.gene_id
            WHERE g.id = target_gene_id
            GROUP BY g.id
            ON CONFLICT (gene_id)
            DO UPDATE SET
                classification = EXCLUDED.classification,
                evidence_score = EXCLUDED.evidence_score,
                evidence_count = EXCLUDED.evidence_count,
                source_count = EXCLUDED.source_count,
                updated_at = EXCLUDED.updated_at;

            RETURN NEW;
        END;
        $$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


--
-- Name: cache_entries; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.cache_entries (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    cache_key text NOT NULL,
    namespace text NOT NULL,
    data jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    expires_at timestamp with time zone,
    last_accessed timestamp with time zone DEFAULT now() NOT NULL,
    access_count integer DEFAULT 1 NOT NULL,
    data_size integer,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL
);


--
-- Name: cache_stats; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.cache_stats AS
 SELECT cache_entries.namespace,
    count(*) AS total_entries,
    sum(COALESCE(cache_entries.data_size, pg_column_size(cache_entries.data))) AS total_size_bytes,
    sum(cache_entries.access_count) AS total_accesses,
    avg(cache_entries.access_count) AS avg_accesses,
    count(*) FILTER (WHERE ((cache_entries.expires_at IS NULL) OR (cache_entries.expires_at > now()))) AS active_entries,
    count(*) FILTER (WHERE ((cache_entries.expires_at IS NOT NULL) AND (cache_entries.expires_at <= now()))) AS expired_entries,
    max(cache_entries.last_accessed) AS last_access_time,
    min(cache_entries.created_at) AS oldest_entry,
    max(cache_entries.created_at) AS newest_entry
   FROM public.cache_entries
  GROUP BY cache_entries.namespace;


--
-- Name: gene_evidence; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.gene_evidence (
    id integer NOT NULL,
    gene_id integer NOT NULL,
    source_name character varying(100) NOT NULL,
    source_detail character varying(255),
    evidence_data jsonb NOT NULL,
    evidence_date date,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    evidence_score double precision
);


--
-- Name: COLUMN gene_evidence.evidence_score; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.gene_evidence.evidence_score IS 'Relevance/confidence score from data source (e.g., PubTator relevance score)';


--
-- Name: genes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.genes (
    id integer NOT NULL,
    hgnc_id character varying(50),
    approved_symbol character varying(100) NOT NULL,
    aliases text[],
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: evidence_classification_weights; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.evidence_classification_weights AS
 WITH gencc_weighted AS (
         SELECT ge.id AS evidence_id,
            g.id AS gene_id,
            g.approved_symbol,
            ge.source_name,
                CASE
                    WHEN (jsonb_array_length((ge.evidence_data -> 'classifications'::text)) > 0) THEN ((((0.5 * (sum(power(
                    CASE
                        WHEN (lower((elem.value)::text) = '"definitive"'::text) THEN 1.0
                        WHEN (lower((elem.value)::text) = '"strong"'::text) THEN 0.8
                        WHEN (lower((elem.value)::text) = '"moderate"'::text) THEN 0.6
                        WHEN (lower((elem.value)::text) = '"supportive"'::text) THEN 0.5
                        WHEN (lower((elem.value)::text) = '"limited"'::text) THEN 0.4
                        WHEN (lower((elem.value)::text) = '"disputed"'::text) THEN 0.2
                        WHEN (lower((elem.value)::text) = '"refuted"'::text) THEN 0.1
                        ELSE 0.3
                    END, (2)::numeric)) / NULLIF(sum(
                    CASE
                        WHEN (lower((elem.value)::text) = '"definitive"'::text) THEN 1.0
                        WHEN (lower((elem.value)::text) = '"strong"'::text) THEN 0.8
                        WHEN (lower((elem.value)::text) = '"moderate"'::text) THEN 0.6
                        WHEN (lower((elem.value)::text) = '"supportive"'::text) THEN 0.5
                        WHEN (lower((elem.value)::text) = '"limited"'::text) THEN 0.4
                        WHEN (lower((elem.value)::text) = '"disputed"'::text) THEN 0.2
                        WHEN (lower((elem.value)::text) = '"refuted"'::text) THEN 0.1
                        ELSE 0.3
                    END), (0)::numeric))))::double precision + ((0.3)::double precision * LEAST((1.0)::double precision, sqrt(((jsonb_array_length((ge.evidence_data -> 'classifications'::text)))::double precision / (5.0)::double precision))))) + ((0.2)::double precision * ((sum(
                    CASE
                        WHEN (lower((elem.value)::text) = ANY (ARRAY['"definitive"'::text, '"strong"'::text])) THEN 1
                        ELSE 0
                    END))::double precision / (NULLIF(jsonb_array_length((ge.evidence_data -> 'classifications'::text)), 0))::double precision)))
                    ELSE (0.3)::double precision
                END AS classification_weight
           FROM ((public.gene_evidence ge
             JOIN public.genes g ON ((ge.gene_id = g.id)))
             CROSS JOIN LATERAL jsonb_array_elements((ge.evidence_data -> 'classifications'::text)) elem(value))
          WHERE ((ge.source_name)::text = 'GenCC'::text)
          GROUP BY ge.id, g.id, g.approved_symbol, ge.source_name, ge.evidence_data
        ), clingen_weights AS (
         SELECT ge.id AS evidence_id,
            g.id AS gene_id,
            g.approved_symbol,
            ge.source_name,
                CASE
                    WHEN (jsonb_typeof((ge.evidence_data -> 'classifications'::text)) = 'array'::text) THEN
                    CASE ((ge.evidence_data -> 'classifications'::text) ->> 0)
                        WHEN 'Definitive'::text THEN 1.0
                        WHEN 'Strong'::text THEN 0.8
                        WHEN 'Moderate'::text THEN 0.6
                        WHEN 'Limited'::text THEN 0.4
                        WHEN 'Disputed'::text THEN 0.2
                        WHEN 'Refuted'::text THEN 0.1
                        ELSE 0.3
                    END
                    WHEN ((ge.evidence_data ->> 'classification'::text) IS NOT NULL) THEN
                    CASE (ge.evidence_data ->> 'classification'::text)
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
           FROM (public.gene_evidence ge
             JOIN public.genes g ON ((ge.gene_id = g.id)))
          WHERE ((ge.source_name)::text = 'ClinGen'::text)
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
   FROM gencc_weighted;


--
-- Name: evidence_source_counts; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.evidence_source_counts AS
 SELECT ge.id AS evidence_id,
    ge.gene_id,
    g.approved_symbol,
    ge.source_name,
        CASE ge.source_name
            WHEN 'PanelApp'::text THEN (COALESCE(jsonb_array_length((ge.evidence_data -> 'panels'::text)), 0))::bigint
            WHEN 'HPO'::text THEN ((COALESCE(jsonb_array_length((ge.evidence_data -> 'hpo_terms'::text)), 0) + COALESCE(jsonb_array_length((ge.evidence_data -> 'diseases'::text)), 0)))::bigint
            WHEN 'PubTator'::text THEN (COALESCE(((ge.evidence_data ->> 'publication_count'::text))::integer, jsonb_array_length((ge.evidence_data -> 'pmids'::text))))::bigint
            WHEN 'Literature'::text THEN (COALESCE(jsonb_array_length((ge.evidence_data -> 'references'::text)), 0))::bigint
            ELSE
            CASE
                WHEN ((ge.source_name)::text ~~ 'static_%'::text) THEN ( SELECT count(DISTINCT ge2.source_detail) AS count
                   FROM public.gene_evidence ge2
                  WHERE ((ge2.gene_id = ge.gene_id) AND ((ge2.source_name)::text = (ge.source_name)::text)))
                ELSE (0)::bigint
            END
        END AS source_count
   FROM (public.gene_evidence ge
     JOIN public.genes g ON ((ge.gene_id = g.id)))
  WHERE (((ge.source_name)::text = ANY (ARRAY['PanelApp'::text, 'HPO'::text, 'PubTator'::text, 'Literature'::text])) OR ((ge.source_name)::text ~~ 'static_%'::text));


--
-- Name: evidence_count_percentiles; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.evidence_count_percentiles AS
 SELECT evidence_source_counts.evidence_id,
    evidence_source_counts.gene_id,
    evidence_source_counts.approved_symbol,
    evidence_source_counts.source_name,
    evidence_source_counts.source_count,
    percent_rank() OVER (PARTITION BY evidence_source_counts.source_name ORDER BY evidence_source_counts.source_count) AS percentile_score
   FROM public.evidence_source_counts
  WHERE (evidence_source_counts.source_count > 0);


--
-- Name: evidence_normalized_scores; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.evidence_normalized_scores AS
 WITH gencc_percentiles AS (
         SELECT evidence_classification_weights.evidence_id,
            evidence_classification_weights.gene_id,
            evidence_classification_weights.approved_symbol,
            evidence_classification_weights.source_name,
            evidence_classification_weights.classification_weight,
            percent_rank() OVER (ORDER BY evidence_classification_weights.classification_weight) AS percentile_score
           FROM public.evidence_classification_weights
          WHERE ((evidence_classification_weights.source_name)::text = 'GenCC'::text)
        )
 SELECT evidence_count_percentiles.evidence_id,
    evidence_count_percentiles.gene_id,
    evidence_count_percentiles.approved_symbol,
    evidence_count_percentiles.source_name,
    evidence_count_percentiles.percentile_score AS normalized_score
   FROM public.evidence_count_percentiles
UNION ALL
 SELECT evidence_classification_weights.evidence_id,
    evidence_classification_weights.gene_id,
    evidence_classification_weights.approved_symbol,
    evidence_classification_weights.source_name,
    evidence_classification_weights.classification_weight AS normalized_score
   FROM public.evidence_classification_weights
  WHERE ((evidence_classification_weights.source_name)::text = 'ClinGen'::text)
UNION ALL
 SELECT gencc_percentiles.evidence_id,
    gencc_percentiles.gene_id,
    gencc_percentiles.approved_symbol,
    gencc_percentiles.source_name,
    gencc_percentiles.percentile_score AS normalized_score
   FROM gencc_percentiles;


--
-- Name: static_sources; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.static_sources (
    id integer NOT NULL,
    source_type character varying(50) NOT NULL,
    source_name character varying(255) NOT NULL,
    display_name character varying(255) NOT NULL,
    description text,
    source_metadata jsonb DEFAULT '{}'::jsonb,
    scoring_metadata jsonb DEFAULT '{"type": "count", "weight": 0.5}'::jsonb NOT NULL,
    is_active boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    created_by character varying(255),
    CONSTRAINT static_sources_type_check CHECK (((source_type)::text = ANY ((ARRAY['diagnostic_panel'::character varying, 'manual_curation'::character varying, 'literature_review'::character varying, 'custom'::character varying])::text[])))
);


--
-- Name: static_evidence_counts; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.static_evidence_counts AS
 SELECT ge.id AS evidence_id,
    ge.gene_id,
    g.approved_symbol,
    ge.source_name,
    ss.display_name AS source_display_name,
    ss.id AS source_id,
    ss.scoring_metadata,
        CASE
            WHEN (((ss.scoring_metadata ->> 'type'::text) = 'count'::text) AND ((ss.scoring_metadata ->> 'field'::text) = 'panels'::text)) THEN ( SELECT count(DISTINCT ge2.source_detail) AS count
               FROM public.gene_evidence ge2
              WHERE ((ge2.gene_id = ge.gene_id) AND ((ge2.source_name)::text = (ge.source_name)::text)))
            WHEN (((ss.scoring_metadata ->> 'type'::text) = 'count'::text) AND ((ss.scoring_metadata ->> 'field'::text) IS NOT NULL) AND (ge.evidence_data ? (ss.scoring_metadata ->> 'field'::text))) THEN (jsonb_array_length((ge.evidence_data -> (ss.scoring_metadata ->> 'field'::text))))::bigint
            WHEN ((ss.scoring_metadata ->> 'type'::text) = 'classification'::text) THEN (
            CASE (ge.evidence_data ->> (ss.scoring_metadata ->> 'field'::text))
                WHEN 'high'::text THEN 3
                WHEN 'medium'::text THEN 2
                WHEN 'low'::text THEN 1
                ELSE 0
            END)::bigint
            ELSE (1)::bigint
        END AS source_count
   FROM ((public.gene_evidence ge
     JOIN public.genes g ON ((ge.gene_id = g.id)))
     JOIN public.static_sources ss ON (((ge.source_name)::text = ('static_'::text || (ss.id)::text))))
  WHERE (ss.is_active = true);


--
-- Name: static_evidence_scores; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.static_evidence_scores AS
 WITH percentiles AS (
         SELECT static_evidence_counts.evidence_id,
            static_evidence_counts.gene_id,
            static_evidence_counts.approved_symbol,
            static_evidence_counts.source_name,
            static_evidence_counts.source_display_name,
            static_evidence_counts.source_id,
            static_evidence_counts.scoring_metadata,
            static_evidence_counts.source_count,
            percent_rank() OVER (PARTITION BY static_evidence_counts.source_id ORDER BY static_evidence_counts.source_count) AS percentile_rank
           FROM public.static_evidence_counts
          WHERE (static_evidence_counts.source_count > 0)
        )
 SELECT percentiles.evidence_id,
    percentiles.gene_id,
    percentiles.approved_symbol,
    percentiles.source_name,
    percentiles.source_display_name,
        CASE
            WHEN ((percentiles.scoring_metadata ->> 'type'::text) = 'fixed'::text) THEN COALESCE(((percentiles.scoring_metadata ->> 'score'::text))::double precision, (0.5)::double precision)
            WHEN ((percentiles.scoring_metadata ->> 'type'::text) = 'classification'::text) THEN COALESCE((((percentiles.scoring_metadata -> 'weight_map'::text) ->> ( SELECT (gene_evidence.evidence_data ->> (percentiles.scoring_metadata ->> 'field'::text))
               FROM public.gene_evidence
              WHERE (gene_evidence.id = percentiles.evidence_id))))::double precision, (0.3)::double precision)
            ELSE
            CASE
                WHEN ((percentiles.scoring_metadata ->> 'field'::text) = 'panels'::text) THEN (LEAST(((percentiles.source_count)::double precision / (9.0)::double precision), (1.0)::double precision) * COALESCE(((percentiles.scoring_metadata ->> 'weight'::text))::double precision, (1.0)::double precision))
                ELSE (percentiles.percentile_rank * COALESCE(((percentiles.scoring_metadata ->> 'weight'::text))::double precision, (1.0)::double precision))
            END
        END AS normalized_score
   FROM percentiles;


--
-- Name: combined_evidence_scores; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.combined_evidence_scores AS
 SELECT evidence_normalized_scores.evidence_id,
    evidence_normalized_scores.gene_id,
    evidence_normalized_scores.approved_symbol,
    evidence_normalized_scores.source_name,
    evidence_normalized_scores.source_name AS display_name,
    evidence_normalized_scores.normalized_score,
    'pipeline'::text AS source_type
   FROM public.evidence_normalized_scores
  WHERE ((evidence_normalized_scores.source_name)::text !~~ 'static_%'::text)
UNION ALL
 SELECT min(static_evidence_scores.evidence_id) AS evidence_id,
    static_evidence_scores.gene_id,
    static_evidence_scores.approved_symbol,
    static_evidence_scores.source_name,
    max((static_evidence_scores.source_display_name)::text) AS display_name,
    max(static_evidence_scores.normalized_score) AS normalized_score,
    'static'::text AS source_type
   FROM public.static_evidence_scores
  GROUP BY static_evidence_scores.gene_id, static_evidence_scores.approved_symbol, static_evidence_scores.source_name;


--
-- Name: data_source_progress; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.data_source_progress (
    id integer NOT NULL,
    source_name character varying NOT NULL,
    status public.source_status DEFAULT 'idle'::public.source_status NOT NULL,
    current_page integer DEFAULT 0,
    total_pages integer,
    current_item integer DEFAULT 0,
    total_items integer,
    items_processed integer DEFAULT 0,
    items_added integer DEFAULT 0,
    items_updated integer DEFAULT 0,
    items_failed integer DEFAULT 0,
    progress_percentage double precision DEFAULT '0'::double precision,
    current_operation character varying,
    last_error text,
    metadata jsonb DEFAULT '{}'::jsonb,
    started_at timestamp with time zone,
    completed_at timestamp with time zone,
    last_update_at timestamp with time zone DEFAULT now(),
    estimated_completion timestamp with time zone,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: data_source_progress_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.data_source_progress_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: data_source_progress_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.data_source_progress_id_seq OWNED BY public.data_source_progress.id;


--
-- Name: evidence_summary_view; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.evidence_summary_view AS
 SELECT ge.gene_id,
    g.approved_symbol AS symbol,
    g.hgnc_id,
    count(DISTINCT ge.source_name) AS source_count,
    array_agg(DISTINCT ge.source_name ORDER BY ge.source_name) AS sources,
    max(ge.evidence_date) AS latest_evidence_date,
    min(ge.evidence_date) AS earliest_evidence_date,
    COALESCE(avg(ge.evidence_score) FILTER (WHERE (ge.evidence_score IS NOT NULL)), (0)::double precision) AS avg_evidence_score,
    max(ge.evidence_score) AS max_evidence_score,
    jsonb_object_agg(ge.source_name, jsonb_build_object('evidence_date', ge.evidence_date, 'evidence_score', ge.evidence_score, 'source_detail', ge.source_detail)) AS source_details
   FROM (public.gene_evidence ge
     JOIN public.genes g ON ((ge.gene_id = g.id)))
  GROUP BY ge.gene_id, g.approved_symbol, g.hgnc_id;


--
-- Name: gene_curations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.gene_curations (
    id integer NOT NULL,
    gene_id integer NOT NULL,
    evidence_count integer,
    source_count integer,
    panelapp_panels text[],
    literature_refs text[],
    diagnostic_panels text[],
    hpo_terms text[],
    pubtator_pmids text[],
    omim_data jsonb,
    clinvar_data jsonb,
    constraint_scores jsonb,
    expression_data jsonb,
    evidence_score double precision,
    classification character varying(50),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: gene_curations_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.gene_curations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: gene_curations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.gene_curations_id_seq OWNED BY public.gene_curations.id;


--
-- Name: gene_evidence_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.gene_evidence_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: gene_evidence_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.gene_evidence_id_seq OWNED BY public.gene_evidence.id;


--
-- Name: gene_normalization_log; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.gene_normalization_log (
    id integer NOT NULL,
    original_text character varying NOT NULL,
    source_name character varying NOT NULL,
    success boolean NOT NULL,
    approved_symbol character varying,
    hgnc_id character varying,
    normalization_log jsonb NOT NULL,
    final_gene_id integer,
    staging_id integer,
    created_at timestamp without time zone NOT NULL,
    api_calls_made integer DEFAULT 0 NOT NULL,
    processing_time_ms integer
);


--
-- Name: gene_normalization_log_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.gene_normalization_log_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: gene_normalization_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.gene_normalization_log_id_seq OWNED BY public.gene_normalization_log.id;


--
-- Name: gene_normalization_staging; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.gene_normalization_staging (
    id integer NOT NULL,
    original_text character varying NOT NULL,
    source_name character varying NOT NULL,
    original_data jsonb,
    normalization_log jsonb NOT NULL,
    status character varying DEFAULT 'pending_review'::character varying NOT NULL,
    reviewed_by character varying,
    reviewed_at timestamp without time zone,
    review_notes text,
    manual_approved_symbol character varying,
    manual_hgnc_id character varying,
    manual_aliases jsonb,
    resolved_gene_id integer,
    resolution_method character varying,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    priority_score integer DEFAULT 0 NOT NULL,
    requires_expert_review boolean DEFAULT false NOT NULL,
    is_duplicate_submission boolean DEFAULT false NOT NULL
);


--
-- Name: gene_normalization_staging_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.gene_normalization_staging_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: gene_normalization_staging_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.gene_normalization_staging_id_seq OWNED BY public.gene_normalization_staging.id;


--
-- Name: gene_scores; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.gene_scores AS
 WITH source_counts AS (
         SELECT combined_evidence_scores.gene_id,
            count(DISTINCT combined_evidence_scores.source_name) AS source_count,
            count(*) AS evidence_count,
            sum(combined_evidence_scores.normalized_score) AS raw_score,
            jsonb_object_agg(COALESCE(combined_evidence_scores.display_name, combined_evidence_scores.source_name), round((combined_evidence_scores.normalized_score)::numeric, 3)) AS source_scores
           FROM public.combined_evidence_scores
          GROUP BY combined_evidence_scores.gene_id
        ), total_sources AS (
         SELECT count(DISTINCT all_sources.name) AS total
           FROM ( SELECT DISTINCT evidence_normalized_scores.source_name AS name
                   FROM public.evidence_normalized_scores
                  WHERE ((evidence_normalized_scores.source_name)::text !~~ 'static_%'::text)
                UNION
                 SELECT DISTINCT static_evidence_scores.source_name AS name
                   FROM public.static_evidence_scores) all_sources
        )
 SELECT sc.gene_id,
    g.approved_symbol,
    g.hgnc_id,
    sc.source_count,
    sc.evidence_count,
    sc.raw_score,
    round((((sc.raw_score / (ts.total)::double precision) * (100)::double precision))::numeric, 2) AS percentage_score,
    ts.total AS total_active_sources,
    sc.source_scores
   FROM ((source_counts sc
     CROSS JOIN total_sources ts)
     JOIN public.genes g ON ((sc.gene_id = g.id)));


--
-- Name: genes_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.genes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: genes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.genes_id_seq OWNED BY public.genes.id;


--
-- Name: pipeline_runs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pipeline_runs (
    id integer NOT NULL,
    status character varying(50),
    started_at timestamp without time zone,
    completed_at timestamp without time zone,
    stats jsonb,
    error_log text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: pipeline_runs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.pipeline_runs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: pipeline_runs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.pipeline_runs_id_seq OWNED BY public.pipeline_runs.id;


--
-- Name: pubtator_evidence_summary; Type: MATERIALIZED VIEW; Schema: public; Owner: -
--

CREATE MATERIALIZED VIEW public.pubtator_evidence_summary AS
 SELECT ge.gene_id,
    g.approved_symbol AS symbol,
    g.hgnc_id,
    ge.evidence_score,
    public.extract_pubtator_metrics(ge.evidence_data) AS pubtator_metrics,
    (ge.evidence_data -> 'pmids'::text) AS pmids,
    (ge.evidence_data -> 'top_mentions'::text) AS top_mentions,
    ge.evidence_date,
    ge.updated_at
   FROM (public.gene_evidence ge
     JOIN public.genes g ON ((ge.gene_id = g.id)))
  WHERE ((ge.source_name)::text = 'PubTator'::text)
  ORDER BY ge.evidence_score DESC NULLS LAST
  WITH NO DATA;


--
-- Name: static_evidence_uploads; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.static_evidence_uploads (
    id integer NOT NULL,
    source_id integer NOT NULL,
    evidence_name character varying(255) NOT NULL,
    file_hash character varying(64) NOT NULL,
    original_filename character varying(255),
    content_type character varying(50),
    upload_status character varying(50) DEFAULT 'pending'::character varying,
    processing_log jsonb DEFAULT '{}'::jsonb,
    gene_count integer,
    genes_normalized integer,
    genes_failed integer,
    genes_staged integer,
    upload_metadata jsonb DEFAULT '{}'::jsonb,
    processed_at timestamp with time zone,
    uploaded_by character varying(255),
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    CONSTRAINT upload_status_check CHECK (((upload_status)::text = ANY ((ARRAY['pending'::character varying, 'processing'::character varying, 'completed'::character varying, 'failed'::character varying, 'superseded'::character varying])::text[])))
);


--
-- Name: static_evidence_uploads_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.static_evidence_uploads_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: static_evidence_uploads_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.static_evidence_uploads_id_seq OWNED BY public.static_evidence_uploads.id;


--
-- Name: static_source_audit; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.static_source_audit (
    id integer NOT NULL,
    source_id integer NOT NULL,
    upload_id integer,
    action character varying(50) NOT NULL,
    details jsonb DEFAULT '{}'::jsonb,
    performed_by character varying(255),
    performed_at timestamp with time zone DEFAULT now()
);


--
-- Name: static_source_audit_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.static_source_audit_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: static_source_audit_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.static_source_audit_id_seq OWNED BY public.static_source_audit.id;


--
-- Name: static_sources_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.static_sources_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: static_sources_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.static_sources_id_seq OWNED BY public.static_sources.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id integer NOT NULL,
    email character varying(255) NOT NULL,
    hashed_password character varying(255) NOT NULL,
    is_admin boolean,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: data_source_progress id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.data_source_progress ALTER COLUMN id SET DEFAULT nextval('public.data_source_progress_id_seq'::regclass);


--
-- Name: gene_curations id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gene_curations ALTER COLUMN id SET DEFAULT nextval('public.gene_curations_id_seq'::regclass);


--
-- Name: gene_evidence id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gene_evidence ALTER COLUMN id SET DEFAULT nextval('public.gene_evidence_id_seq'::regclass);


--
-- Name: gene_normalization_log id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gene_normalization_log ALTER COLUMN id SET DEFAULT nextval('public.gene_normalization_log_id_seq'::regclass);


--
-- Name: gene_normalization_staging id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gene_normalization_staging ALTER COLUMN id SET DEFAULT nextval('public.gene_normalization_staging_id_seq'::regclass);


--
-- Name: genes id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.genes ALTER COLUMN id SET DEFAULT nextval('public.genes_id_seq'::regclass);


--
-- Name: pipeline_runs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pipeline_runs ALTER COLUMN id SET DEFAULT nextval('public.pipeline_runs_id_seq'::regclass);


--
-- Name: static_evidence_uploads id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.static_evidence_uploads ALTER COLUMN id SET DEFAULT nextval('public.static_evidence_uploads_id_seq'::regclass);


--
-- Name: static_source_audit id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.static_source_audit ALTER COLUMN id SET DEFAULT nextval('public.static_source_audit_id_seq'::regclass);


--
-- Name: static_sources id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.static_sources ALTER COLUMN id SET DEFAULT nextval('public.static_sources_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: cache_entries cache_entries_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cache_entries
    ADD CONSTRAINT cache_entries_pkey PRIMARY KEY (id);


--
-- Name: data_source_progress data_source_progress_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.data_source_progress
    ADD CONSTRAINT data_source_progress_pkey PRIMARY KEY (id);


--
-- Name: data_source_progress data_source_progress_source_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.data_source_progress
    ADD CONSTRAINT data_source_progress_source_name_key UNIQUE (source_name);


--
-- Name: gene_curations gene_curations_gene_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gene_curations
    ADD CONSTRAINT gene_curations_gene_id_key UNIQUE (gene_id);


--
-- Name: gene_curations gene_curations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gene_curations
    ADD CONSTRAINT gene_curations_pkey PRIMARY KEY (id);


--
-- Name: gene_evidence gene_evidence_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gene_evidence
    ADD CONSTRAINT gene_evidence_pkey PRIMARY KEY (id);


--
-- Name: gene_evidence gene_evidence_source_idx; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gene_evidence
    ADD CONSTRAINT gene_evidence_source_idx UNIQUE (gene_id, source_name, source_detail);


--
-- Name: gene_normalization_log gene_normalization_log_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gene_normalization_log
    ADD CONSTRAINT gene_normalization_log_pkey PRIMARY KEY (id);


--
-- Name: gene_normalization_staging gene_normalization_staging_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gene_normalization_staging
    ADD CONSTRAINT gene_normalization_staging_pkey PRIMARY KEY (id);


--
-- Name: genes genes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.genes
    ADD CONSTRAINT genes_pkey PRIMARY KEY (id);


--
-- Name: pipeline_runs pipeline_runs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pipeline_runs
    ADD CONSTRAINT pipeline_runs_pkey PRIMARY KEY (id);


--
-- Name: static_evidence_uploads static_evidence_uploads_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.static_evidence_uploads
    ADD CONSTRAINT static_evidence_uploads_pkey PRIMARY KEY (id);


--
-- Name: static_source_audit static_source_audit_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.static_source_audit
    ADD CONSTRAINT static_source_audit_pkey PRIMARY KEY (id);


--
-- Name: static_sources static_sources_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.static_sources
    ADD CONSTRAINT static_sources_pkey PRIMARY KEY (id);


--
-- Name: static_sources static_sources_source_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.static_sources
    ADD CONSTRAINT static_sources_source_name_key UNIQUE (source_name);


--
-- Name: static_evidence_uploads unique_upload_per_source; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.static_evidence_uploads
    ADD CONSTRAINT unique_upload_per_source UNIQUE (source_id, file_hash);


--
-- Name: cache_entries uq_cache_entries_cache_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cache_entries
    ADD CONSTRAINT uq_cache_entries_cache_key UNIQUE (cache_key);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: idx_audit_source_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_source_id ON public.static_source_audit USING btree (source_id);


--
-- Name: idx_cache_entries_expires_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_cache_entries_expires_at ON public.cache_entries USING btree (expires_at) WHERE (expires_at IS NOT NULL);


--
-- Name: idx_cache_entries_last_accessed; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_cache_entries_last_accessed ON public.cache_entries USING btree (last_accessed);


--
-- Name: idx_cache_entries_namespace; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_cache_entries_namespace ON public.cache_entries USING btree (namespace);


--
-- Name: idx_cache_entries_namespace_key; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_cache_entries_namespace_key ON public.cache_entries USING btree (namespace, cache_key);


--
-- Name: idx_data_source_progress_source_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_data_source_progress_source_name ON public.data_source_progress USING btree (source_name);


--
-- Name: idx_evidence_merge_history; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_evidence_merge_history ON public.gene_evidence USING btree (((evidence_data -> 'merge_history'::text))) WHERE (evidence_data ? 'merge_history'::text);


--
-- Name: idx_gene_evidence_score; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_gene_evidence_score ON public.gene_evidence USING btree (evidence_score) WHERE (evidence_score IS NOT NULL);


--
-- Name: idx_gene_evidence_source_score; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_gene_evidence_source_score ON public.gene_evidence USING btree (source_name, evidence_score) WHERE (evidence_score IS NOT NULL);


--
-- Name: idx_pubtator_evidence_summary_gene_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pubtator_evidence_summary_gene_id ON public.pubtator_evidence_summary USING btree (gene_id);


--
-- Name: idx_pubtator_evidence_summary_score; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pubtator_evidence_summary_score ON public.pubtator_evidence_summary USING btree (evidence_score DESC NULLS LAST);


--
-- Name: idx_static_sources_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_static_sources_active ON public.static_sources USING btree (is_active);


--
-- Name: idx_static_sources_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_static_sources_type ON public.static_sources USING btree (source_type);


--
-- Name: idx_uploads_hash; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_uploads_hash ON public.static_evidence_uploads USING btree (file_hash);


--
-- Name: idx_uploads_source_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_uploads_source_id ON public.static_evidence_uploads USING btree (source_id);


--
-- Name: idx_uploads_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_uploads_status ON public.static_evidence_uploads USING btree (upload_status);


--
-- Name: ix_gene_curations_evidence_score; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_gene_curations_evidence_score ON public.gene_curations USING btree (evidence_score);


--
-- Name: ix_gene_curations_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_gene_curations_id ON public.gene_curations USING btree (id);


--
-- Name: ix_gene_evidence_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_gene_evidence_id ON public.gene_evidence USING btree (id);


--
-- Name: ix_gene_evidence_source_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_gene_evidence_source_name ON public.gene_evidence USING btree (source_name);


--
-- Name: ix_gene_normalization_log_approved_symbol; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_gene_normalization_log_approved_symbol ON public.gene_normalization_log USING btree (approved_symbol);


--
-- Name: ix_gene_normalization_log_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_gene_normalization_log_created_at ON public.gene_normalization_log USING btree (created_at);


--
-- Name: ix_gene_normalization_log_hgnc_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_gene_normalization_log_hgnc_id ON public.gene_normalization_log USING btree (hgnc_id);


--
-- Name: ix_gene_normalization_log_original_text; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_gene_normalization_log_original_text ON public.gene_normalization_log USING btree (original_text);


--
-- Name: ix_gene_normalization_log_source_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_gene_normalization_log_source_name ON public.gene_normalization_log USING btree (source_name);


--
-- Name: ix_gene_normalization_log_success; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_gene_normalization_log_success ON public.gene_normalization_log USING btree (success);


--
-- Name: ix_gene_normalization_staging_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_gene_normalization_staging_created_at ON public.gene_normalization_staging USING btree (created_at);


--
-- Name: ix_gene_normalization_staging_original_text; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_gene_normalization_staging_original_text ON public.gene_normalization_staging USING btree (original_text);


--
-- Name: ix_gene_normalization_staging_priority_score; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_gene_normalization_staging_priority_score ON public.gene_normalization_staging USING btree (priority_score);


--
-- Name: ix_gene_normalization_staging_source_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_gene_normalization_staging_source_name ON public.gene_normalization_staging USING btree (source_name);


--
-- Name: ix_gene_normalization_staging_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_gene_normalization_staging_status ON public.gene_normalization_staging USING btree (status);


--
-- Name: ix_genes_approved_symbol; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_genes_approved_symbol ON public.genes USING btree (approved_symbol);


--
-- Name: ix_genes_hgnc_id; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_genes_hgnc_id ON public.genes USING btree (hgnc_id);


--
-- Name: ix_genes_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_genes_id ON public.genes USING btree (id);


--
-- Name: ix_pipeline_runs_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pipeline_runs_id ON public.pipeline_runs USING btree (id);


--
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);


--
-- Name: ix_users_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_users_id ON public.users USING btree (id);


--
-- Name: gene_evidence update_curation_on_evidence_change; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_curation_on_evidence_change AFTER INSERT OR DELETE OR UPDATE ON public.gene_evidence FOR EACH ROW EXECUTE FUNCTION public.update_gene_curation_on_evidence_change();


--
-- Name: TRIGGER update_curation_on_evidence_change ON gene_evidence; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TRIGGER update_curation_on_evidence_change ON public.gene_evidence IS 'Automatically updates gene_curations when evidence changes to maintain data consistency';


--
-- Name: gene_curations gene_curations_gene_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gene_curations
    ADD CONSTRAINT gene_curations_gene_id_fkey FOREIGN KEY (gene_id) REFERENCES public.genes(id);


--
-- Name: gene_evidence gene_evidence_gene_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gene_evidence
    ADD CONSTRAINT gene_evidence_gene_id_fkey FOREIGN KEY (gene_id) REFERENCES public.genes(id) ON DELETE CASCADE;


--
-- Name: static_evidence_uploads static_evidence_uploads_source_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.static_evidence_uploads
    ADD CONSTRAINT static_evidence_uploads_source_id_fkey FOREIGN KEY (source_id) REFERENCES public.static_sources(id) ON DELETE CASCADE;


--
-- Name: static_source_audit static_source_audit_source_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.static_source_audit
    ADD CONSTRAINT static_source_audit_source_id_fkey FOREIGN KEY (source_id) REFERENCES public.static_sources(id) ON DELETE CASCADE;


--
-- Name: static_source_audit static_source_audit_upload_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.static_source_audit
    ADD CONSTRAINT static_source_audit_upload_id_fkey FOREIGN KEY (upload_id) REFERENCES public.static_evidence_uploads(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict jlU0eQMbtgvDcA0BmY1pn3b9FsFdbLQzWKKuYPzi87lWOIt8htpxFWZoHzpzksO

