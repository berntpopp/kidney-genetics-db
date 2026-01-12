"""
STRING-DB Protein-Protein Interaction annotation source.

Implements PPI scoring using STRING database physical interactions,
weighted by partner kidney evidence scores and normalized to avoid hub bias.
"""

import math
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.models.gene import Gene
from app.pipeline.sources.annotations.base import BaseAnnotationSource

logger = get_logger(__name__)


class StringPPIAnnotationSource(BaseAnnotationSource):
    """
    STRING-DB Protein-Protein Interaction annotation source.

    Calculates PPI scores based on physical interaction confidence
    weighted by partner kidney evidence scores with hub bias correction.

    Algorithm:
    PPI_score(gene) = Σ(STRING_score/1000 × partner_kidney_evidence) / sqrt(degree)
    """

    source_name = "string_ppi"
    display_name = "STRING Protein Interactions"
    version = settings.STRING_VERSION

    # Configuration from settings
    cache_ttl_days = settings.STRING_CACHE_TTL_DAYS
    min_string_score = settings.STRING_MIN_SCORE
    max_interactions_stored = settings.STRING_MAX_INTERACTIONS_STORED

    # Data file paths
    data_dir = Path(settings.STRING_DATA_DIR)
    protein_info_file = "9606.protein.info.v12.0.txt"
    physical_links_file = "9606.protein.physical.links.v12.0.txt"

    # Class-level flag for one-time warnings
    _percentile_warning_shown = False

    def __init__(self, session: Session) -> None:
        """Initialize STRING PPI annotation source."""
        super().__init__(session)

        # Cache for protein mappings and interaction data
        self._protein_to_gene: dict[str, str] | None = None
        self._gene_to_protein: dict[str, list[str]] | None = None
        self._interactions: pd.DataFrame | None = None
        self._kidney_genes: set[str] | None = None
        self._gene_evidence_scores: dict[str, float] | None = None

    async def _load_data(self) -> None:
        """Load and prepare STRING data files."""
        if self._protein_to_gene is not None:
            return  # Already loaded

        logger.sync_info("Loading STRING data files", version=self.version)

        # Load protein info file
        protein_info_path = self.data_dir / self.protein_info_file
        if not protein_info_path.exists():
            # Try gzipped version
            gz_path = protein_info_path.with_suffix(".txt.gz")
            if gz_path.exists():
                logger.sync_info("Loading gzipped protein info file")
                df_info = pd.read_csv(gz_path, sep="\t", compression="gzip")
            else:
                raise FileNotFoundError(f"STRING protein info file not found: {protein_info_path}")
        else:
            df_info = pd.read_csv(protein_info_path, sep="\t")

        # Create bidirectional mappings
        df_info["protein_id"] = df_info["#string_protein_id"].str.replace("9606.", "")
        self._protein_to_gene = dict(
            zip(df_info["protein_id"], df_info["preferred_name"], strict=False)
        )
        self._gene_to_protein = {}
        for protein, gene in self._protein_to_gene.items():
            if gene not in self._gene_to_protein:
                self._gene_to_protein[gene] = []
            self._gene_to_protein[gene].append(protein)

        logger.sync_info(f"Loaded {len(self._protein_to_gene)} protein mappings")

        # Load physical links file
        physical_links_path = self.data_dir / self.physical_links_file
        if not physical_links_path.exists():
            # Try gzipped version
            gz_path = physical_links_path.with_suffix(".txt.gz")
            if gz_path.exists():
                logger.sync_info("Loading gzipped physical links file")
                df_links = pd.read_csv(gz_path, sep=" ", compression="gzip")
            else:
                raise FileNotFoundError(
                    f"STRING physical links file not found: {physical_links_path}"
                )
        else:
            df_links = pd.read_csv(physical_links_path, sep=" ")

        # Clean protein IDs
        df_links["protein1"] = df_links["protein1"].str.replace("9606.", "")
        df_links["protein2"] = df_links["protein2"].str.replace("9606.", "")

        # Filter by minimum score
        df_links = df_links[df_links["combined_score"] >= self.min_string_score]

        # Map proteins to gene symbols
        df_links["gene1"] = df_links["protein1"].map(self._protein_to_gene)
        df_links["gene2"] = df_links["protein2"].map(self._protein_to_gene)

        # Remove rows where mapping failed
        df_links = df_links.dropna(subset=["gene1", "gene2"])

        self._interactions = df_links
        logger.sync_info(f"Loaded {len(self._interactions)} interactions above threshold")

    async def _load_kidney_genes(self) -> None:
        """Load kidney genes and their evidence scores from database."""
        if self._kidney_genes is not None:
            return

        from sqlalchemy import text

        result = self.session.execute(
            text("""
            SELECT approved_symbol, percentage_score
            FROM gene_scores
            WHERE percentage_score > 0
        """)
        )

        kidney_genes = []
        evidence_scores = {}

        for row in result:
            symbol = row[0]
            score = row[1]

            kidney_genes.append(symbol)
            evidence_scores[symbol] = float(score)

        self._kidney_genes = set(kidney_genes)
        self._gene_evidence_scores = evidence_scores

        logger.sync_info(f"Loaded {len(self._kidney_genes)} kidney genes with evidence scores")

    async def fetch_annotation(self, gene: Gene) -> dict[str, Any] | None:
        """
        Fetch STRING PPI annotation for a single gene.

        Note: This method is not efficient for individual genes.
        Use fetch_batch for better performance.
        """
        # Load data if not already loaded
        await self._load_data()
        await self._load_kidney_genes()

        # Process single gene
        batch_results = await self.fetch_batch([gene])
        return batch_results.get(gene.id)

    async def fetch_batch(self, genes: list[Gene]) -> dict[int, dict[str, Any]]:
        """
        Fetch annotations for multiple genes.

        Now uses global percentiles instead of batch-relative calculation.
        Gracefully falls back to None if percentiles unavailable.
        """
        # Load data if not already loaded
        await self._load_data()
        await self._load_kidney_genes()

        # After loading, these are guaranteed to be set
        if (
            self._kidney_genes is None
            or self._interactions is None
            or self._gene_evidence_scores is None
        ):
            raise RuntimeError("Data should be loaded at this point")

        logger.sync_info(f"Processing {len(genes)} genes for PPI scores")

        results: dict[int, dict[str, Any]] = {}
        raw_scores: dict[int, float] = {}

        for gene in genes:
            gene_symbol = gene.approved_symbol

            # Skip if not a kidney gene
            if gene_symbol not in self._kidney_genes:
                continue

            # Get all interactions for this gene
            gene_interactions = self._interactions[
                (self._interactions["gene1"] == gene_symbol)
                | (self._interactions["gene2"] == gene_symbol)
            ].copy()

            if len(gene_interactions) == 0:
                # No interactions found
                raw_scores[gene.id] = 0
                results[gene.id] = self._format_annotation(gene_symbol, 0, 0, 0, [])
                continue

            # Identify partners
            gene_interactions["partner"] = gene_interactions.apply(
                lambda row, gs=gene_symbol: row["gene2"] if row["gene1"] == gs else row["gene1"],
                axis=1,
            )

            # Filter for kidney gene partners only
            gene_interactions = gene_interactions[
                gene_interactions["partner"].isin(self._kidney_genes)
            ]

            if len(gene_interactions) == 0:
                # No kidney gene interactions
                raw_scores[gene.id] = 0
                results[gene.id] = self._format_annotation(gene_symbol, 0, 0, 0, [])
                continue

            # Aggregate interactions by partner gene (handling multiple isoforms)
            partner_interactions: dict[str, dict[str, Any]] = {}

            for _, interaction in gene_interactions.iterrows():
                partner = interaction["partner"]
                string_score = interaction["combined_score"]
                # _gene_evidence_scores is guaranteed to be loaded at this point (checked above)
                partner_evidence = self._gene_evidence_scores.get(partner, 0)

                # If we already have this partner, keep the highest scoring interaction
                if partner in partner_interactions:
                    if string_score > partner_interactions[partner]["string_score"]:
                        partner_interactions[partner] = {
                            "partner_symbol": partner,
                            "string_score": string_score,
                            "partner_evidence": round(partner_evidence, 1),
                            "weighted_score": round((string_score / 1000) * partner_evidence, 2),
                        }
                else:
                    partner_interactions[partner] = {
                        "partner_symbol": partner,
                        "string_score": string_score,
                        "partner_evidence": round(partner_evidence, 1),
                        "weighted_score": round((string_score / 1000) * partner_evidence, 2),
                    }

            # Convert to list and calculate total weighted sum
            interaction_details = list(partner_interactions.values())
            weighted_sum = sum(i["weighted_score"] for i in interaction_details)

            # Calculate degree (number of UNIQUE kidney gene partners)
            degree = len(partner_interactions)

            # Apply hub bias correction
            if degree > 0:
                raw_score = weighted_sum / math.sqrt(degree)
            else:
                raw_score = 0

            raw_scores[gene.id] = raw_score

            # Sort interactions by weighted score and keep top N
            interaction_details.sort(key=lambda x: x["weighted_score"], reverse=True)
            top_interactions = interaction_details[: self.max_interactions_stored]

            # Create summary statistics
            summary = {
                "total_interactions": degree,
                "raw_sum": round(sum(i["string_score"] for i in interaction_details), 2),
                "weighted_sum": round(weighted_sum, 2),
                "avg_string_score": round(
                    sum(i["string_score"] for i in interaction_details) / degree
                    if degree > 0
                    else 0,
                    2,
                ),
                "strong_interactions": len(
                    [i for i in interaction_details if i["string_score"] > 800]
                ),
            }

            # Store preliminary results (will add percentile after getting global values)
            results[gene.id] = {
                "ppi_score": round(raw_score, 2),
                "ppi_degree": degree,
                "interactions": top_interactions,
                "summary": summary,
            }

        # NEW: Get global percentiles instead of calculating batch-relative
        if raw_scores:
            # Try to get global percentiles with proper error handling
            global_percentiles = None

            try:
                from app.core.percentile_service import PercentileService

                percentile_service = PercentileService(self.session)
                # Only get cached percentiles - don't trigger recalculation
                global_percentiles = await percentile_service.get_cached_percentiles_only(
                    "string_ppi"
                )

                if not global_percentiles:
                    # Try one calculation attempt (non-blocking)
                    global_percentiles = await percentile_service.calculate_global_percentiles(
                        "string_ppi",
                        "ppi_score",
                        force=False,  # Respect frequency limiting
                    )

            except Exception as e:
                # Log but don't fail - graceful degradation
                logger.sync_debug(f"Percentile service unavailable: {e}")
                global_percentiles = None

            # Apply global percentiles with fallback
            for gene_id in results:
                if global_percentiles and gene_id in global_percentiles:
                    results[gene_id]["ppi_percentile"] = global_percentiles[gene_id]
                else:
                    # CRITICAL: Return None, not 1.0 (misleading 100th percentile)
                    results[gene_id]["ppi_percentile"] = None

                    # Only warn once per batch to avoid log spam
                    if not StringPPIAnnotationSource._percentile_warning_shown:
                        logger.sync_warning(
                            "No global percentiles available - returning None. "
                            "Run percentile calculation after all genes processed."
                        )
                        StringPPIAnnotationSource._percentile_warning_shown = True

        logger.sync_info(
            f"Calculated PPI scores for {len(results)} genes",
            zero_score_genes=len([1 for s in raw_scores.values() if s == 0]),
        )

        return results

    def _format_annotation(
        self, gene_symbol: str, score: float, percentile: float, degree: int, interactions: list
    ) -> dict[str, Any]:
        """Format annotation data for storage."""
        return {
            "ppi_score": round(score, 2),
            "ppi_percentile": None
            if percentile == 0
            else round(percentile, 3),  # Use None for no data
            "ppi_degree": degree,
            "interactions": interactions,
            "summary": {
                "total_interactions": degree,
                "raw_sum": 0,
                "weighted_sum": 0,
                "avg_string_score": 0,
                "strong_interactions": 0,
            },
        }

    def get_default_config(self) -> dict[str, Any]:
        """Get default configuration for this source."""
        config = super().get_default_config()
        config.update(
            {
                "min_string_score": self.min_string_score,
                "max_interactions_stored": self.max_interactions_stored,
                "data_version": self.version,
                "data_dir": str(self.data_dir),
            }
        )
        return config

    async def validate_data_files(self) -> bool:
        """Validate that required data files exist."""
        protein_info_path = self.data_dir / self.protein_info_file
        physical_links_path = self.data_dir / self.physical_links_file

        # Check for either regular or gzipped versions
        protein_info_exists = (
            protein_info_path.exists() or protein_info_path.with_suffix(".txt.gz").exists()
        )

        physical_links_exists = (
            physical_links_path.exists() or physical_links_path.with_suffix(".txt.gz").exists()
        )

        if not protein_info_exists:
            logger.sync_error(f"Protein info file not found: {protein_info_path}")
            return False

        if not physical_links_exists:
            logger.sync_error(f"Physical links file not found: {physical_links_path}")
            return False

        return True

    async def recalculate_global_percentiles(self) -> None:
        """
        Trigger global percentile recalculation after batch updates.
        Should be called after annotation pipeline runs.
        """
        from app.core.percentile_service import PercentileService

        try:
            service = PercentileService(self.session)
            percentiles = await service.calculate_global_percentiles(
                "string_ppi",
                "ppi_score",
                force=True,  # Force recalculation after batch
            )

            if percentiles:
                logger.sync_info(
                    f"Updated global STRING PPI percentiles for {len(percentiles)} genes"
                )
            else:
                logger.sync_warning("No percentiles calculated - may need to check view")

        except Exception as e:
            logger.sync_error(f"Failed to recalculate global percentiles: {e}")
