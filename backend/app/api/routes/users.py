from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.api.deps import get_app_settings, require_admin
from app.core.settings import Settings
from app.db.session import get_db
from app.schemas.users import ProvisionByEmployeeIdRequest, ResetCredentialRequest, UserAccessUpdateRequest, UserSummary
from app.services import auth_service, employee_directory_service, user_access_service
from app.services.audit_log_service import log_event
from app.services.csrf_service import enforce_csrf

router = APIRouter(prefix='/auth/users', tags=['users'])


@router.get('', response_model=list[UserSummary])
def list_auth_users(db: Session = Depends(get_db), session=Depends(require_admin)):
    del session
    settings = get_app_settings()
    users = user_access_service.list_users(db)
    rows: list[UserSummary] = []
    for u in users:
        employee_id = int(u.get('EmployeeID') or 0)
        directory_entry = employee_directory_service.get_employee(settings, employee_id) or {}
        rows.append(
            UserSummary(
                employee_id=employee_id,
                name=directory_entry.get('name'),
                email=directory_entry.get('email'),
                is_admin=user_access_service.is_admin_user(db, employee_id),
                is_active=bool(u.get('IsActive', True)),
            )
        )
    return rows


@router.put('/{employee_id}/apps/{app_key}')
def upsert_user_access(
    employee_id: int,
    app_key: str,
    payload: UserAccessUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    session=Depends(require_admin),
):
    enforce_csrf(request, session.CsrfToken, settings.csrf_header_name)

    access = user_access_service.upsert_app_access(
        db,
        employee_id=employee_id,
        app_key=app_key,
        role=payload.role,
        rights=payload.rights,
        is_active=payload.is_active,
    )
    log_event(
        'User app access updated',
        event_type='admin.user_access.update',
        employee_id=employee_id,
        ip=request.client.host if request.client else None,
        app_key=app_key,
        result='ok',
    )
    return {
        'ok': True,
        'employee_id': employee_id,
        'app_key': app_key,
        'role': access.Role,
        'rights': payload.rights,
        'is_active': access.IsActive,
    }


@router.post('/{employee_id}/reset-credential')
def reset_user_credential(
    employee_id: int,
    payload: ResetCredentialRequest,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    session=Depends(require_admin),
):
    enforce_csrf(request, session.CsrfToken, settings.csrf_header_name)
    try:
        auth_service.reset_credential(db, employee_id=employee_id, new_password=payload.new_password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    log_event(
        'User credential reset by admin',
        event_type='admin.user.reset_credential',
        employee_id=employee_id,
        ip=request.client.host if request.client else None,
        result='ok',
    )
    return {'ok': True}


@router.post('/provision-by-employee-id')
def provision_by_employee_id(
    payload: ProvisionByEmployeeIdRequest,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    session=Depends(require_admin),
):
    enforce_csrf(request, session.CsrfToken, settings.csrf_header_name)

    normalized = auth_service.normalize_employee_id(payload.employee_id)
    if not normalized:
        raise HTTPException(status_code=400, detail='Invalid employee_id')
    employee_id = int(normalized)

    directory_entry = employee_directory_service.get_employee(settings, employee_id)
    if not directory_entry:
        raise HTTPException(status_code=400, detail='EmployeeID not found in employee directory')

    # Best-effort user row for environments where AtlasUsers is used directly.
    user_access_service.ensure_user_exists(db, employee_id=employee_id, is_active=True)

    if payload.make_admin:
        user_access_service.upsert_app_access(
            db,
            employee_id=employee_id,
            app_key='atlas_user_auth_admin',
            role='admin',
            rights={'manage_users': True},
            is_active=True,
        )

    access = user_access_service.upsert_app_access(
        db,
        employee_id=employee_id,
        app_key=payload.app_key,
        role=payload.initial_role,
        rights={},
        is_active=True,
    )

    log_event(
        'User provisioned by employee id',
        event_type='admin.user.provision',
        employee_id=employee_id,
        ip=request.client.host if request.client else None,
        app_key=payload.app_key,
        result='ok',
    )

    return {
        'ok': True,
        'employee_id': employee_id,
        'name': directory_entry.get('name'),
        'app_key': access.AppKey,
        'role': access.Role,
    }
