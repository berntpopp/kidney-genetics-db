# Leiden objective and resolution sweep (#331)

**Decision:** Leiden uses the `modularity` objective, `resolution: 0.8`,
`iterations: -1` (until stable) and the request seed (default 0), set in
`backend/config/network_analysis.yaml`. Objective, resolution, iterations and
seed are echoed in the `/api/network/cluster` response `parameters`.

## Data

- Real well-supported network, built read-only from the dev database
  (`kidney_genetics_postgres`, every session `default_transaction_read_only=on`)
  through `NetworkAnalysisService.build_network_from_string_data`, the API's own
  build path.
- Genes: `gene_scores.evidence_group = 'well_supported' AND percentage_score > 0`
  (622 genes), STRING score >= 400, no node filters (API defaults).
- Graph: 622 nodes, 2657 edges, 150 isolated nodes, 164 components. Isolated
  nodes and small components are singleton or tiny clusters at any resolution,
  so the count of clusters with >= 3 genes is also reported.
- 10 seeds (0-9) per setting; ARI over all 45 seed pairs
  (`igraph.compare_communities(method="adjusted_rand")`). Modularity is standard
  weighted modularity (resolution 1) of the resulting partition, mean over seeds.

## Sweep (iterations: 2, the previous setting)

| objective | resolution | clusters mean (range) | clusters >= 3 genes | modularity | mean ARI | min ARI |
|---|---|---|---|---|---|---|
| CPM (previous) | 1.0 | 388.3 (387-390) | 46.1 | 0.522 | 0.972 | 0.947 |
| modularity | 0.2 | 172.3 (172-173) | 15.3 | 0.690 | 0.909 | 0.799 |
| modularity | 0.4 | 175.2 (175-177) | 18.2 | 0.781 | 0.862 | 0.682 |
| modularity | 0.6 | 177.3 (176-179) | 20.3 | 0.790 | 0.916 | 0.792 |
| modularity | 0.8 | 180.9 (179-182) | 23.9 | 0.796 | 0.933 | 0.847 |
| modularity | 1.0 | 182.5 (180-184) | 25.5 | 0.796 | 0.893 | 0.776 |
| modularity | 1.2 | 184.5 (183-185) | 27.5 | 0.796 | 0.885 | 0.747 |
| modularity | 1.4 | 185.2 (184-186) | 28.2 | 0.794 | 0.880 | 0.800 |
| modularity | 1.6 | 187.7 (186-189) | 30.7 | 0.790 | 0.826 | 0.699 |
| modularity | 1.8 | 188.5 (188-189) | 31.5 | 0.788 | 0.828 | 0.719 |
| modularity | 2.0 | 189.5 (188-191) | 31.5 | 0.784 | 0.844 | 0.685 |

## Iterating until stable (iterations: -1)

| objective | resolution | clusters mean (range) | clusters >= 3 genes | modularity | mean ARI | min ARI |
|---|---|---|---|---|---|---|
| modularity | 0.6 | 177.2 (177-178) | 20.2 | 0.790 | 0.944 | 0.812 |
| modularity | 0.8 | 181.0 (180-182) | 24.0 | 0.796 | 0.957 | 0.872 |
| modularity | 1.0 | 182.8 (181-184) | 25.8 | 0.797 | 0.915 | 0.853 |

30 converged runs including the graph build took 2.6 s.

## Choice

- CPM at resolution 1.0 fragments the network: 388 clusters, 46 with >= 3
  genes, modularity 0.52. Its high ARI reflects near-singleton partitions, not
  stable communities.
- Modularity peaks at 0.796-0.797 over 0.8-1.2; resolution 0.8 has the highest
  seed stability in that plateau (mean ARI 0.933 at 2 iterations, 0.957
  converged) and about 24 communities with >= 3 genes.
- Iterating until stable raises stability at negligible cost, so `iterations: -1`.
- Remaining seed sensitivity (min ARI 0.87) is why the seed is fixed (default 0)
  and reported; published numbers must cite objective, resolution, iterations
  and seed.

Before/after for this network (mean over seeds 0-9): about 388 clusters (46 with
>= 3 genes) with CPM 1.0, about 181 (24 with >= 3 genes) with modularity 0.8.
The sweep reflects the 2026-10-21 dev snapshot; re-run it if the gene set or
STRING data changes materially.
