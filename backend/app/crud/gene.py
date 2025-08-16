"""
CRUD operations for genes
"""

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

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

    def get_by_hgnc_id(self, db: Session, hgnc_id: str) -> Gene | None:
        """Get gene by HGNC ID"""
        return db.query(Gene).filter(Gene.hgnc_id == hgnc_id).first()

    def get_multi(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        search: str | None = None,
        min_score: float | None = None,
    ) -> list[Gene]:
        """Get multiple genes with filtering"""
        query = db.query(Gene).options(joinedload(Gene.curation))

        # Search filter
        if search:
            search_filter = f"%{search}%"
            query = query.filter(
                or_(Gene.approved_symbol.ilike(search_filter), Gene.hgnc_id.ilike(search_filter))
            )

        # Score filter (requires join with curation)
        if min_score is not None:
            query = query.join(GeneCuration).filter(GeneCuration.evidence_score >= min_score)

        # Order by symbol
        query = query.order_by(Gene.approved_symbol)

        return query.offset(skip).limit(limit).all()

    def count(self, db: Session, search: str | None = None, min_score: float | None = None) -> int:
        """Count genes with filtering"""
        query = db.query(func.count(Gene.id))

        if search:
            search_filter = f"%{search}%"
            query = query.filter(
                or_(Gene.approved_symbol.ilike(search_filter), Gene.hgnc_id.ilike(search_filter))
            )

        if min_score is not None:
            query = query.join(GeneCuration).filter(GeneCuration.evidence_score >= min_score)

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


# Create singleton instance
gene_crud = CRUDGene()
