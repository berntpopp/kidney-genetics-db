"""
CRUD operations for genes
"""

import re

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.gene import Gene, GeneCuration, GeneEvidence
from app.schemas.gene import GeneCreate, GeneUpdate

logger = get_logger(__name__)

# Identifier-shape patterns used by ``resolve_query``.
_HGNC_RE = re.compile(r"^HGNC:\d+$", re.IGNORECASE)
_ENSG_RE = re.compile(r"^ENSG\d+", re.IGNORECASE)
_DIGITS_RE = re.compile(r"^\d+$")
# UniProt accession formats (https://www.uniprot.org/help/accession_numbers)
_UNIPROT_RE = re.compile(
    r"^[OPQ][0-9][A-Z0-9]{3}[0-9]$|^[A-NR-Z][0-9]([A-Z][A-Z0-9]{2}[0-9]){1,2}$"
)

# Match types returned to the caller, keyed to the branch that matched.
MATCH_HGNC = "hgnc_id"
MATCH_ENSEMBL = "ensembl"
MATCH_NCBI = "ncbi"
MATCH_UNIPROT = "uniprot"
MATCH_SYMBOL = "symbol"
MATCH_ALIAS = "alias"


class CRUDGene:
    """CRUD operations for genes"""

    def get(self, db: Session, gene_id: int) -> Gene | None:
        """Get gene by ID - REFACTORED"""
        from app.core.query_builder import QueryBuilder

        builder = QueryBuilder(db, Gene)
        return builder.filter_by(id=gene_id).first()

    def get_by_symbol(self, db: Session, symbol: str) -> Gene | None:
        """Get gene by symbol - REFACTORED"""
        from app.core.query_builder import QueryBuilder

        # For case-insensitive search, still need raw filter
        builder = QueryBuilder(db, Gene)
        builder.query = builder.query.filter(func.upper(Gene.approved_symbol) == symbol.upper())
        return builder.first()

    def get_gene_by_symbol(self, db: Session, symbol: str) -> Gene | None:
        """Get gene by symbol (alias for get_by_symbol for test compatibility)"""
        return self.get_by_symbol(db, symbol)

    def get_by_hgnc_id(self, db: Session, hgnc_id: str) -> Gene | None:
        """Get gene by HGNC ID - REFACTORED"""
        from app.core.query_builder import QueryBuilder

        builder = QueryBuilder(db, Gene)
        return builder.filter_by(hgnc_id=hgnc_id).first()

    def resolve_query(self, db: Session, query: str) -> "Gene | list[Gene] | None":
        """Resolve a free-text gene identifier to its canonical Gene.

        Branches by identifier shape, trying the most specific identifier
        classes first and falling back to symbol/alias lookups:

        1. ``HGNC:<digits>`` (case-insensitive prefix) -> ``get_by_hgnc_id``
        2. ``ENSG<digits>`` -> ``gene_annotations`` (source ``hgnc``,
           key ``ensembl_gene_id``)
        3. bare digits -> NCBI/Entrez via ``gene_annotations`` (source
           ``hgnc``, key ``ncbi_gene_id``)
        4. UniProt accession -> ``gene_annotations`` (source ``uniprot``,
           key ``accession``)
        5. exact approved symbol (case-insensitive) -> ``get_by_symbol``
        6. fallback alias / prev-symbol / name -> ``genes.aliases`` array
           containment (case-insensitive) and the HGNC-annotation JSONB
           keys ``alias_symbol`` / ``prev_symbol`` / ``name``.

        Returns:
            - a single ``Gene`` for an unambiguous match,
            - a ``list[Gene]`` of distinct candidates when a symbol/alias
              fallback is ambiguous (>1 distinct gene),
            - ``None`` when nothing matches.

        Note:
            ENSG/NCBI/UniProt branches query the ``gene_annotations`` JSONB
            directly (not the ``gene_annotations_summary`` materialized view),
            so resolution reflects the live annotation table without requiring
            a matview refresh.
        """
        if not query or not query.strip():
            return None

        q = query.strip()

        # 1. HGNC identifier (exact, prefix case-insensitive).
        if _HGNC_RE.match(q):
            # Normalise the prefix to canonical "HGNC:" while keeping the
            # numeric portion as stored.
            normalised = "HGNC:" + q.split(":", 1)[1]
            gene = self.get_by_hgnc_id(db, normalised)
            if gene is None and normalised != q:
                gene = self.get_by_hgnc_id(db, q)
            return gene

        # 2. Ensembl gene identifier.
        if _ENSG_RE.match(q):
            return self._resolve_annotation_value(db, "hgnc", "ensembl_gene_id", q)

        # 3. NCBI/Entrez gene identifier (bare digits).
        if _DIGITS_RE.match(q):
            return self._resolve_annotation_value(db, "hgnc", "ncbi_gene_id", q)

        # 4. UniProt accession.
        if _UNIPROT_RE.match(q):
            gene = self._resolve_annotation_value(db, "uniprot", "accession", q)
            if gene is not None:
                return gene
            # Fall through: an accession-shaped token might also be a symbol.

        # 5. Exact approved symbol (case-insensitive).
        gene = self.get_by_symbol(db, q)
        if gene is not None:
            return gene

        # 6. Fallback: alias / prev-symbol / name.
        candidates = self._resolve_alias(db, q)
        if not candidates:
            return None
        if len(candidates) == 1:
            return candidates[0]
        return candidates

    def _resolve_annotation_value(
        self, db: Session, source: str, key: str, value: str
    ) -> Gene | None:
        """Find the Gene whose ``gene_annotations`` JSONB (for ``source``)
        has ``annotations->>key == value``."""
        row = db.execute(
            text(
                """
                SELECT gene_id
                FROM gene_annotations
                WHERE source = :source
                  AND annotations->>:key = :value
                LIMIT 1
                """
            ),
            {"source": source, "key": key, "value": value},
        ).first()
        if row is None:
            return None
        return self.get(db, int(row[0]))

    def _resolve_alias(self, db: Session, query: str) -> list[Gene]:
        """Return distinct genes matching ``query`` as an alias, previous
        symbol, or HGNC name (case-insensitive).

        Sources, in order, deduplicated by gene id:
          - ``genes.aliases`` array containment (case-insensitive)
          - HGNC-annotation JSONB arrays ``alias_symbol`` / ``prev_symbol``
          - HGNC-annotation JSONB scalar ``name``
        """
        lowered = query.lower()
        gene_ids: list[int] = []
        seen: set[int] = set()

        # genes.aliases array containment (case-insensitive).
        alias_rows = db.execute(
            text(
                """
                SELECT id
                FROM genes
                WHERE EXISTS (
                    SELECT 1 FROM unnest(aliases) AS a
                    WHERE lower(a) = :lowered
                )
                """
            ),
            {"lowered": lowered},
        ).fetchall()
        for row in alias_rows:
            gid = int(row[0])
            if gid not in seen:
                seen.add(gid)
                gene_ids.append(gid)

        # HGNC-annotation JSONB: alias_symbol / prev_symbol arrays + name scalar.
        hgnc_rows = db.execute(
            text(
                """
                SELECT gene_id
                FROM gene_annotations
                WHERE source = 'hgnc'
                  AND (
                    EXISTS (
                        SELECT 1 FROM jsonb_array_elements_text(
                            CASE WHEN jsonb_typeof(annotations->'alias_symbol') = 'array'
                                 THEN annotations->'alias_symbol' ELSE '[]'::jsonb END
                        ) AS al WHERE lower(al) = :lowered
                    )
                    OR EXISTS (
                        SELECT 1 FROM jsonb_array_elements_text(
                            CASE WHEN jsonb_typeof(annotations->'prev_symbol') = 'array'
                                 THEN annotations->'prev_symbol' ELSE '[]'::jsonb END
                        ) AS pv WHERE lower(pv) = :lowered
                    )
                    OR lower(annotations->>'name') = :lowered
                  )
                """
            ),
            {"lowered": lowered},
        ).fetchall()
        for row in hgnc_rows:
            gid = int(row[0])
            if gid not in seen:
                seen.add(gid)
                gene_ids.append(gid)

        if not gene_ids:
            return []

        genes = db.query(Gene).filter(Gene.id.in_(gene_ids)).all()
        # Preserve first-seen ordering for deterministic single-result returns.
        by_id = {int(g.id): g for g in genes}
        return [by_id[gid] for gid in gene_ids if gid in by_id]

    def count(self, db: Session, search: str | None = None, min_score: float | None = None) -> int:
        """Count genes with filtering using gene_scores view for percentage scores - REFACTORED"""
        from app.core.query_builder import QueryBuilder

        if min_score is not None:
            # Use QueryBuilder for view-based counting
            builder = QueryBuilder(db, Gene)

            # Join with gene_scores view
            builder = builder.join_view("gene_scores", "gene_scores.gene_id = genes.id")

            # Add search filter
            if search:
                builder = builder.search(search, "approved_symbol", "hgnc_id")

            # Add score filter
            if min_score is not None:
                builder = builder.filter_range("percentage_score", min_value=min_score)

            # For now, still use raw SQL for COUNT queries with views
            query = """
                SELECT COUNT(DISTINCT gs.gene_id)
                FROM gene_scores gs
                JOIN genes g ON gs.gene_id = g.id
                WHERE 1=1
            """
            params: dict[str, str | float] = {}

            if search:
                query += " AND (gs.approved_symbol ILIKE :search OR g.hgnc_id ILIKE :search)"
                params["search"] = f"%{search}%"

            if min_score is not None:
                query += " AND gs.percentage_score >= :min_score"
                params["min_score"] = min_score

            result = db.execute(text(query), params).scalar()
            return result if result is not None else 0
        else:
            # Use QueryBuilder for regular counting
            builder = QueryBuilder(db, Gene)

            if search:
                builder = builder.search(search, "approved_symbol", "hgnc_id")

            # Execute count query
            query = builder.query
            result = query.count()
            return result if result is not None else 0

    def create(self, db: Session, obj_in: GeneCreate) -> Gene:
        """Create new gene"""
        db_obj = Gene(
            hgnc_id=obj_in.hgnc_id, approved_symbol=obj_in.approved_symbol, aliases=obj_in.aliases
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, db_obj: Gene, obj_in: GeneUpdate) -> Gene:
        """Update gene"""
        update_data = obj_in.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_evidence(self, db: Session, gene_id: int) -> list[GeneEvidence]:
        """Get all evidence for a gene - REFACTORED"""
        from app.core.query_builder import QueryBuilder

        builder = QueryBuilder(db, GeneEvidence)
        return builder.filter_by(gene_id=gene_id).all()

    def get_curation(self, db: Session, gene_id: int) -> GeneCuration | None:
        """Get curation data for a gene - REFACTORED"""
        from app.core.query_builder import QueryBuilder

        builder = QueryBuilder(db, GeneCuration)
        return builder.filter_by(gene_id=gene_id).first()

    def get_gene_score(self, db: Session, gene_id: int) -> dict | None:
        """Get gene scores from the gene_scores view"""
        result = db.execute(
            text(
                """
                SELECT gene_id, approved_symbol, source_count, evidence_count,
                       raw_score, percentage_score, total_active_sources, source_scores
                FROM gene_scores
                WHERE gene_id = :gene_id
            """
            ),
            {"gene_id": gene_id},
        ).first()

        if result:
            return {
                "gene_id": result[0],
                "approved_symbol": result[1],
                "source_count": result[2],
                "evidence_count": result[3],
                "raw_score": result[4],
                "percentage_score": result[5],
                "total_active_sources": result[6],
                "source_percentiles": result[7],
            }
        return None

    def create_pipeline_run(self, db: Session) -> int:
        """Create a new pipeline run record and return its ID (for test compatibility)"""
        # This is a simplified implementation for test compatibility
        from datetime import datetime, timezone

        from app.models.gene import PipelineRun

        run = PipelineRun(status="running", started_at=datetime.now(timezone.utc), stats={})
        db.add(run)
        db.commit()
        db.refresh(run)
        return int(run.id)

    def create_or_update_gene(self, db: Session, hgnc_id: str, symbol: str) -> int:
        """Create or update a gene and return its ID (for test compatibility)"""
        # Check if gene already exists
        existing = self.get_by_symbol(db, symbol)
        if existing:
            return int(existing.id)

        # Create new gene
        from app.schemas.gene import GeneCreate

        gene_data = GeneCreate(hgnc_id=hgnc_id, approved_symbol=symbol, aliases=[])
        new_gene = self.create(db, gene_data)
        return int(new_gene.id)

    def create_gene_evidence(
        self, db: Session, gene_id: int, source_name: str, evidence_data: dict
    ) -> int:
        """Create gene evidence record and return its ID (for test compatibility)"""
        from datetime import datetime, timezone

        from app.models.gene import GeneEvidence

        evidence = GeneEvidence(
            gene_id=gene_id,
            source_name=source_name,
            evidence_data=evidence_data,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(evidence)
        db.commit()
        db.refresh(evidence)
        return int(evidence.id)


# Create singleton instance
gene_crud = CRUDGene()
