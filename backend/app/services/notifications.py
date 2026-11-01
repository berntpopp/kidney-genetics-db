"""Email notifications for staff events; per-user opt-out, off when SMTP is not configured."""

from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.email import email_enabled, send_email
from app.core.logging import get_logger
from app.models.curation_report import CurationReport, UserNotificationPref
from app.models.user import User

logger = get_logger(__name__)

# event key -> label shown in the preferences UI; later features add their events here
EVENTS = {"curation_report": "A report or suggestion on a curated gene"}


def prefs_for(db: Session, user: User) -> dict[str, bool]:
    stored = {
        p.event: p.enabled
        for p in db.query(UserNotificationPref).filter(UserNotificationPref.user_id == user.id)
    }
    return {event: stored.get(event, True) for event in EVENTS}


def set_pref(db: Session, user: User, event: str, enabled: bool) -> None:
    db.merge(UserNotificationPref(user_id=user.id, event=event, enabled=enabled))


def report_body(report: CurationReport, gene_symbol: str) -> tuple[str, str]:
    subject = f"[Kidney-Genetics] New {report.kind} on {gene_symbol}"
    who = report.reporter_name or "Anonymous"
    if report.reporter_email:
        who += f" <{report.reporter_email}>"
    body = (
        f"A {report.kind} was submitted for {gene_symbol}.\n\nFrom: {who}\n\n{report.message}\n\n"
        f"Review it: {settings.SITE_URL}/curation/reports\n"
        "Turn these emails off in your account notification preferences.\n"
    )
    return subject, body


async def _send(user_id: int, to: str, subject: str, body: str) -> None:
    try:
        await send_email(to, subject, body)
    except Exception as exc:  # a failed notification must never fail the request
        await logger.error("Notification email failed", user_id=user_id, error=str(exc))


def notify(
    db: Session,
    event: str,
    users: list[User],
    subject: str,
    body: str,
    background_tasks: BackgroundTasks,
) -> None:
    if not email_enabled():
        return
    for user in users:
        if user.is_active and prefs_for(db, user).get(event, False):
            background_tasks.add_task(_send, user.id, user.email, subject, body)
