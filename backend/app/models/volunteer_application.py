"""Public applications to volunteer as a curator for a gene; admins decide."""

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base


class VolunteerApplication(Base):
    __tablename__ = "volunteer_application"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected')", name="ck_volunteer_application_status"
        ),
        Index("ix_volunteer_application_status_created", "status", "created_at"),
    )

    id = Column(BigInteger, primary_key=True)
    gene_id = Column(BigInteger, ForeignKey("genes.id"), nullable=False)
    name = Column(String(200), nullable=False)
    email = Column(String(320), nullable=False)  # admins only; never in a public response
    affiliation = Column(String(300), nullable=True)
    orcid = Column(String(19), nullable=True)
    motivation = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, server_default="pending")
    decided_by = Column(BigInteger, ForeignKey("users.id"), nullable=True)
    decided_at = Column(DateTime(timezone=True), nullable=True)
    decision_note = Column(Text, nullable=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    gene = relationship("Gene")
