from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.api.deps import get_app_settings, require_admin
from app.core.settings import Settings
from app.db.models import AtlasUser
from app.db.session import get_db
from app.schemas.users import ProvisionByEmployeeIdRequest, ResetCredentialRequest, UserAccessUpdateRequest, UserSummary
from app.services import auth_service, employee_directory_service, user_access_service
from app.services.audit_log_service import log_event
from app.services.csrf_service import enforce_csrf

router = APIRouter(prefix='/auth/users', tags=['users'])


@router.get('', response_model=list[UserSummary])
def list_auth_users(db: Session = Depends(get_db), session=Depends(require_admin)):
    del session
    users = user_access_service.list_users(db)
    return [
        UserSummary(
            employee_id=u.EmployeeID,
            name=u.Name,
            email=u.EMail,
            is_admin=bool(u.IsAdmin),
            is_active=bool(u.IsActive),
        )
        for u in users
    ]


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

    user = user_access_service.get_user_by_employee_id(db, employee_id)
    if not user:
        raise HTTPException(status_code=404, detail='User not found')

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
    auth_service.reset_credential(db, employee_id=employee_id, new_password=payload.new_password)
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

    user = user_access_service.get_user_by_employee_id(db, employee_id)
    if not user:
        user = AtlasUser(
            EmployeeID=employee_id,
            Name=directory_entry.get('name'),
            Initials=directory_entry.get('initials'),
            EMail=directory_entry.get('email'),
            IsActive=True,
            IsAdmin=payload.make_admin,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        user.Name = directory_entry.get('name')
        user.Initials = directory_entry.get('initials')
        user.EMail = directory_entry.get('email')
        if payload.make_admin:
            user.IsAdmin = True
        db.add(user)
        db.commit()

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
        'name': user.Name,
        'app_key': access.AppKey,
        'role': access.Role,
    }
