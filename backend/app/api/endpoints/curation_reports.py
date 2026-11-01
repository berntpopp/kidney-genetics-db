"""Public problem/suggestion reports on curated associations, triaged by curators."""

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_curator
from app.core.rate_limit import LIMIT_CURATION_REPORT, limiter
from app.models.curation_report import CurationReport
from app.models.gene import Gene
from app.models.gene_disease_association import GeneDiseaseAssociation as GDA
from app.models.user import User
from app.schemas.curation_report import ReportCreate, ReportList, ReportResponse, ReportUpdate
from app.services import notifications

router = APIRouter()


def _to_response(report: CurationReport) -> dict[str, Any]:
    return {
        **{c: getattr(report, c) for c in ReportResponse.model_fields if c != "gene_symbol"},
        "gene_symbol": report.gene.approved_symbol,
    }


@router.post("/", status_code=202)
@limiter.limit(LIMIT_CURATION_REPORT)
def create_report(
    request: Request,
    response: Response,
    body: ReportCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Public: report a problem or suggestion on a published curated association."""
    if body.website:  # honeypot: bots fill every field; pretend success, store nothing
        return {"status": "received"}
    gene = (
        db.query(Gene).filter(func.upper(Gene.approved_symbol) == body.gene_symbol.upper()).first()
    )
    published = db.query(GDA.id).filter(GDA.status == "published")
    if gene is None or not published.filter(GDA.gene_id == gene.id).first():
        raise HTTPException(status_code=404, detail="No curated association found for this gene")
    if (
        body.association_id is not None
        and not published.filter(GDA.id == body.association_id, GDA.gene_id == gene.id).first()
    ):
        raise HTTPException(status_code=404, detail="Association not found for this gene")

    report = CurationReport(
        gene_id=gene.id,
        association_id=body.association_id,
        kind=body.kind,
        message=body.message,
        reporter_name=body.reporter_name,
        reporter_email=body.reporter_email,
    )
    db.add(report)
    db.commit()
    staff = db.query(User).filter(User.role.in_(["curator", "admin"]), User.is_active.is_(True))
    subject, text = notifications.report_body(report, gene.approved_symbol)
    notifications.notify(db, "curation_report", staff.all(), subject, text, background_tasks)
    return {"status": "received"}


@router.get("/", response_model=ReportList)
def list_reports(
    db: Session = Depends(get_db),
    _: User = Depends(require_curator),
    status: str | None = Query(None, pattern="^(open|resolved|dismissed)$"),
    gene_symbol: str | None = Query(None, max_length=100),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    """Reports with reporter contact details (curators and admins)."""
    query = db.query(CurationReport).join(Gene, CurationReport.gene_id == Gene.id)
    if status:
        query = query.filter(CurationReport.status == status)
    if gene_symbol:
        query = query.filter(func.upper(Gene.approved_symbol) == gene_symbol.upper())
    rows = (
        query.order_by(CurationReport.created_at.desc(), CurationReport.id.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )
    open_count = db.query(CurationReport).filter(CurationReport.status == "open").count()
    return {
        "data": [_to_response(r) for r in rows],
        "meta": {
            "total": query.count(),
            "limit": limit,
            "offset": offset,
            "open_count": open_count,
        },
    }


@router.patch("/{report_id}", response_model=ReportResponse)
def update_report(
    report_id: int,
    body: ReportUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_curator),
) -> dict[str, Any]:
    report = db.get(CurationReport, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    report.status = body.status
    report.handled_by = user.id if body.status != "open" else None
    report.handled_at = datetime.now(timezone.utc) if body.status != "open" else None
    db.commit()
    return _to_response(report)
