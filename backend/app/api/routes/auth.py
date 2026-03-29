import json
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session
from app.api.deps import get_app_settings, require_authenticated
from app.core.settings import Settings
from app.db.session import get_db
from app.schemas.auth import LoginRequest, LoginResponse, LogoutResponse, MeResponse
from app.services import auth_service, employee_directory_service, lockout_service, session_service, user_access_service
from app.services.audit_log_service import log_event
from app.services.csrf_service import enforce_csrf

router = APIRouter(prefix='/auth', tags=['auth'])


@router.post('/login', response_model=LoginResponse)
def login(payload: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db), settings: Settings = Depends(get_app_settings)):
    ip = request.client.host if request.client else 'unknown'
    normalized = auth_service.normalize_employee_id(payload.employee_id)

    if lockout_service.is_locked(ip, normalized or payload.employee_id):
        log_event('Login denied due to lockout', event_type='auth.lockout', employee_id=None, ip=ip, result='locked')
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail='Too many attempts, try again later')

    result = auth_service.verify_credentials(db, employee_id_raw=payload.employee_id, password=payload.password, settings=settings)
    if not result.ok or result.employee_id is None:
        lockout_service.register_failure(ip, normalized or payload.employee_id)
        log_event('Login failed', event_type='auth.login', employee_id=None, ip=ip, result='failed')
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid credentials')

    lockout_service.register_success(ip, str(result.employee_id))
    signed_cookie, csrf_token = session_service.create_session(db, employee_id=result.employee_id, settings=settings)

    response.set_cookie(
        key=settings.session_cookie_name,
        value=signed_cookie,
        max_age=settings.session_absolute_timeout_seconds,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
        domain=settings.session_cookie_domain,
        path=settings.session_cookie_path,
    )
    response.set_cookie(
        key='atlas_auth_csrf',
        value=csrf_token,
        max_age=settings.session_absolute_timeout_seconds,
        httponly=False,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
        domain=settings.session_cookie_domain,
        path=settings.session_cookie_path,
    )
    log_event('Login succeeded', event_type='auth.login', employee_id=result.employee_id, ip=ip, result='ok')
    return LoginResponse(ok=True, message='Authenticated')


@router.post('/logout', response_model=LogoutResponse)
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    session=Depends(require_authenticated),
    session_cookie: str | None = Cookie(default=None, alias='atlas_auth_session'),
):
    enforce_csrf(request, session.CsrfToken, settings.csrf_header_name)
    del session
    response.delete_cookie(settings.session_cookie_name, path=settings.session_cookie_path, domain=settings.session_cookie_domain)
    response.delete_cookie('atlas_auth_csrf', path=settings.session_cookie_path, domain=settings.session_cookie_domain)
    session_service.destroy_session(db, signed_cookie=session_cookie, settings=settings)
    return LogoutResponse(ok=True)


@router.get('/me', response_model=MeResponse)
def me(
    appKey: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    session=Depends(require_authenticated),
):
    if session.EmployeeID == 0:
        return MeResponse(
            authenticated=True,
            employee_id=0,
            name=settings.local_admin_name,
            email=None,
            is_admin=True,
            app_key=appKey,
            role='super_admin',
            rights={'all': True},
        )

    user = user_access_service.get_user_by_employee_id(db, session.EmployeeID)
    if not user:
        return MeResponse(authenticated=True, employee_id=session.EmployeeID, app_key=appKey)

    employee = employee_directory_service.get_employee(settings, session.EmployeeID) or {}

    access = user_access_service.get_app_access(db, employee_id=session.EmployeeID, app_key=appKey)
    rights = {}
    role = None
    if access:
        role = access.Role
        try:
            rights = json.loads(access.RightsJson or '{}')
        except Exception:
            rights = {}

    return MeResponse(
        authenticated=True,
        employee_id=int(user.get('EmployeeID') or session.EmployeeID),
        name=employee.get('name'),
        email=employee.get('email'),
        is_admin=user_access_service.is_admin_user(db, session.EmployeeID),
        app_key=appKey,
        role=role,
        rights=rights,
    )
