"""Public problem/suggestion reports on curated associations, and per-user notification prefs."""

from sqlalchemy import (
    BigInteger,
    Boolean,
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


class CurationReport(Base):
    __tablename__ = "curation_report"
    __table_args__ = (
        CheckConstraint("kind IN ('problem', 'suggestion')", name="ck_curation_report_kind"),
        CheckConstraint(
            "status IN ('open', 'resolved', 'dismissed')", name="ck_curation_report_status"
        ),
        Index("ix_curation_report_status_gene", "status", "gene_id"),
    )

    id = Column(BigInteger, primary_key=True)
    gene_id = Column(BigInteger, ForeignKey("genes.id"), nullable=False)
    association_id = Column(BigInteger, ForeignKey("gene_disease_associations.id"), nullable=True)
    kind = Column(String(20), nullable=False)
    message = Column(Text, nullable=False)
    reporter_name = Column(String(200), nullable=True)
    reporter_email = Column(String(320), nullable=True)  # curators only; never in a public response
    status = Column(String(20), nullable=False, server_default="open")
    handled_by = Column(BigInteger, ForeignKey("users.id"), nullable=True)
    handled_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    gene = relationship("Gene")


class UserNotificationPref(Base):
    """A missing row means the event is enabled."""

    __tablename__ = "user_notification_pref"

    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    event = Column(String(40), primary_key=True)
    enabled = Column(Boolean, nullable=False)
