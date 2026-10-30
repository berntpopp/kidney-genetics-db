"""
Enrichment Service

Provides functional enrichment analysis for gene clusters.
Supports HPO, GO, and KEGG enrichment using Fisher's exact test and GSEApy.

CRITICAL DESIGN PATTERNS:
- Thread-safe: Session passed per-call
- Timeout protection: GSEApy calls have 120s timeout
- Rate limiting: 2s minimum interval between Enrichr API calls
- Reuses: HPO infrastructure, singleton thread pool
"""

import asyncio
import functools
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, cast

import numpy as np
import pandas as pd
from scipy.stats import fisher_exact
from sqlalchemy import text
from sqlalchemy.orm import Session
from statsmodels.stats.multitest import fdrcorrection

from app.core.cache_service import get_cache_service
from app.core.database import get_thread_pool_executor
from app.core.datasource_config import get_config, get_source_parameter
from app.core.hpo.terms import HPOTerms
from app.core.logging import get_logger
from app.models.gene import Gene
from app.pipeline.sources.annotations.hpo import (
    ClinicalGroupClassifier,
    download_pinned_hp_json,
    load_hpo_parents,
)

logger = get_logger(__name__)

# Cleared with the network_analysis namespace after every successful source update
HPO_TERM_GENES_CACHE_KEY = "hpo_kidney_term_genes:true_path"
TERM_NAME_CONCURRENCY = 10

# Lazy import of gseapy (not always needed)
try:
    import gseapy as gp

    GSEAPY_AVAILABLE = True
except ImportError:
    GSEAPY_AVAILABLE = False
    logger.sync_warning("GSEApy not available - GO/KEGG enrichment disabled")


_ENRICHR_GO_TERM = re.compile(r"^(?P<name>.+) \((?P<id>GO:\d{7})\)$")


def split_enrichr_term(term: str) -> tuple[str, str]:
    """Enrichr GO terms read "Name (GO:0000000)"; return (id, name). Other libraries
    (e.g. KEGG) carry no ID, so the term doubles as its ID."""
    match = _ENRICHR_GO_TERM.match(term)
    return (match["id"], match["name"]) if match else (term, term)


class EnrichmentService:
    """
    Service for functional enrichment analysis of gene clusters.

    Features:
    - HPO term enrichment (Fisher's exact test)
    - GO/KEGG enrichment (via GSEApy)
    - FDR correction (Benjamini-Hochberg)
    - Rate limiting for Enrichr API
    """

    def __init__(self) -> None:
        """
        Initialize enrichment service.

        IMPORTANT: Session NOT stored - passed per-call for thread safety.
        """
        enrichment = get_config().enrichment
        hpo_config, go_config = enrichment.get("hpo", {}), enrichment.get("go", {})
        self.hpo_client = HPOTerms()
        self._executor = get_thread_pool_executor()
        # Terms with fewer annotated genes in the tested universe are not tested (gene-set size)
        self.min_term_genes: int = hpo_config.get("min_term_genes", 2)
        # Pinned HPO is_a graph + kidney subtree, loaded once per process for true-path
        self._ontology: tuple[ClinicalGroupClassifier, frozenset[str]] | None = None
        self._ontology_lock = asyncio.Lock()

        # Enrichr calls get their own pool: a timed-out call must not occupy the shared DB pool
        self._enrichr_executor = ThreadPoolExecutor(
            max_workers=go_config.get("max_concurrent_requests", 1),
            thread_name_prefix="enrichr",
        )
        # Rate limiting for GSEApy/Enrichr API (prevents IP blocking)
        self._last_enrichr_call: float = 0.0
        self._enrichr_min_interval: float = go_config.get("min_request_interval", 2.0)
        self._enrichr_lock = threading.Lock()

    async def enrich_hpo_terms(
        self,
        cluster_genes: list[int],
        session: Session,
        background_genes: list[int] | None = None,
        fdr_threshold: float = 0.05,
    ) -> tuple[list[dict[str, Any]], list[int]]:
        """
        Perform HPO term enrichment using Fisher's exact test.

        The tested universe is every gene with a kidney HPO annotation, intersected with
        ``background_genes`` when given. Cluster genes outside it (unannotated,
        not in the background, or unknown) are not tested and are returned as excluded.

        Args:
            cluster_genes: Gene IDs in cluster to test for enrichment
            session: Database session (passed per-call)
            background_genes: Background gene IDs (default: all kidney HPO-annotated genes)
            fdr_threshold: FDR cutoff for significance (default: 0.05)

        Returns:
            (results, excluded cluster gene IDs), results being
            [
                {
                    "term_id": "HP:0000107",
                    "term_name": "Renal cyst",
                    "p_value": 1.2e-12,
                    "fdr": 2.3e-10,
                    "gene_count": 14,
                    "cluster_size": 17,
                    "background_count": 80,
                    "genes": ["WT1", "PAX2", ...],
                    "enrichment_score": 8.5,
                    "odds_ratio": 12.3
                },
                ...
            ]
        """
        id_to_symbol = self._gene_symbols(cluster_genes, session)
        if not id_to_symbol:
            await logger.warning("No valid genes found in cluster")
            return [], sorted(set(cluster_genes))

        per_community, excluded = await self._run_hpo_tests(
            [cluster_genes], id_to_symbol, session, background_genes
        )
        results = per_community[0]
        if not results:
            await logger.info("No HPO terms enriched in cluster")
            return [], excluded[0]

        self._apply_bh(results)
        results = self._filter_and_sort(results, fdr_threshold)
        await self._fill_term_names(results)

        await logger.info(
            "HPO enrichment complete",
            significant_terms=len(results),
            cluster_size=len(id_to_symbol),
            fdr_threshold=fdr_threshold,
        )

        return results, excluded[0]

    async def enrich_hpo_terms_batch(
        self,
        communities: list[list[int]],
        session: Session,
        fdr_threshold: float = 0.05,
        background_genes: list[int] | None = None,
    ) -> tuple[list[list[dict[str, Any]]], int, list[list[int]]]:
        """
        HPO enrichment for several communities with one Benjamini-Hochberg
        correction pooled over all community x term pairs with at least one
        overlapping community gene, the same family as the single-community
        test, not every possible pair (#332).

        Returns (results per community in submitted order, pooled test count,
        excluded gene IDs per community; universe as in enrich_hpo_terms).
        """
        id_to_symbol = self._gene_symbols([g for c in communities for g in c], session)
        per_community, excluded = await self._run_hpo_tests(
            communities, id_to_symbol, session, background_genes
        )
        pooled = [r for results in per_community for r in results]
        if pooled:
            self._apply_bh(pooled)  # mutates the shared result dicts

        significant = [self._filter_and_sort(r, fdr_threshold) for r in per_community]
        await self._fill_term_names([r for results in significant for r in results])
        return significant, len(pooled), excluded

    @staticmethod
    def _gene_symbols(gene_ids: list[int], session: Session) -> dict[int, str]:
        rows = session.query(Gene.id, Gene.approved_symbol).filter(Gene.id.in_(gene_ids)).all()
        return {row.id: row.approved_symbol for row in rows}

    async def _run_hpo_tests(
        self,
        communities: list[list[int]],
        id_to_symbol: dict[int, str],
        session: Session,
        background_genes: list[int] | None = None,
    ) -> tuple[list[list[dict[str, Any]]], list[list[int]]]:
        """
        Fisher tests per community (raw p only), run off the event loop.

        All four contingency counts come from one universe (#289): kidney HPO-annotated
        genes, intersected with background_genes when given. Returns
        (results per community, excluded cluster gene IDs per community).
        """
        hpo_term_to_genes = await self._get_hpo_annotations(session)
        if not hpo_term_to_genes:
            await logger.warning("No HPO annotations found in database")
            return [[] for _ in communities], [sorted(set(c)) for c in communities]

        universe: set[str] = set().union(*hpo_term_to_genes.values())
        if background_genes is not None:
            universe &= set(self._gene_symbols(background_genes, session).values())
        term_to_genes = {
            t: in_universe
            for t, g in hpo_term_to_genes.items()
            if len(in_universe := g & universe) >= self.min_term_genes
        }
        await logger.info(
            "HPO enrichment background",
            communities=len(communities),
            background_size=len(universe),
            custom_background=background_genes is not None,
            hpo_terms=len(term_to_genes),
        )

        symbol_sets = [
            {id_to_symbol[g] for g in c if id_to_symbol.get(g) in universe} for c in communities
        ]
        excluded = [
            sorted({g for g in c if id_to_symbol.get(g) not in universe}) for c in communities
        ]
        loop = asyncio.get_event_loop()
        per_community = await loop.run_in_executor(
            self._executor,
            lambda: [
                self._hpo_fisher_tests(symbols, term_to_genes, len(universe))
                for symbols in symbol_sets
            ],
        )
        return per_community, excluded

    @staticmethod
    def _hpo_fisher_tests(
        cluster_symbols: set[str], hpo_term_to_genes: dict[str, set], total_background: int
    ) -> list[dict[str, Any]]:
        """One-sided Fisher's exact test per HPO term with any cluster overlap (raw p only)."""
        results = []

        for term_id, term_genes in hpo_term_to_genes.items():
            # Contingency table for Fisher's exact test
            # [[a, b], [c, d]]
            # a = cluster genes with term
            # b = cluster genes without term
            # c = background genes with term (excluding cluster)
            # d = background genes without term (excluding cluster)

            a = len(cluster_symbols & term_genes)  # Intersection
            b = len(cluster_symbols) - a
            c = len(term_genes) - a
            d = total_background - len(cluster_symbols) - c

            if a == 0:
                continue  # No overlap - skip
            if min(b, c, d) < 0:  # cluster or term not within the universe (#289)
                raise ValueError(f"Invalid contingency table for {term_id}: {[[a, b], [c, d]]}")

            # Fisher's exact test (one-tailed, testing for over-representation)
            odds_ratio, p_value = fisher_exact([[a, b], [c, d]], alternative="greater")

            # Cap infinite odds ratios to a large finite value for JSON serialization
            # Infinity occurs with perfect enrichment (all cluster genes have term)
            if np.isinf(odds_ratio):
                odds_ratio = 1000.0

            results.append(
                {
                    "term_id": term_id,
                    "term_name": None,  # Will be filled later
                    "p_value": float(p_value),
                    "gene_count": a,
                    "cluster_size": len(cluster_symbols),
                    "background_count": len(term_genes),
                    "genes": sorted(cluster_symbols & term_genes),
                    "odds_ratio": float(odds_ratio),
                }
            )

        return results

    @staticmethod
    def _apply_bh(results: list[dict[str, Any]]) -> None:
        """Benjamini-Hochberg over exactly these results."""
        _, fdr_values = fdrcorrection([r["p_value"] for r in results])

        for i, result in enumerate(results):
            fdr_val = float(fdr_values[i])
            result["fdr"] = fdr_val
            result["enrichment_score"] = -np.log10(fdr_val) if fdr_val > 0 else 100.0

    async def _fill_term_names(self, results: list[dict[str, Any]]) -> None:
        """Get term names from HPO API (call after filtering: significant rows only)."""
        semaphore = asyncio.Semaphore(TERM_NAME_CONCURRENCY)

        async def fill(result: dict[str, Any]) -> None:
            hpo_term_id = str(result["term_id"])
            try:
                async with semaphore:
                    term = await self.hpo_client.get_term(hpo_term_id)
                result["term_name"] = term.name if term else hpo_term_id
            except Exception as e:
                await logger.debug(f"Failed to get HPO term name: {e}", term_id=hpo_term_id)
                result["term_name"] = hpo_term_id

        await asyncio.gather(*(fill(r) for r in results))

    @staticmethod
    def _filter_and_sort(
        results: list[dict[str, Any]], fdr_threshold: float
    ) -> list[dict[str, Any]]:
        # fdr is always set as float by _apply_bh
        kept = [r for r in results if cast(float, r["fdr"]) < fdr_threshold]
        kept.sort(key=lambda x: cast(float, x["fdr"]))
        return kept

    async def enrich_go_terms(
        self,
        cluster_genes: list[int],
        session: Session,
        gene_set: str = "GO_Biological_Process_2023",
        fdr_threshold: float = 0.05,
        timeout_seconds: int = 120,
        background_genes: list[int] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Perform GO/KEGG enrichment using GSEApy with timeout and rate limiting.

        Args:
            cluster_genes: Gene IDs in cluster
            session: Database session
            gene_set: GSEApy gene set name (GO_Biological_Process_2023, KEGG_2021_Human, etc.)
            fdr_threshold: FDR cutoff
            timeout_seconds: Maximum time to wait for Enrichr API (default: 120s)
            background_genes: Background gene IDs; when given, Enrichr's background
                endpoint (speedrichr backgroundenrich) tests against them instead of the
                library's genome background, and cluster genes outside it are not tested

        Returns:
            Same format as enrich_hpo_terms
        """
        if not GSEAPY_AVAILABLE:
            await logger.error("GSEApy not installed - cannot perform GO enrichment")
            return []

        # Get gene symbols
        genes = session.query(Gene).filter(Gene.id.in_(cluster_genes)).all()
        gene_symbols = [g.approved_symbol for g in genes]

        background: list[str] | None = None
        if background_genes is not None:
            background_set = set(self._gene_symbols(background_genes, session).values())
            background = sorted(background_set)
            gene_symbols = [s for s in gene_symbols if s in background_set]

        if not gene_symbols:
            await logger.warning("No valid genes found in cluster")
            return []

        # Run GSEApy with timeout and rate limiting
        loop = asyncio.get_event_loop()

        try:
            enr_result = await asyncio.wait_for(
                loop.run_in_executor(
                    self._enrichr_executor,
                    self._run_gseapy_enrichr_safe,
                    gene_symbols,
                    gene_set,
                    background,
                    timeout_seconds,
                ),
                timeout=timeout_seconds,
            )

            if enr_result is None:
                await logger.warning("GSEApy enrichment returned None (API failure)")
                return []

        except asyncio.TimeoutError:
            await logger.error(
                f"GSEApy enrichment timed out after {timeout_seconds}s",
                gene_count=len(gene_symbols),
                gene_set=gene_set,
            )
            return []
        except Exception as e:
            await logger.error(f"GSEApy enrichment failed: {e}", gene_set=gene_set)
            return []

        # Convert GSEApy results to our format
        results = []

        # gseapy leaves results as [] when no library returned hits
        if not isinstance(enr_result.results, pd.DataFrame) or enr_result.results.empty:
            await logger.info("No GO terms enriched in cluster")
            return []

        for _, row in enr_result.results.iterrows():
            if row["Adjusted P-value"] > fdr_threshold:
                continue

            gene_list = row["Genes"].split(";") if isinstance(row["Genes"], str) else []
            term_id, term_name = split_enrichr_term(row["Term"])

            # Cap infinite values for JSON serialization
            odds_ratio = float(row.get("Odds Ratio", 0))
            if np.isinf(odds_ratio):
                odds_ratio = 1000.0

            combined_score = float(row["Combined Score"])
            if np.isinf(combined_score):
                combined_score = 1000.0

            results.append(
                {
                    "term_id": term_id,
                    "term_name": term_name,
                    "p_value": float(row["P-value"]),
                    "fdr": float(row["Adjusted P-value"]),
                    "gene_count": len(gene_list),
                    "cluster_size": len(gene_symbols),
                    "background_count": None,  # Not provided by Enrichr
                    "genes": gene_list,
                    "enrichment_score": -np.log10(row["Adjusted P-value"])
                    if row["Adjusted P-value"] > 0
                    else 100.0,
                    "odds_ratio": odds_ratio,
                    "combined_score": combined_score,  # Enrichr-specific
                }
            )

        await logger.info(
            "GO enrichment complete",
            significant_terms=len(results),
            gene_set=gene_set,
            cluster_size=len(gene_symbols),
        )

        return results

    def _run_gseapy_enrichr_safe(
        self,
        gene_list: list[str],
        gene_set: str,
        background: list[str] | None = None,
        timeout_seconds: float = 120,
    ) -> Any:
        """
        Synchronous GSEApy call with rate limiting (runs in thread pool).

        Rate limits API calls to prevent Enrichr IP blocking.
        CRITICAL: Enrichr blocks concurrent requests from same IP.
        """
        # Rate limiting: Wait if called too recently
        with self._enrichr_lock:
            now = time.time()
            elapsed = now - self._last_enrichr_call

            if elapsed < self._enrichr_min_interval:
                sleep_time = self._enrichr_min_interval - elapsed
                logger.sync_debug(f"Rate limiting: sleeping {sleep_time:.2f}s before Enrichr call")
                time.sleep(sleep_time)

            self._last_enrichr_call = time.time()

        # Call GSEApy (has built-in retry=5)
        try:
            logger.sync_info(
                "Calling GSEApy Enrichr API", gene_count=len(gene_list), gene_set=gene_set
            )

            result = gp.Enrichr(
                gene_list=gene_list,
                gene_sets=gene_set,
                organism="human",
                outdir=None,  # Don't save files
                background=background,  # list -> Enrichr background API, None -> genome
            )
            # ponytail: gseapy 1.3.1 has no timeout option, so bound each HTTP call on its
            # private requests session; revisit if gseapy exposes a timeout or renames _session
            result._session.request = functools.partial(
                result._session.request, timeout=(10, timeout_seconds)
            )
            result.set_organism()
            result.run()
            return result

        except Exception as e:
            logger.sync_error(f"GSEApy API error: {e}")
            return None

    async def _kidney_ontology(self) -> tuple[ClinicalGroupClassifier, frozenset[str]]:
        """Pinned HPO is_a graph and the configured kidney subtree (loaded once)."""
        async with self._ontology_lock:
            if self._ontology is None:
                parents = await asyncio.to_thread(load_hpo_parents, await download_pinned_hp_json())
                ontology = ClinicalGroupClassifier(
                    parents, {}, str(get_source_parameter("HPO", "hpo_release"))
                )
                roots = get_source_parameter("HPO", "kidney_terms", [])
                kidney = frozenset().union(*(ontology.descendants(t) for t in roots))
                self._ontology = (ontology, kidney)
            return self._ontology

    async def _get_hpo_annotations(self, session: Session) -> dict[str, set[str]]:
        """
        Kidney HPO term -> gene symbols, closed under the true-path rule.

        A gene annotated to a term also counts for that term's is_a ancestors inside the
        kidney subtree (e.g. "Renal cortical cyst" genes count for "Renal cyst"); stored
        annotations are not changed. Cached in the network_analysis namespace, which is
        cleared after every source update. Database errors propagate.

        Returns:
            {"HP:0000107": {"WT1", "PAX2", ...}, ...}
        """
        cache = get_cache_service(session)
        cached = await cache.get(HPO_TERM_GENES_CACHE_KEY, namespace="network_analysis")
        if cached is not None:
            return {term: set(genes) for term, genes in cached.items()}

        result = session.execute(
            text("""
            WITH hpo_genes AS (
                SELECT
                    g.approved_symbol,
                    jsonb_array_elements(ga.annotations->'kidney_phenotypes') AS phenotype
                FROM gene_annotations ga
                JOIN genes g ON ga.gene_id = g.id
                WHERE ga.source = 'hpo'
                  AND ga.annotations ? 'kidney_phenotypes'
                  AND jsonb_typeof(ga.annotations->'kidney_phenotypes') = 'array'
            )
            SELECT
                phenotype->>'id' AS hpo_term_id,
                array_agg(DISTINCT approved_symbol) AS gene_symbols
            FROM hpo_genes
            WHERE phenotype->>'id' IS NOT NULL
            GROUP BY phenotype->>'id'
        """)
        )
        direct = {row.hpo_term_id: set(row.gene_symbols) for row in result if row.gene_symbols}
        if not direct:
            return {}

        ontology, kidney = await self._kidney_ontology()
        hpo_to_genes: dict[str, set[str]] = {}
        for term, genes in direct.items():
            # The term itself always counts, even if a newer release moved it out of the subtree
            for target in {term} | (ontology.ancestors(term) & kidney):
                hpo_to_genes.setdefault(target, set()).update(genes)

        logger.sync_info(
            "Loaded HPO annotations from database",
            annotated_terms=len(direct),
            term_count=len(hpo_to_genes),
            total_genes=len(set().union(*direct.values())),
        )
        await cache.set(
            HPO_TERM_GENES_CACHE_KEY,
            {term: sorted(genes) for term, genes in hpo_to_genes.items()},
            namespace="network_analysis",
            ttl=3600,
        )
        return hpo_to_genes

    async def get_cluster_summary(
        self, cluster_genes: list[int], session: Session
    ) -> dict[str, Any]:
        """
        Get summary statistics for a gene cluster.

        Returns:
            {
                "gene_count": int,
                "gene_symbols": List[str],
                "avg_ppi_score": float,
                "avg_evidence_score": float,
                "disease_groups": Dict[str, int]
            }
        """
        genes = session.query(Gene).filter(Gene.id.in_(cluster_genes)).all()

        return {
            "gene_count": len(genes),
            "gene_symbols": sorted([g.approved_symbol for g in genes]),
            # Add more statistics as needed from gene_scores view
        }
