from pydantic import BaseModel


class EmployeeItem(BaseModel):
    employee_id: int
    name: str
    initials: str | None = None
    email: str | None = None
    department_code: str | None = None
