from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    employee_id: str = Field(min_length=1, max_length=32)
    password: str = Field(min_length=1, max_length=256)


class LoginResponse(BaseModel):
    ok: bool
    message: str


class MeResponse(BaseModel):
    authenticated: bool
    employee_id: int | None = None
    name: str | None = None
    email: str | None = None
    is_admin: bool = False
    app_key: str | None = None
    role: str | None = None
    access_level: int | None = None
    access_label: str | None = None
    rights: dict = Field(default_factory=dict)


class LogoutResponse(BaseModel):
    ok: bool
