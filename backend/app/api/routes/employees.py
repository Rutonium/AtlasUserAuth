from fastapi import APIRouter, Depends
from app.api.deps import get_app_settings, require_admin
from app.core.settings import Settings
from app.services import employee_directory_service

router = APIRouter(prefix='/auth/employees', tags=['employees'])


@router.get('/search')
def employee_search(q: str = '', settings: Settings = Depends(get_app_settings), session=Depends(require_admin)):
    del session
    return {'items': employee_directory_service.search_employees(settings, q=q, limit=20)}


@router.get('/public-search')
def public_employee_search(q: str = '', settings: Settings = Depends(get_app_settings)):
    return {'items': employee_directory_service.search_employees(settings, q=q, limit=12)}
