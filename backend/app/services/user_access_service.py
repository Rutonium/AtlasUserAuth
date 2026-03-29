import json
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from app.core.settings import get_settings
from app.db.models import AtlasAppAccess, DB_SCHEMA

_USERS_TABLE = f"{DB_SCHEMA}.AtlasUsers" if DB_SCHEMA else "AtlasUsers"
_IS_SQLITE = get_settings().atlas_auth_db_url.startswith("sqlite")


def get_user_by_employee_id(db: Session, employee_id: int) -> dict | None:
    if _IS_SQLITE:
        stmt = text(
            f"""
            SELECT EmployeeID, COALESCE(IsActive, 1) AS IsActive
            FROM {_USERS_TABLE}
            WHERE EmployeeID = :employee_id
            LIMIT 1
            """
        )
    else:
        stmt = text(
            f"""
            SELECT TOP 1 EmployeeID, ISNULL(IsActive, 1) AS IsActive
            FROM {_USERS_TABLE}
            WHERE EmployeeID = :employee_id
            """
        )
    row = db.execute(
        stmt,
        {"employee_id": employee_id},
    ).mappings().first()
    return dict(row) if row else None


def list_users(db: Session, limit: int = 200) -> list[dict]:
    safe_limit = int(limit)
    # Primary list source is AtlasAppAccess because provisioning and rights
    # management are app-access driven.
    if _IS_SQLITE:
        access_stmt = text(
            f"""
            SELECT EmployeeID, 1 AS IsActive
            FROM {DB_SCHEMA + '.' if DB_SCHEMA else ''}AtlasAppAccess
            GROUP BY EmployeeID
            ORDER BY EmployeeID ASC
            LIMIT {safe_limit}
            """
        )
    else:
        access_stmt = text(
            f"""
            SELECT TOP {safe_limit} EmployeeID, 1 AS IsActive
            FROM {DB_SCHEMA + '.' if DB_SCHEMA else ''}AtlasAppAccess
            GROUP BY EmployeeID
            ORDER BY EmployeeID ASC
            """
        )
    access_rows = db.execute(access_stmt).mappings().all()

    # Merge AtlasUsers rows when present (keeps IsActive when that table is in use).
    user_rows: list[dict] = []
    try:
        if _IS_SQLITE:
            user_stmt = text(
                f"""
                SELECT EmployeeID, COALESCE(IsActive, 1) AS IsActive
                FROM {_USERS_TABLE}
                ORDER BY EmployeeID ASC
                LIMIT {safe_limit}
                """
            )
        else:
            user_stmt = text(
                f"""
                SELECT TOP {safe_limit} EmployeeID, ISNULL(IsActive, 1) AS IsActive
                FROM {_USERS_TABLE}
                ORDER BY EmployeeID ASC
                """
            )
        user_rows = [dict(r) for r in db.execute(user_stmt).mappings().all()]
    except Exception:
        # AtlasUsers can have varying schema per environment; keep admin functional.
        user_rows = []

    merged: dict[int, dict] = {}
    for row in access_rows:
        employee_id = int(row.get("EmployeeID") or 0)
        if employee_id > 0:
            merged[employee_id] = {"EmployeeID": employee_id, "IsActive": True}
    for row in user_rows:
        employee_id = int(row.get("EmployeeID") or 0)
        if employee_id <= 0:
            continue
        merged[employee_id] = {
            "EmployeeID": employee_id,
            "IsActive": bool(row.get("IsActive", True)),
        }
    return list(merged.values())[:safe_limit]


def ensure_user_exists(db: Session, employee_id: int, is_active: bool = True) -> None:
    existing = get_user_by_employee_id(db, employee_id)
    if existing:
        return
    # AtlasUsers schema differs across environments; some SQL Server versions
    # define EmployeeID as IDENTITY, which rejects explicit inserts.
    # Provisioning works via AtlasAppAccess, so we treat AtlasUsers insert
    # as best-effort only.
    try:
        db.execute(
            text(
                f"""
                INSERT INTO {_USERS_TABLE} (EmployeeID, IsActive)
                VALUES (:employee_id, :is_active)
                """
            ),
            {"employee_id": employee_id, "is_active": 1 if is_active else 0},
        )
        db.commit()
    except Exception:
        db.rollback()


def is_admin_user(db: Session, employee_id: int) -> bool:
    access = db.scalar(
        select(AtlasAppAccess).where(
            AtlasAppAccess.EmployeeID == employee_id,
            AtlasAppAccess.AppKey == "atlas_user_auth_admin",
            AtlasAppAccess.IsActive == True,
            AtlasAppAccess.Role.in_(["admin", "super_admin"]),
        )
    )
    return access is not None


def get_app_access(db: Session, *, employee_id: int, app_key: str) -> AtlasAppAccess | None:
    return db.scalar(
        select(AtlasAppAccess).where(
            AtlasAppAccess.EmployeeID == employee_id,
            AtlasAppAccess.AppKey == app_key,
            AtlasAppAccess.IsActive == True,
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
