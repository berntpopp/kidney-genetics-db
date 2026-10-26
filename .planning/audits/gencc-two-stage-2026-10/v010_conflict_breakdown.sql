-- v0.10.0 (migration 0006, >= 2-rank rule, Supportive unranked): superseded by conflict_breakdown.sql.
-- Run: psql -At -f v010_conflict_breakdown.sql against the snapshot.
WITH s AS (
  SELECT ge.id, x->>'submitter' sub,
    CASE lower(btrim(x->>'classification')) WHEN 'definitive' THEN 6 WHEN 'strong' THEN 5 WHEN 'moderate' THEN 4
      WHEN 'limited' THEN 2 WHEN 'disputed evidence' THEN 1
      WHEN 'no known disease relationship' THEN 0 WHEN 'refuted evidence' THEN 0 END r
  FROM gene_evidence ge, jsonb_array_elements(ge.evidence_data->'submissions') x WHERE source_name='GenCC'
), c AS (SELECT id, sub, max(r) r FROM s WHERE sub <> 'ClinGen' AND r IS NOT NULL GROUP BY 1,2),
g AS (SELECT id, max(r)-min(r) spread, min(r) lo, max(r) hi FROM c GROUP BY 1)
SELECT count(*) FILTER (WHERE spread>=2) AS penalized,
       -- DiStefano 2022 conflict: Limited/Disputed/Refuted (rank <= 2) vs Moderate/Strong/Definitive (rank >= 4)
       count(*) FILTER (WHERE spread>=2 AND lo<=2 AND hi>=4) AS distefano_conflict,
       count(*) FILTER (WHERE spread>=2 AND lo>=4) AS definitive_vs_moderate_only,
       count(*) FILTER (WHERE spread>=2 AND hi<=2) AS low_ranks_only
FROM g;
