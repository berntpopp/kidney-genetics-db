-- v1 (Supportive ranked 3): first run, superseded by conflict_breakdown.sql.
WITH s AS (
  SELECT ge.id, x->>'submitter' sub,
    CASE lower(btrim(x->>'classification')) WHEN 'definitive' THEN 6 WHEN 'strong' THEN 5 WHEN 'moderate' THEN 4
      WHEN 'supportive' THEN 3 WHEN 'limited' THEN 2 WHEN 'disputed evidence' THEN 1
      WHEN 'no known disease relationship' THEN 0 WHEN 'refuted evidence' THEN 0 END r
  FROM gene_evidence ge, jsonb_array_elements(ge.evidence_data->'submissions') x WHERE source_name='GenCC'
), c AS (SELECT id, sub, max(r) r FROM s WHERE sub <> 'ClinGen' AND r IS NOT NULL GROUP BY 1,2),
g AS (SELECT id, max(r)-min(r) spread,
        max(r) FILTER (WHERE r<>3) - min(r) FILTER (WHERE r<>3) spread_wo_supportive,
        bool_or(sub='Orphanet' AND r=3) orpha_supportive FROM c GROUP BY 1)
SELECT count(*) FILTER (WHERE spread>=2) penalized,
       count(*) FILTER (WHERE spread>=2 AND coalesce(spread_wo_supportive,0)<2) only_via_supportive,
       count(*) FILTER (WHERE spread>=2 AND orpha_supportive) with_orphanet_supportive
FROM g;
SELECT x->>'submitter', count(*) FROM gene_evidence ge, jsonb_array_elements(ge.evidence_data->'submissions') x WHERE source_name='GenCC' AND x->>'classification'='Supportive' GROUP BY 1;
SELECT count(*) FROM gene_evidence ge WHERE source_name='GenCC' AND
  (SELECT max(CASE lower(btrim(x->>'classification')) WHEN 'definitive' THEN 1.0 WHEN 'strong' THEN 0.8 WHEN 'moderate' THEN 0.6 WHEN 'supportive' THEN 0.5 WHEN 'limited' THEN 0.4 WHEN 'disputed evidence' THEN 0.2 ELSE 0.0 END) FROM jsonb_array_elements(ge.evidence_data->'submissions') x)
  IS DISTINCT FROM
  (SELECT max(CASE lower(replace(e.value::text,'"','')) WHEN 'definitive' THEN 1.0 WHEN 'strong' THEN 0.8 WHEN 'moderate' THEN 0.6 WHEN 'supportive' THEN 0.5 WHEN 'limited' THEN 0.4 WHEN 'disputed evidence' THEN 0.2 ELSE 0.0 END) FROM jsonb_array_elements(ge.evidence_data->'classifications') e);
SELECT count(*) FROM gene_evidence ge, jsonb_array_elements(ge.evidence_data->'submissions') x WHERE source_name='GenCC' AND coalesce(btrim(x->>'submitter'),'')='';
