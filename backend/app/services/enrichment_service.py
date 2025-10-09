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
import threading
import time
from typing import Any

import numpy as np
from scipy.stats import fisher_exact
from sqlalchemy import text
from sqlalchemy.orm import Session
from statsmodels.stats.multitest import fdrcorrection

from app.core.database import get_thread_pool_executor
from app.core.hpo.terms import HPOTerms
from app.core.logging import get_logger
from app.models.gene import Gene

logger = get_logger(__name__)

# Lazy import of gseapy (not always needed)
try:
    import gseapy as gp

    GSEAPY_AVAILABLE = True
except ImportError:
    GSEAPY_AVAILABLE = False
    logger.sync_warning("GSEApy not available - GO/KEGG enrichment disabled")


class EnrichmentService:
    """
    Service for functional enrichment analysis of gene clusters.

    Features:
    - HPO term enrichment (Fisher's exact test)
    - GO/KEGG enrichment (via GSEApy)
    - FDR correction (Benjamini-Hochberg)
    - Rate limiting for Enrichr API
    """

    def __init__(self):
        """
        Initialize enrichment service.

        IMPORTANT: Session NOT stored - passed per-call for thread safety.
        """
        self.hpo_client = HPOTerms()
        self._executor = get_thread_pool_executor()

        # Rate limiting for GSEApy/Enrichr API (prevents IP blocking)
        self._last_enrichr_call = 0
        self._enrichr_min_interval = 2.0  # 2 seconds between calls
        self._enrichr_lock = threading.Lock()

    async def enrich_hpo_terms(
        self,
        cluster_genes: list[int],
        session: Session,
        background_genes: list[int] | None = None,
        fdr_threshold: float = 0.05,
    ) -> list[dict[str, Any]]:
        """
        Perform HPO term enrichment using Fisher's exact test.

        Args:
            cluster_genes: Gene IDs in cluster to test for enrichment
            session: Database session (passed per-call)
            background_genes: Background gene set (default: all genes in DB)
            fdr_threshold: FDR cutoff for significance (default: 0.05)

        Returns:
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
        # Get gene symbols for cluster
        cluster_gene_objs = session.query(Gene).filter(Gene.id.in_(cluster_genes)).all()
        cluster_symbols = {g.approved_symbol for g in cluster_gene_objs}

        if not cluster_symbols:
            await logger.warning("No valid genes found in cluster")
            return []

        # Get HPO annotations from database (JSONB extraction)
        hpo_term_to_genes = await self._get_hpo_annotations(session)

        if not hpo_term_to_genes:
            await logger.warning("No HPO annotations found in database")
            return []

        # CRITICAL FIX: Background must be only genes WITH HPO annotations
        # Get all unique genes that have ANY HPO annotation
        all_annotated_genes = set()
        for term_genes in hpo_term_to_genes.values():
            all_annotated_genes.update(term_genes)

        await logger.info(
            "HPO enrichment background",
            cluster_size=len(cluster_symbols),
            background_size=len(all_annotated_genes),
            hpo_terms=len(hpo_term_to_genes),
        )

        # Perform Fisher's exact test for each HPO term
        results = []
        p_values = []

        total_background = len(all_annotated_genes)

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

            # Fisher's exact test (one-tailed, testing for over-representation)
            odds_ratio, p_value = fisher_exact([[a, b], [c, d]], alternative="greater")

            p_values.append(p_value)

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

        if not results:
            await logger.info("No HPO terms enriched in cluster")
            return []

        # FDR correction (Benjamini-Hochberg)
        _, fdr_values = fdrcorrection([r["p_value"] for r in results])

        for i, result in enumerate(results):
            result["fdr"] = float(fdr_values[i])
            result["enrichment_score"] = -np.log10(result["fdr"]) if result["fdr"] > 0 else 100.0

        # Get term names from HPO API
        for result in results:
            try:
                term = await self.hpo_client.get_term(result["term_id"])
                result["term_name"] = term.name if term else result["term_id"]
            except Exception as e:
                await logger.debug(f"Failed to get HPO term name: {e}", term_id=result["term_id"])
                result["term_name"] = result["term_id"]

        # Filter by FDR and sort
        results = [r for r in results if r["fdr"] < fdr_threshold]
        results.sort(key=lambda x: x["fdr"])

        await logger.info(
            "HPO enrichment complete",
            significant_terms=len(results),
            cluster_size=len(cluster_symbols),
            fdr_threshold=fdr_threshold,
        )

        return results

    async def enrich_go_terms(
        self,
        cluster_genes: list[int],
        session: Session,
        gene_set: str = "GO_Biological_Process_2023",
        fdr_threshold: float = 0.05,
        timeout_seconds: int = 120,
    ) -> list[dict[str, Any]]:
        """
        Perform GO/KEGG enrichment using GSEApy with timeout and rate limiting.

        Args:
            cluster_genes: Gene IDs in cluster
            session: Database session
            gene_set: GSEApy gene set name (GO_Biological_Process_2023, KEGG_2021_Human, etc.)
            fdr_threshold: FDR cutoff
            timeout_seconds: Maximum time to wait for Enrichr API (default: 120s)

        Returns:
            Same format as enrich_hpo_terms
        """
        if not GSEAPY_AVAILABLE:
            await logger.error("GSEApy not installed - cannot perform GO enrichment")
            return []

        # Get gene symbols
        genes = session.query(Gene).filter(Gene.id.in_(cluster_genes)).all()
        gene_symbols = [g.approved_symbol for g in genes]

        if not gene_symbols:
            await logger.warning("No valid genes found in cluster")
            return []

        # Run GSEApy with timeout and rate limiting
        loop = asyncio.get_event_loop()

        try:
            enr_result = await asyncio.wait_for(
                loop.run_in_executor(
                    self._executor, self._run_gseapy_enrichr_safe, gene_symbols, gene_set
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

        if enr_result.results.empty:
            await logger.info("No GO terms enriched in cluster")
            return []

        for _, row in enr_result.results.iterrows():
            if row["Adjusted P-value"] > fdr_threshold:
                continue

            gene_list = row["Genes"].split(";") if isinstance(row["Genes"], str) else []

            results.append(
                {
                    "term_id": row["Term"],
                    "term_name": row["Term"],  # GSEApy uses same for both
                    "p_value": float(row["P-value"]),
                    "fdr": float(row["Adjusted P-value"]),
                    "gene_count": len(gene_list),
                    "cluster_size": len(gene_symbols),
                    "background_count": None,  # Not provided by Enrichr
                    "genes": gene_list,
                    "enrichment_score": -np.log10(row["Adjusted P-value"])
                    if row["Adjusted P-value"] > 0
                    else 100.0,
                    "odds_ratio": float(row.get("Odds Ratio", 0)),
                    "combined_score": float(row["Combined Score"]),  # Enrichr-specific
                }
            )

        await logger.info(
            "GO enrichment complete",
            significant_terms=len(results),
            gene_set=gene_set,
            cluster_size=len(gene_symbols),
        )

        return results

    def _run_gseapy_enrichr_safe(self, gene_list: list[str], gene_set: str):
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

            result = gp.enrichr(
                gene_list=gene_list,
                gene_sets=gene_set,
                organism="human",
                outdir=None,  # Don't save files
            )

            return result

        except Exception as e:
            logger.sync_error(f"GSEApy API error: {e}")
            return None

    async def _get_hpo_annotations(
        self, session: Session, use_kidney_only: bool = True
    ) -> dict[str, set]:
        """
        Get HPO term → genes mapping from database using JSONB operators.

        Extracts HPO terms from gene_annotations.annotations JSONB column.

        Args:
            session: Database session
            use_kidney_only: If True, use kidney_phenotypes; if False, use all phenotypes

        Returns:
            {"HP:0000107": {"WT1", "PAX2", ...}, ...}
        """
        try:
            # Choose which phenotype field to use
            phenotype_field = "kidney_phenotypes" if use_kidney_only else "phenotypes"

            # Use PostgreSQL JSONB operators to extract phenotypes
            # Note: phenotype_field must be string-formatted (not parameterized) for JSONB key access
            result = session.execute(
                text(f"""
                WITH hpo_genes AS (
                    SELECT
                        g.approved_symbol,
                        jsonb_array_elements(ga.annotations->'{phenotype_field}') AS phenotype
                    FROM gene_annotations ga
                    JOIN genes g ON ga.gene_id = g.id
                    WHERE ga.source = 'hpo'
                      AND ga.annotations ? '{phenotype_field}'
                      AND jsonb_typeof(ga.annotations->'{phenotype_field}') = 'array'
                )
                SELECT
                    phenotype->>'id' AS hpo_term_id,
                    array_agg(DISTINCT approved_symbol) AS gene_symbols
                FROM hpo_genes
                WHERE phenotype->>'id' IS NOT NULL
                GROUP BY phenotype->>'id'
            """)
            )

            hpo_to_genes = {}
            for row in result:
                if row.hpo_term_id and row.gene_symbols:
                    hpo_to_genes[row.hpo_term_id] = set(row.gene_symbols)

            logger.sync_info(
                "Loaded HPO annotations from database",
                phenotype_field=phenotype_field,
                term_count=len(hpo_to_genes),
                total_genes=sum(len(genes) for genes in hpo_to_genes.values()),
            )

            return hpo_to_genes

        except Exception as e:
            logger.sync_error(f"Failed to load HPO annotations from database: {e}")
            return {}

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
