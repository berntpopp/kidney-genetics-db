"""
HPO term operations and hierarchy traversal.
"""

import logging

from app.core.hpo.base import HPOAPIBase
from app.core.hpo.models import HPOTerm

logger = logging.getLogger(__name__)

class HPOTerms(HPOAPIBase):
    """HPO term operations and hierarchy traversal."""

    async def get_term(self, hpo_id: str) -> HPOTerm | None:
        """
        Get detailed information about an HPO term.

        Args:
            hpo_id: HPO term ID (e.g., "HP:0000001")

        Returns:
            HPOTerm object or None if not found
        """
        try:
            response = await self._get(
                f"hp/terms/{hpo_id}",
                cache_key=f"term:{hpo_id}",
                ttl=self.ttl_stable,  # Terms are stable
            )

            if response:
                # Parse the response into our model
                return HPOTerm(
                    id=hpo_id,
                    name=response.get("name", ""),
                    definition=response.get("definition"),
                    synonyms=response.get("synonyms", []),
                    is_obsolete=response.get("isObsolete", False),
                    replaced_by=response.get("replacedBy"),
                    children=[c.get("id") for c in response.get("children", []) if c.get("id")],
                    parents=[p.get("id") for p in response.get("parents", []) if p.get("id")],
                )

        except Exception as e:
            logger.error(f"Failed to get term {hpo_id}: {e}")

        return None

    async def get_descendants(
        self, hpo_id: str, max_depth: int = 10, include_self: bool = True
    ) -> set[str]:
        """
        Get all descendant terms using optimal strategy.

        First tries the descendants endpoint (single call), then falls back
        to recursive children traversal if needed.

        Args:
            hpo_id: HPO term ID
            max_depth: Maximum recursion depth
            include_self: Whether to include the original term

        Returns:
            Set of HPO term IDs including descendants
        """
        descendants = set()
        if include_self:
            descendants.add(hpo_id)

        # Try direct descendants endpoint first (most efficient)
        try:
            logger.info(f"Trying descendants endpoint for {hpo_id}")
            response = await self._get(
                f"hp/terms/{hpo_id}/descendants",
                cache_key=f"descendants:{hpo_id}",
                ttl=self.ttl_stable,
            )

            if isinstance(response, list):
                for item in response:
                    desc_id = item.get("id") if isinstance(item, dict) else item
                    if desc_id:
                        descendants.add(desc_id)

                logger.info(f"Got {len(descendants)} descendants for {hpo_id} from API")
                return descendants

        except Exception as e:
            logger.debug(f"Descendants endpoint not available for {hpo_id}: {e}")

        # Fallback to recursive approach
        logger.info(f"Using recursive approach for {hpo_id}")
        descendants.update(await self._get_descendants_recursive(hpo_id, max_depth))

        logger.info(f"Total descendants for {hpo_id}: {len(descendants)}")
        return descendants

    async def _get_descendants_recursive(self, hpo_id: str, max_depth: int) -> set[str]:
        """
        Recursively collect descendants via children endpoint.

        Args:
            hpo_id: HPO term ID
            max_depth: Maximum recursion depth

        Returns:
            Set of descendant HPO term IDs
        """
        descendants = set()
        visited = set()

        async def collect_children(term_id: str, depth: int):
            """Recursive helper to collect children."""
            if depth >= max_depth or term_id in visited:
                return

            visited.add(term_id)

            try:
                # Get children for this term
                response = await self._get(
                    f"hp/terms/{term_id}/children",
                    cache_key=f"children:{term_id}",
                    ttl=self.ttl_stable,
                )

                if isinstance(response, list):
                    for child in response:
                        child_id = child.get("id") if isinstance(child, dict) else child
                        if child_id and child_id not in descendants:
                            descendants.add(child_id)
                            # Recursively get children of children
                            await collect_children(child_id, depth + 1)

            except Exception as e:
                logger.warning(f"Failed to get children for {term_id}: {e}")

        # Start recursive collection
        await collect_children(hpo_id, 0)

        return descendants

    async def get_children(self, hpo_id: str) -> list[str]:
        """
        Get immediate children of an HPO term.

        Args:
            hpo_id: HPO term ID

        Returns:
            List of child HPO term IDs
        """
        try:
            response = await self._get(
                f"hp/terms/{hpo_id}/children", cache_key=f"children:{hpo_id}", ttl=self.ttl_stable
            )

            if isinstance(response, list):
                children = []
                for child in response:
                    child_id = child.get("id") if isinstance(child, dict) else child
                    if child_id:
                        children.append(child_id)
                return children

        except Exception as e:
            logger.error(f"Failed to get children for {hpo_id}: {e}")

        return []

    async def get_ancestors(self, hpo_id: str) -> list[str]:
        """
        Get ancestor terms (parents up to root).

        Args:
            hpo_id: HPO term ID

        Returns:
            List of ancestor HPO term IDs
        """
        try:
            response = await self._get(
                f"hp/terms/{hpo_id}/parents", cache_key=f"parents:{hpo_id}", ttl=self.ttl_stable
            )

            if isinstance(response, list):
                ancestors = []
                for parent in response:
                    parent_id = parent.get("id") if isinstance(parent, dict) else parent
                    if parent_id:
                        ancestors.append(parent_id)
                return ancestors

        except Exception as e:
            logger.error(f"Failed to get ancestors for {hpo_id}: {e}")

        return []

    async def search_terms(self, query: str, max_results: int = 100) -> list[HPOTerm]:
        """
        Search for HPO terms by text.

        Args:
            query: Search query
            max_results: Maximum number of results

        Returns:
            List of matching HPO terms
        """
        try:
            response = await self._get(
                "hp/search",
                params={"q": query, "max": max_results},
                cache_key=f"term_search:{query}:{max_results}",
                ttl=self.ttl_search,
            )

            terms = []
            if response and "terms" in response:
                for item in response["terms"]:
                    terms.append(
                        HPOTerm(
                            id=item.get("id", ""),
                            name=item.get("name", ""),
                            definition=item.get("definition"),
                            synonyms=item.get("synonyms", []),
                        )
                    )

            return terms

        except Exception as e:
            logger.error(f"Failed to search terms with query '{query}': {e}")
            return []
