from pydantic import BaseModel, Field


class UserSummary(BaseModel):
    employee_id: int
    name: str | None = None
    email: str | None = None
    is_admin: bool
    is_active: bool
    app_access_count: int = 0
    active_app_count: int = 0
    app_keys: list[str] = Field(default_factory=list)


class AppAccessSummary(BaseModel):
    app_key: str
    role: str
    access_level: int = Field(ge=1, le=5)
    access_label: str | None = None
    rights: dict = Field(default_factory=dict)
    is_active: bool = True


class UserDetail(UserSummary):
    access_entries: list[AppAccessSummary] = Field(default_factory=list)


class DashboardAppMetric(BaseModel):
    app_key: str
    user_count: int


class DashboardSummary(BaseModel):
    total_users: int
    admin_users: int
    total_access_entries: int
    active_access_entries: int
    unique_apps: int
    top_apps: list[DashboardAppMetric] = Field(default_factory=list)


class UserAccessUpdateRequest(BaseModel):
    role: str = Field(min_length=1, max_length=100)
    access_level: int = Field(default=1, ge=1, le=5)
    access_label: str | None = Field(default=None, max_length=100)
    rights: dict = Field(default_factory=dict)
    is_active: bool = True


class ProvisionByEmployeeIdRequest(BaseModel):
    employee_id: str = Field(min_length=1, max_length=32)
    make_admin: bool = False
    initial_role: str = 'user'
    initial_access_level: int = Field(default=1, ge=1, le=5)
    initial_access_label: str | None = Field(default=None, max_length=100)
    app_key: str = Field(min_length=1, max_length=100)


class ResetCredentialRequest(BaseModel):
    new_password: str = Field(min_length=8, max_length=256)
