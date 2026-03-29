import threading
import httpx
from app.core.security import now_epoch
from app.core.settings import Settings

_lock = threading.Lock()
_cache: dict[int, dict] = {}
_last_refresh_epoch: int | None = None
_last_error: str | None = None


def _auth_value(settings: Settings) -> str:
    if settings.employee_api_auth_scheme:
        return f"{settings.employee_api_auth_scheme} {settings.employee_api_token}"
    return settings.employee_api_token


def _normalize_employee(raw: dict) -> tuple[int, dict] | None:
    number = str(raw.get('number', '')).strip()
    name = str(raw.get('name', '')).strip()
    if not number or not name or not number.isdigit():
        return None
    employee_id = int(number)
    return employee_id, {
        'employee_id': employee_id,
        'name': name,
        'initials': (raw.get('initials') or '').strip() or None,
        'email': (raw.get('eMail') or '').strip() or None,
        'department_code': (raw.get('departmentCode') or '').strip() or None,
    }


def refresh_cache(settings: Settings) -> bool:
    global _cache, _last_refresh_epoch, _last_error

    headers = {settings.employee_api_auth_header: _auth_value(settings)}
    url = f"{settings.employee_api_base_url.rstrip('/')}/Employees/all"

    try:
        with httpx.Client(timeout=settings.employee_api_timeout_seconds) as client:
            resp = client.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        tmp: dict[int, dict] = {}
        if isinstance(data, list):
            for row in data:
                if not isinstance(row, dict):
                    continue
                normalized = _normalize_employee(row)
                if normalized:
                    tmp[normalized[0]] = normalized[1]

        with _lock:
            _cache = tmp
            _last_refresh_epoch = now_epoch()
            _last_error = None
        return True
    except Exception as exc:
        with _lock:
            _last_error = str(exc)
        return False


def _maybe_refresh(settings: Settings) -> None:
    with _lock:
        stale = _last_refresh_epoch is None or now_epoch() - _last_refresh_epoch > settings.employee_cache_ttl_seconds
    if stale:
        refresh_cache(settings)


def search_employees(settings: Settings, q: str, limit: int = 20) -> list[dict]:
    _maybe_refresh(settings)
    needle = q.strip().lower()
    with _lock:
        values = list(_cache.values())

    if not needle:
        return values[:limit]

    out = []
    for row in values:
        if needle in str(row['employee_id']) or needle in row['name'].lower() or (row.get('email') and needle in row['email'].lower()):
            out.append(row)
        if len(out) >= limit:
            break
    return out


def get_employee(settings: Settings, employee_id: int) -> dict | None:
    _maybe_refresh(settings)
    with _lock:
        return _cache.get(employee_id)


def cache_status() -> dict:
    with _lock:
        return {
            'employee_cache_ok': bool(_cache),
            'employee_cache_size': len(_cache),
            'employee_cache_last_refresh_epoch': _last_refresh_epoch,
            'employee_cache_last_error': _last_error,
        }
