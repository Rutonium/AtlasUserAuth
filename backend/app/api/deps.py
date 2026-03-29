from fastapi import Cookie, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from app.core.settings import Settings, get_settings
from app.db.session import get_db
from app.services import session_service, user_access_service


def get_app_settings() -> Settings:
    return get_settings()


def current_session(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    session_cookie: str | None = Cookie(default=None, alias='atlas_auth_session'),
):
    session = session_service.get_session(db, signed_cookie=session_cookie, settings=settings)
    request.state.session = session
    return session


def require_authenticated(session=Depends(current_session)):
    if not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Not authenticated')
    return session


def require_admin(db: Session = Depends(get_db), session=Depends(require_authenticated)):
    if session.EmployeeID == 0:
        return session
    user = user_access_service.get_user_by_employee_id(db, session.EmployeeID)
    if not user or not user.IsAdmin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Admin required')
    return session
