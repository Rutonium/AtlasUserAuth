from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.api.deps import get_app_settings, require_admin
from app.core.settings import Settings
from app.db.session import get_db
from app.schemas.users import (
    AccessMatrixAddUserRequest,
    AccessMatrixApp,
    AccessMatrixCellUpdateRequest,
    AccessMatrixResponse,
    AccessMatrixUser,
    AppAccessSummary,
    DashboardSummary,
    ProvisionByEmployeeIdRequest,
    ResetCredentialRequest,
    UserAccessUpdateRequest,
    UserDetail,
    UserSummary,
)
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
                app_access_count=int(u.get('AppAccessCount') or 0),
                active_app_count=int(u.get('ActiveAppCount') or 0),
                app_keys=list(u.get('AppKeys') or []),
            )
        )
    return rows


@router.get('/matrix', response_model=AccessMatrixResponse)
def get_access_matrix(db: Session = Depends(get_db), session=Depends(require_admin)):
    del session
    settings = get_app_settings()
    payload = user_access_service.access_matrix(db)
    users: list[AccessMatrixUser] = []
    for row in payload.get('users') or []:
        employee_id = int(row.get('employee_id') or 0)
        directory_entry = employee_directory_service.get_employee(settings, employee_id) or {}
        users.append(
            AccessMatrixUser(
                employee_id=employee_id,
                name=directory_entry.get('name'),
                email=directory_entry.get('email'),
                is_active=bool(row.get('is_active', True)),
                app_levels=dict(row.get('app_levels') or {}),
            )
        )
    apps = [AccessMatrixApp(**row) for row in payload.get('apps') or []]
    return AccessMatrixResponse(apps=apps, users=users)


@router.put('/matrix/{employee_id}/apps/{app_key}')
def update_matrix_cell(
    employee_id: int,
    app_key: str,
    payload: AccessMatrixCellUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    session=Depends(require_admin),
):
    enforce_csrf(request, session.CsrfToken, settings.csrf_header_name)
    updated = user_access_service.update_access_level_only(db, employee_id=employee_id, app_key=app_key, access_level=payload.access_level)
    log_event(
        'User access level updated from matrix',
        event_type='admin.user_access.matrix_update',
        employee_id=employee_id,
        ip=request.client.host if request.client else None,
        app_key=app_key,
        result='ok',
    )
    return {
        'ok': True,
        'employee_id': employee_id,
        'app_key': app_key,
        'access_level': int(payload.access_level),
        'is_active': bool(updated.IsActive) if updated else False,
    }


@router.post('/matrix/add-user')
def add_user_from_matrix(
    payload: AccessMatrixAddUserRequest,
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

    selected_levels = {
        str(app_key).strip(): int(level)
        for app_key, level in (payload.app_levels or {}).items()
        if str(app_key).strip() and int(level or 0) > 0
    }
    if not selected_levels:
        raise HTTPException(status_code=400, detail='Choose at least one app access level before adding the user')

    user_access_service.ensure_user_exists(db, employee_id=employee_id, is_active=True)
    for app_key, level in selected_levels.items():
        user_access_service.update_access_level_only(db, employee_id=employee_id, app_key=app_key, access_level=level)

    log_event(
        'User added from matrix',
        event_type='admin.user_access.matrix_add_user',
        employee_id=employee_id,
        ip=request.client.host if request.client else None,
        result='ok',
    )
    return {
        'ok': True,
        'employee_id': employee_id,
        'name': directory_entry.get('name'),
        'app_levels': selected_levels,
    }


@router.get('/summary', response_model=DashboardSummary)
def get_dashboard_summary(db: Session = Depends(get_db), session=Depends(require_admin)):
    del session
    return DashboardSummary(**user_access_service.dashboard_summary(db))


@router.get('/{employee_id}', response_model=UserDetail)
def get_user_detail(employee_id: int, db: Session = Depends(get_db), session=Depends(require_admin)):
    del session
    settings = get_app_settings()
    detail = user_access_service.get_user_detail(db, employee_id=employee_id)
    if not detail:
        raise HTTPException(status_code=404, detail='User not found')
    directory_entry = employee_directory_service.get_employee(settings, employee_id) or {}
    return UserDetail(
        employee_id=employee_id,
        name=directory_entry.get('name'),
        email=directory_entry.get('email'),
        is_admin=user_access_service.is_admin_user(db, employee_id),
        is_active=bool(detail.get('IsActive', True)),
        app_access_count=int(detail.get('AppAccessCount') or 0),
        active_app_count=int(detail.get('ActiveAppCount') or 0),
        app_keys=list(detail.get('AppKeys') or []),
        access_entries=[AppAccessSummary(**entry) for entry in detail.get('AccessEntries') or []],
    )


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
        access_level=payload.access_level,
        access_label=payload.access_label,
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
        'access_level': access.AccessLevel,
        'access_label': access.AccessLabel,
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
            access_level=5,
            access_label='Owner',
            rights={'manage_users': True},
            is_active=True,
        )

    access = user_access_service.upsert_app_access(
        db,
        employee_id=employee_id,
        app_key=payload.app_key,
        role=payload.initial_role,
        access_level=payload.initial_access_level,
        access_label=payload.initial_access_label,
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
        'access_level': access.AccessLevel,
        'access_label': access.AccessLabel,
    }
