"""
CRUD operations for genes
"""

from sqlalchemy import func, or_, text
from sqlalchemy.orm import Session

from app.models.gene import Gene, GeneCuration, GeneEvidence
from app.schemas.gene import GeneCreate, GeneUpdate


class CRUDGene:
    """CRUD operations for genes"""

    def get(self, db: Session, gene_id: int) -> Gene | None:
        """Get gene by ID"""
        return db.query(Gene).filter(Gene.id == gene_id).first()

    def get_by_symbol(self, db: Session, symbol: str) -> Gene | None:
        """Get gene by symbol"""
        return db.query(Gene).filter(func.upper(Gene.approved_symbol) == symbol.upper()).first()

    def get_gene_by_symbol(self, db: Session, symbol: str) -> Gene | None:
        """Get gene by symbol (alias for get_by_symbol for test compatibility)"""
        return self.get_by_symbol(db, symbol)

    def get_by_hgnc_id(self, db: Session, hgnc_id: str) -> Gene | None:
        """Get gene by HGNC ID"""
        return db.query(Gene).filter(Gene.hgnc_id == hgnc_id).first()


    def count(self, db: Session, search: str | None = None, min_score: float | None = None) -> int:
        """Count genes with filtering using gene_scores view for percentage scores"""
        if min_score is not None:
            # Use the gene_scores view when filtering by score
            query = """
                SELECT COUNT(DISTINCT gs.gene_id)
                FROM gene_scores gs
                JOIN genes g ON gs.gene_id = g.id
                WHERE 1=1
            """
            params = {}

            if search:
                query += " AND (gs.approved_symbol ILIKE :search OR g.hgnc_id ILIKE :search)"
                params["search"] = f"%{search}%"

            if min_score is not None:
                query += " AND gs.percentage_score >= :min_score"
                params["min_score"] = min_score

            result = db.execute(text(query), params).scalar()
            return result if result is not None else 0
        else:
            # Use regular query when not filtering by score
            query = db.query(func.count(Gene.id))

            if search:
                search_filter = f"%{search}%"
                query = query.filter(
                    or_(Gene.approved_symbol.ilike(search_filter), Gene.hgnc_id.ilike(search_filter))
                )

            result = query.scalar()
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
        """Get all evidence for a gene"""
        return db.query(GeneEvidence).filter(GeneEvidence.gene_id == gene_id).all()

    def get_curation(self, db: Session, gene_id: int) -> GeneCuration | None:
        """Get curation data for a gene"""
        return db.query(GeneCuration).filter(GeneCuration.gene_id == gene_id).first()

    def get_gene_score(self, db: Session, gene_id: int) -> dict | None:
        """Get gene scores from the gene_scores view"""
        result = db.execute(
            text("""
                SELECT gene_id, approved_symbol, source_count, evidence_count,
                       raw_score, percentage_score, total_active_sources, source_scores
                FROM gene_scores
                WHERE gene_id = :gene_id
            """),
            {"gene_id": gene_id}
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

    def get_multi_with_scores(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        search: str | None = None,
        min_score: float | None = None,
        sort_by: str | None = None,
        sort_desc: bool = False,
    ) -> list[dict]:
        """Get multiple genes with scores from the view"""
        # Build query using the gene_scores view
        params = {"skip": skip, "limit": limit}

        base_query = """
            SELECT gs.gene_id, gs.approved_symbol, gs.source_count, gs.evidence_count,
                   gs.raw_score, gs.percentage_score, gs.total_active_sources,
                   g.hgnc_id, g.aliases, g.created_at, g.updated_at
            FROM gene_scores gs
            JOIN genes g ON gs.gene_id = g.id
            WHERE 1=1
        """

        # Search filter
        if search:
            base_query += " AND (gs.approved_symbol ILIKE :search OR g.hgnc_id ILIKE :search)"
            params["search"] = f"%{search}%"

        # Score filter (using percentage_score)
        if min_score is not None:
            base_query += " AND gs.percentage_score >= :min_score"
            params["min_score"] = min_score

        # Sorting
        if sort_by == "approved_symbol":
            order_clause = "gs.approved_symbol"
        elif sort_by == "hgnc_id":
            order_clause = "g.hgnc_id"
        elif sort_by == "evidence_count":
            order_clause = "gs.evidence_count"
        elif sort_by == "evidence_score":
            order_clause = "gs.percentage_score"
        else:
            order_clause = "gs.approved_symbol"

        if sort_desc:
            base_query += f" ORDER BY {order_clause} DESC NULLS LAST"
        else:
            base_query += f" ORDER BY {order_clause} ASC NULLS FIRST"

        base_query += " LIMIT :limit OFFSET :skip"

        results = db.execute(text(base_query), params).fetchall()

        genes = []
        for row in results:
            genes.append({
                "id": row[0],
                "approved_symbol": row[1],
                "source_count": row[2],
                "evidence_count": row[3],
                "raw_score": row[4],
                "percentage_score": row[5],
                "total_active_sources": row[6],
                "hgnc_id": row[7],
                "aliases": row[8] or [],
                "created_at": row[9],
                "updated_at": row[10],
            })

        return genes

    def create_pipeline_run(self, db: Session) -> int:
        """Create a new pipeline run record and return its ID (for test compatibility)"""
        # This is a simplified implementation for test compatibility
        from datetime import datetime, timezone

        from app.models.gene import PipelineRun

        run = PipelineRun(
            status="running",
            started_at=datetime.now(timezone.utc),
            stats={}
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        return run.id

    def create_or_update_gene(self, db: Session, hgnc_id: str, symbol: str) -> int:
        """Create or update a gene and return its ID (for test compatibility)"""
        # Check if gene already exists
        existing = self.get_by_symbol(db, symbol)
        if existing:
            return existing.id

        # Create new gene
        from app.schemas.gene import GeneCreate
        gene_data = GeneCreate(
            hgnc_id=hgnc_id,
            approved_symbol=symbol,
            aliases=[]
        )
        new_gene = self.create(db, gene_data)
        return new_gene.id

    def create_gene_evidence(self, db: Session, gene_id: int, source_name: str, evidence_data: dict) -> int:
        """Create gene evidence record and return its ID (for test compatibility)"""
        from datetime import datetime, timezone

        from app.models.gene import GeneEvidence

        evidence = GeneEvidence(
            gene_id=gene_id,
            source_name=source_name,
            evidence_data=evidence_data,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(evidence)
        db.commit()
        db.refresh(evidence)
        return evidence.id


# Create singleton instance
gene_crud = CRUDGene()
