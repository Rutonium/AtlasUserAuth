from pydantic import BaseModel, Field


class UserSummary(BaseModel):
    employee_id: int
    name: str | None = None
    email: str | None = None
    is_admin: bool
    is_active: bool


class UserAccessUpdateRequest(BaseModel):
    role: str = Field(min_length=1, max_length=100)
    rights: dict = Field(default_factory=dict)
    is_active: bool = True


class ProvisionByEmployeeIdRequest(BaseModel):
    employee_id: str = Field(min_length=1, max_length=32)
    make_admin: bool = False
    initial_role: str = 'user'
    app_key: str = Field(min_length=1, max_length=100)


class ResetCredentialRequest(BaseModel):
    new_password: str = Field(min_length=8, max_length=256)
