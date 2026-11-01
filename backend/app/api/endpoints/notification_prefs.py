"""Per-user email notification preferences."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.endpoints.auth import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.curation_report import NotificationPref
from app.services import notifications

router = APIRouter()


def _list(db: Session, user: User) -> list[dict[str, object]]:
    prefs = notifications.prefs_for(db, user)
    return [
        {"event": e, "label": notifications.EVENTS[e], "enabled": on} for e, on in prefs.items()
    ]


@router.get("/me/notification-prefs", response_model=list[NotificationPref])
def get_prefs(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[dict[str, object]]:
    return _list(db, user)


@router.put("/me/notification-prefs", response_model=list[NotificationPref])
def put_prefs(
    body: dict[str, bool],
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[dict[str, object]]:
    unknown = set(body) - set(notifications.EVENTS)
    if unknown:
        raise HTTPException(status_code=422, detail=f"Unknown event: {sorted(unknown)[0]}")
    for event, enabled in body.items():
        notifications.set_pref(db, user, event, enabled)
    db.commit()
    return _list(db, user)
