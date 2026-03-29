from sqlalchemy import text
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends
from app.db.session import get_db
from app.schemas.common import ApiHealthResponse, HealthResponse
from app.services.employee_directory_service import cache_status

router = APIRouter(tags=['health'])


@router.get('/healthz', response_model=HealthResponse)
def healthz():
    return HealthResponse(ok=True, service='atlas_user_auth')


@router.get('/api/healthz', response_model=ApiHealthResponse)
def api_healthz(db: Session = Depends(get_db)):
    db_ok = True
    try:
        db.execute(text('SELECT 1'))
    except Exception:
        db_ok = False

    status = cache_status()
    return ApiHealthResponse(
        ok=db_ok,
        service='atlas_user_auth',
        db_ok=db_ok,
        employee_cache_ok=status['employee_cache_ok'],
        employee_cache_size=status['employee_cache_size'],
        employee_cache_last_refresh_epoch=status['employee_cache_last_refresh_epoch'],
        employee_cache_last_error=status['employee_cache_last_error'],
    )
