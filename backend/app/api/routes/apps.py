from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.api.deps import get_app_settings, require_admin
from app.core.settings import Settings
from app.db.session import get_db
from app.schemas.users import RightDefinitionCreateRequest, RightDefinitionUpdateRequest, RightsMatrixResponse, RightDefinitionRow
from app.services import app_rights_service
from app.services.audit_log_service import log_event
from app.services.csrf_service import enforce_csrf

router = APIRouter(prefix='/auth/apps', tags=['apps'])


@router.get('/rights-matrix', response_model=RightsMatrixResponse)
def get_rights_matrix(appKey: str | None = None, db: Session = Depends(get_db), session=Depends(require_admin)):
    del session
    apps = app_rights_service.list_apps(db)
    selected = appKey or (apps[0] if apps else "")
    rows = app_rights_service.get_matrix(db, app_key=selected) if selected else []
    return RightsMatrixResponse(app_key=selected, apps=apps, rows=[RightDefinitionRow(**row) for row in rows])


@router.put('/{app_key}/rights-matrix/{right_key}')
def update_right_definition(
    app_key: str,
    right_key: str,
    payload: RightDefinitionUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    session=Depends(require_admin),
):
    enforce_csrf(request, session.CsrfToken, settings.csrf_header_name)
    row = app_rights_service.upsert_right(db, app_key=app_key, right_key=right_key, levels=payload.levels)
    log_event(
        'App right definition updated',
        event_type='admin.app_rights.update',
        employee_id=session.EmployeeID,
        ip=request.client.host if request.client else None,
        app_key=app_key,
        result='ok',
    )
    return {'ok': True, 'app_key': app_key, 'right_key': row.RightKey, 'levels': payload.levels}


@router.post('/{app_key}/rights-matrix')
def create_right_definition(
    app_key: str,
    payload: RightDefinitionCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    session=Depends(require_admin),
):
    enforce_csrf(request, session.CsrfToken, settings.csrf_header_name)
    row = app_rights_service.upsert_right(
        db,
        app_key=app_key,
        right_key=payload.right_key.strip(),
        levels={"1": False, "2": False, "3": False, "4": False, "5": False},
    )
    log_event(
        'App right definition created',
        event_type='admin.app_rights.create',
        employee_id=session.EmployeeID,
        ip=request.client.host if request.client else None,
        app_key=app_key,
        result='ok',
    )
    return {'ok': True, 'app_key': app_key, 'right_key': row.RightKey}


@router.delete('/{app_key}/rights-matrix/{right_key}')
def delete_right_definition(
    app_key: str,
    right_key: str,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    session=Depends(require_admin),
):
    enforce_csrf(request, session.CsrfToken, settings.csrf_header_name)
    deleted = app_rights_service.delete_right(db, app_key=app_key, right_key=right_key)
    if not deleted:
        raise HTTPException(status_code=404, detail='Right definition not found')
    log_event(
        'App right definition deleted',
        event_type='admin.app_rights.delete',
        employee_id=session.EmployeeID,
        ip=request.client.host if request.client else None,
        app_key=app_key,
        result='ok',
    )
    return {'ok': True}
