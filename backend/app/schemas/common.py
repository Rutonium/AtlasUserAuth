from pydantic import BaseModel


class HealthResponse(BaseModel):
    ok: bool
    service: str


class ApiHealthResponse(BaseModel):
    ok: bool
    service: str
    db_ok: bool
    employee_cache_ok: bool
    employee_cache_size: int
    employee_cache_last_refresh_epoch: int | None = None
    employee_cache_last_error: str | None = None
