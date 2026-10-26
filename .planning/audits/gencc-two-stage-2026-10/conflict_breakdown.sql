-- GenCC conflict breakdown: DiStefano 2022 Level 3 (migration 0008, current) vs the
-- gene-level DiStefano rule of commit ac4c83a and the 0006 >= 2-rank rule (v0.10.0).
-- Run: psql -At -f conflict_breakdown.sql against the snapshot (reads gene_evidence only).
WITH s AS (
  SELECT ge.id, g.approved_symbol sym, x->>'submitter' sub,
    NULLIF(btrim(x->'raw_data'->>'disease_curie'), '') dis, NULLIF(btrim(x->'raw_data'->>'moi_curie'), '') moi,
    lower(btrim(x->>'classification')) = 'no known disease relationship' nkdr,
    CASE lower(btrim(x->>'classification')) WHEN 'definitive' THEN 6 WHEN 'strong' THEN 5 WHEN 'moderate' THEN 4
      WHEN 'limited' THEN 2 WHEN 'disputed evidence' THEN 1
      WHEN 'no known disease relationship' THEN 0 WHEN 'refuted evidence' THEN 0 END r
  FROM gene_evidence ge JOIN genes g ON g.id = ge.gene_id, jsonb_array_elements(ge.evidence_data->'submissions') x
  WHERE ge.source_name = 'GenCC'
), c AS (  -- gene level: strongest class per counted submitter
  SELECT id, sym, sub, max(r) r FROM s WHERE sub <> 'ClinGen' AND r IS NOT NULL GROUP BY 1,2,3
), gene AS (
  SELECT id, sym, bool_or(r >= 4) AND bool_or(r <= 2) gene_level, max(r)-min(r) >= 2 rank_spread FROM c GROUP BY 1,2
), l3s AS (  -- Level 3: strongest class per counted submitter within (disease, MOI)
  SELECT id, dis, moi, sub, max(r) r,
    -- the submitter's strongest class here is NKDR (rank 0 and no Refuted at rank 0)
    max(r) = 0 AND bool_and(nkdr OR r > 0) only_nkdr_low
  FROM s WHERE sub <> 'ClinGen' AND r IS NOT NULL AND dis IS NOT NULL AND moi IS NOT NULL GROUP BY 1,2,3,4
), l3 AS (
  SELECT id, bool_or(hi AND lo) level3, bool_or(hi AND lo_wo_nkdr) level3_wo_nkdr FROM (
    SELECT id, bool_or(r >= 4) hi, bool_or(r <= 2) lo, bool_or(r <= 2 AND NOT only_nkdr_low) lo_wo_nkdr
    FROM l3s GROUP BY id, dis, moi) t GROUP BY 1
), j AS (SELECT gene.*, coalesce(l3.level3, false) level3, coalesce(l3.level3_wo_nkdr, false) level3_wo_nkdr
         FROM gene LEFT JOIN l3 USING (id))
SELECT 'counts: level3 | ac4c83a gene-level | 0006 | level3 only via NKDR',
       (count(*) FILTER (WHERE level3))::text,
       (count(*) FILTER (WHERE gene_level))::text,
       (count(*) FILTER (WHERE rank_spread))::text,
       (count(*) FILTER (WHERE level3 AND NOT level3_wo_nkdr))::text
FROM j
UNION ALL SELECT 'level3 not gene_level', string_agg(sym, ' ' ORDER BY sym), NULL, NULL, NULL FROM j WHERE level3 AND NOT gene_level
UNION ALL SELECT 'gene_level not level3', string_agg(sym, ' ' ORDER BY sym), NULL, NULL, NULL FROM j WHERE gene_level AND NOT level3
UNION ALL SELECT 'level3 not 0006', string_agg(sym, ' ' ORDER BY sym), NULL, NULL, NULL FROM j WHERE level3 AND NOT rank_spread
UNION ALL SELECT '0006 not level3', string_agg(sym, ' ' ORDER BY sym), NULL, NULL, NULL FROM j WHERE rank_spread AND NOT level3
UNION ALL SELECT 'level3 only via NKDR', string_agg(sym, ' ' ORDER BY sym), NULL, NULL, NULL FROM j WHERE level3 AND NOT level3_wo_nkdr;
