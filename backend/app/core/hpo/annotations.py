"""
HPO phenotype annotation operations for genes and diseases.
"""

import asyncio
from typing import Any

from app.core.hpo.base import HPOAPIBase
from app.core.hpo.models import (
    Disease,
    DiseaseAnnotations,
    Gene,
    InheritancePattern,
    TermAnnotations,
)
from app.core.logging import get_logger

logger = get_logger(__name__)


class HPOAnnotations(HPOAPIBase):
    """Phenotype annotation operations for terms, genes, and diseases."""

    async def get_term_annotations(self, hpo_id: str) -> TermAnnotations | None:
        """
        Get all annotations for an HPO term.

        Returns genes, diseases, and medical actions associated with the term.

        Args:
            hpo_id: HPO term ID (e.g., "HP:0000113")

        Returns:
            TermAnnotations object or None if not found
        """
        try:
            response = await self._get(
                f"network/annotation/{hpo_id}",
                cache_key=f"annotations:{hpo_id}",
                ttl=self.ttl_annotations,
            )

            if response:
                return TermAnnotations(**response)

        except Exception as e:
            logger.sync_error("Failed to get annotations for HPO term", hpo_id=hpo_id, error=str(e))

        return None

    async def get_disease_annotations(self, disease_id: str) -> DiseaseAnnotations | None:
        """
        Get annotations for a disease (e.g., OMIM:123456, ORPHA:789).

        Includes phenotypes, genes, and inheritance patterns.

        Args:
            disease_id: Disease ID (OMIM:XXXXX or ORPHA:XXXXX)

        Returns:
            DiseaseAnnotations object or None if not found
        """
        try:
            response = await self._get(
                f"network/annotation/{disease_id}",
                cache_key=f"disease:{disease_id}",
                ttl=self.ttl_annotations,
            )

            if response:
                return DiseaseAnnotations(**response)

        except Exception as e:
            logger.sync_error(
                "Failed to get disease annotations", disease_id=disease_id, error=str(e)
            )

        return None

    async def get_disease_inheritance(self, disease_id: str) -> list[InheritancePattern]:
        """
        Get inheritance patterns for a disease.

        Args:
            disease_id: Disease ID (OMIM:XXXXX or ORPHA:XXXXX)

        Returns:
            List of inheritance patterns
        """
        annotations = await self.get_disease_annotations(disease_id)
        if annotations:
            return annotations.get_inheritance_patterns()
        return []

    async def batch_get_annotations(
        self, hpo_ids: list[str], batch_size: int = 10, delay: float = 0.1
    ) -> dict[str, TermAnnotations]:
        """
        Efficiently fetch annotations for multiple HPO terms.

        Uses concurrent requests with batching to avoid overwhelming the API.

        Args:
            hpo_ids: List of HPO term IDs
            batch_size: Number of concurrent requests per batch
            delay: Delay between batches in seconds

        Returns:
            Dictionary mapping HPO IDs to their annotations
        """
        results = {}
        total = len(hpo_ids)

        for i in range(0, total, batch_size):
            batch = hpo_ids[i : i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (total + batch_size - 1) // batch_size

            logger.sync_info(
                "Processing batch of HPO terms",
                batch_num=batch_num,
                total_batches=total_batches,
                batch_size=len(batch),
            )

            # Create tasks for this batch
            tasks = [self.get_term_annotations(hpo_id) for hpo_id in batch]

            # Execute batch concurrently
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            for hpo_id, result in zip(batch, batch_results, strict=False):
                if isinstance(result, Exception):
                    logger.sync_warning(
                        "Failed to get annotations for HPO term", hpo_id=hpo_id, error=str(result)
                    )
                elif result is not None:
                    results[hpo_id] = result

            # Add delay between batches to be respectful to the API
            if i + batch_size < total:
                await asyncio.sleep(delay)

        logger.sync_info(
            "Successfully fetched annotations for terms",
            success_count=len(results),
            total_count=total,
        )
        return results

    async def get_genes_for_term(self, hpo_id: str) -> list[Gene]:
        """
        Get all genes associated with an HPO term.

        Args:
            hpo_id: HPO term ID

        Returns:
            List of genes
        """
        annotations = await self.get_term_annotations(hpo_id)
        if annotations:
            return annotations.genes
        return []

    async def get_diseases_for_term(self, hpo_id: str) -> list[Disease]:
        """
        Get all diseases associated with an HPO term.

        Args:
            hpo_id: HPO term ID

        Returns:
            List of diseases
        """
        annotations = await self.get_term_annotations(hpo_id)
        if annotations:
            return annotations.diseases
        return []

    async def get_genes_with_inheritance(
        self, hpo_id: str, include_disease_details: bool = True
    ) -> dict[str, dict[str, Any]]:
        """
        Get genes for an HPO term with inheritance information from associated diseases.

        Args:
            hpo_id: HPO term ID
            include_disease_details: Whether to fetch detailed disease information

        Returns:
            Dictionary mapping gene symbols to their data including inheritance
        """
        genes_data = {}

        # Get term annotations
        annotations = await self.get_term_annotations(hpo_id)
        if not annotations:
            return genes_data

        # Process genes
        for gene in annotations.genes:
            gene_symbol = gene.name
            if gene_symbol not in genes_data:
                genes_data[gene_symbol] = {
                    "entrez_id": gene.entrez_id,
                    "hpo_terms": {hpo_id},
                    "diseases": set(),
                    "inheritance_patterns": set(),
                }
            else:
                genes_data[gene_symbol]["hpo_terms"].add(hpo_id)

        # Process diseases for inheritance if requested
        if include_disease_details:
            for disease in annotations.diseases:
                # Only process OMIM diseases for now
                if disease.id.startswith("OMIM:"):
                    disease_details = await self.get_disease_annotations(disease.id)
                    if disease_details:
                        # Get inheritance patterns
                        inheritance = disease_details.get_inheritance_patterns()

                        # Link to genes
                        for gene in disease_details.genes:
                            gene_symbol = gene.name
                            if gene_symbol in genes_data:
                                genes_data[gene_symbol]["diseases"].add(disease.id)
                                for pattern in inheritance:
                                    genes_data[gene_symbol]["inheritance_patterns"].add(
                                        pattern.name
                                    )

        # Convert sets to lists for JSON serialization
        for gene_data in genes_data.values():
            gene_data["hpo_terms"] = list(gene_data["hpo_terms"])
            gene_data["diseases"] = list(gene_data["diseases"])
            gene_data["inheritance_patterns"] = list(gene_data["inheritance_patterns"])

        return genes_data
