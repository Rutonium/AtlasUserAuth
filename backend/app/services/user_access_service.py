import json
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.models import AtlasAppAccess, AtlasUser


def get_user_by_employee_id(db: Session, employee_id: int) -> AtlasUser | None:
    return db.scalar(select(AtlasUser).where(AtlasUser.EmployeeID == employee_id))


def list_users(db: Session, limit: int = 200) -> list[AtlasUser]:
    return list(db.scalars(select(AtlasUser).order_by(AtlasUser.EmployeeID).limit(limit)))


def get_app_access(db: Session, *, employee_id: int, app_key: str) -> AtlasAppAccess | None:
    return db.scalar(
        select(AtlasAppAccess).where(
            AtlasAppAccess.EmployeeID == employee_id,
            AtlasAppAccess.AppKey == app_key,
            AtlasAppAccess.IsActive.is_(True),
        )
    )


def upsert_app_access(db: Session, *, employee_id: int, app_key: str, role: str, rights: dict, is_active: bool) -> AtlasAppAccess:
    existing = db.scalar(
        select(AtlasAppAccess).where(AtlasAppAccess.EmployeeID == employee_id, AtlasAppAccess.AppKey == app_key)
    )
    rights_json = json.dumps(rights, ensure_ascii=True)
    if existing:
        existing.Role = role
        existing.RightsJson = rights_json
        existing.IsActive = is_active
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return existing

    row = AtlasAppAccess(
        EmployeeID=employee_id,
        AppKey=app_key,
        Role=role,
        RightsJson=rights_json,
        IsActive=is_active,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
