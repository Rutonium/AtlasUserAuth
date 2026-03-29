import secrets
from sqlalchemy.orm import Session
from app.core.security import now_epoch, sign_value, unsign_value
from app.core.settings import Settings
from app.db.models import AtlasSession


def create_session(db: Session, *, employee_id: int, settings: Settings) -> tuple[str, str]:
    now = now_epoch()
    session_id = secrets.token_urlsafe(32)
    csrf_token = secrets.token_urlsafe(24)
    row = AtlasSession(
        SessionId=session_id,
        EmployeeID=employee_id,
        CreatedAtEpoch=now,
        LastSeenAtEpoch=now,
        CsrfToken=csrf_token,
    )
    db.merge(row)
    db.commit()
    cookie_payload = {'sid': session_id}
    return sign_value(settings.session_signing_secret, cookie_payload), csrf_token


def get_session(db: Session, *, signed_cookie: str | None, settings: Settings) -> AtlasSession | None:
    if not signed_cookie:
        return None
    token = unsign_value(settings.session_signing_secret, signed_cookie)
    if not token:
        return None
    sid = token.get('sid')
    if not sid:
        return None

    row = db.get(AtlasSession, sid)
    if not row:
        return None

    now = now_epoch()
    if now - row.LastSeenAtEpoch > settings.session_idle_timeout_seconds:
        db.delete(row)
        db.commit()
        return None
    if now - row.CreatedAtEpoch > settings.session_absolute_timeout_seconds:
        db.delete(row)
        db.commit()
        return None

    row.LastSeenAtEpoch = now
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def destroy_session(db: Session, *, signed_cookie: str | None, settings: Settings) -> None:
    if not signed_cookie:
        return
    token = unsign_value(settings.session_signing_secret, signed_cookie)
    if not token or 'sid' not in token:
        return
    row = db.get(AtlasSession, token['sid'])
    if row:
        db.delete(row)
        db.commit()
