"""Public volunteer-curator applications; an admin decision creates or links the account."""

import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import require_admin
from app.core.rate_limit import LIMIT_VOLUNTEER_APPLICATION, limiter
from app.core.security import (
    generate_password_reset_token,
    get_password_hash,
    hash_reset_token,
)
from app.models.gene import Gene
from app.models.user import User
from app.models.volunteer_application import VolunteerApplication
from app.schemas.volunteer_application import (
    ApplicationCreate,
    ApplicationDecision,
    ApplicationList,
    ApplicationResponse,
)
from app.services import notifications

router = APIRouter()

INVITE_VALID_DAYS = 7


def _to_response(application: VolunteerApplication) -> dict[str, Any]:
    fields = [c for c in ApplicationResponse.model_fields if c != "gene_symbol"]
    return {
        **{c: getattr(application, c) for c in fields},
        "gene_symbol": application.gene.approved_symbol,
    }


def _unique_username(db: Session, email: str) -> str:
    base = (re.sub(r"[^a-z0-9._-]", "", email.split("@")[0].lower()) or "curator")[:40]
    name, n = base, 1
    while db.query(User.id).filter(User.username == name).first():
        n += 1
        name = f"{base}{n}"
    return name


@router.post("/", status_code=202)
@limiter.limit(LIMIT_VOLUNTEER_APPLICATION)
def create_application(
    request: Request,
    response: Response,
    body: ApplicationCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Public: apply to curate a gene. Stored data is never echoed."""
    if body.website:  # honeypot: bots fill every field; pretend success, store nothing
        return {"status": "received"}
    gene = (
        db.query(Gene).filter(func.upper(Gene.approved_symbol) == body.gene_symbol.upper()).first()
    )
    if gene is None:
        raise HTTPException(status_code=404, detail="Gene not found")
    duplicate = (
        db.query(VolunteerApplication.id)
        .filter(
            VolunteerApplication.gene_id == gene.id,
            VolunteerApplication.status == "pending",
            func.lower(VolunteerApplication.email) == body.email.lower(),
        )
        .first()
    )
    if duplicate:
        return {"status": "received"}

    db.add(
        VolunteerApplication(
            gene_id=gene.id,
            name=body.name,
            email=body.email,
            affiliation=body.affiliation,
            orcid=body.orcid,
            motivation=body.motivation,
        )
    )
    db.commit()
    symbol = gene.approved_symbol
    notifications.send_transactional(
        body.email,
        f"[Kidney-Genetics] We received your application for {symbol}",
        f"Hello {body.name},\n\nThank you for volunteering to curate {symbol}. An administrator "
        "will review your application and email you with the decision.\n",
        background_tasks,
    )
    admins = db.query(User).filter(User.role == "admin", User.is_active.is_(True)).all()
    notifications.notify(
        db,
        "volunteer_application",
        admins,
        f"[Kidney-Genetics] New volunteer application for {symbol}",
        f"{body.name} <{body.email}> applied to curate {symbol}.\n\n"
        f"Review it: {settings.SITE_URL}/admin/volunteer-applications\n"
        "Turn these emails off in your account notification preferences.\n",
        background_tasks,
    )
    return {"status": "received"}


@router.get("/", response_model=ApplicationList)
def list_applications(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
    status: str | None = Query(None, pattern="^(pending|approved|rejected)$"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    """Applications with applicant contact details (admins only)."""
    query = db.query(VolunteerApplication)
    if status:
        query = query.filter(VolunteerApplication.status == status)
    rows = (
        query.order_by(VolunteerApplication.created_at.desc(), VolunteerApplication.id.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )
    pending = db.query(VolunteerApplication).filter(VolunteerApplication.status == "pending")
    return {
        "data": [_to_response(r) for r in rows],
        "meta": {
            "total": query.count(),
            "limit": limit,
            "offset": offset,
            "pending_count": pending.count(),
        },
    }


@router.post("/{application_id}/decision", response_model=ApplicationResponse)
def decide_application(
    application_id: int,
    body: ApplicationDecision,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> dict[str, Any]:
    application = db.get(VolunteerApplication, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")
    if application.status != "pending":
        raise HTTPException(status_code=409, detail="Application was already decided")

    symbol = application.gene.approved_symbol
    invite_token = None
    if body.decision == "approved":
        user = db.query(User).filter(func.lower(User.email) == application.email.lower()).first()
        if user is None:
            # Pre-verified like /auth/register; the password is unusable, the applicant sets
            # their own through the reset link.
            invite_token = generate_password_reset_token()
            user = User(
                email=application.email,
                username=_unique_username(db, application.email),
                hashed_password=get_password_hash(secrets.token_urlsafe(32)),
                full_name=application.name,
                role=body.role,
                is_active=True,
                is_verified=True,
                is_admin=False,
                password_reset_token=hash_reset_token(invite_token),
                password_reset_expires=datetime.now(timezone.utc)
                + timedelta(days=INVITE_VALID_DAYS),
            )
            db.add(user)
            db.flush()
        elif user.role == "viewer" and body.role == "curator":
            user.role = "curator"
        application.user_id = user.id
    application.status = body.decision
    application.decided_by = admin.id
    application.decided_at = datetime.now(timezone.utc)
    application.decision_note = body.note
    db.commit()

    subject = f"[Kidney-Genetics] Your application for {symbol}"
    if body.decision == "approved":
        text = f"Hello {application.name},\n\nYour application to curate {symbol} was approved.\n"
        if invite_token:
            link = f"{settings.SITE_URL}/reset-password?token={invite_token}"
            text += f"\nSet your password within {INVITE_VALID_DAYS} days to sign in:\n{link}\n"
        else:
            text += f"\nSign in with your existing account: {settings.SITE_URL}/login\n"
    else:
        text = (
            f"Hello {application.name},\n\nThank you for offering to curate {symbol}. "
            "We are unable to accept your application at this time.\n"
        )
    if body.note:
        text += f"\nNote from the administrator:\n{body.note}\n"
    notifications.send_transactional(application.email, subject, text, background_tasks)
    return _to_response(application)
