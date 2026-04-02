import json
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from app.core.settings import get_settings
from app.db.models import AtlasAppAccess, DB_SCHEMA

_USERS_TABLE = f"{DB_SCHEMA}.AtlasUsers" if DB_SCHEMA else "AtlasUsers"
_IS_SQLITE = get_settings().atlas_auth_db_url.startswith("sqlite")
_APP_ACCESS_TABLE = f"{DB_SCHEMA + '.' if DB_SCHEMA else ''}AtlasAppAccess"

ACCESS_LEVEL_LABELS = {
    1: "Viewer",
    2: "Contributor",
    3: "Specialist",
    4: "Manager",
    5: "Owner",
}


def default_access_label(level: int) -> str:
    return ACCESS_LEVEL_LABELS.get(int(level), "Custom")


def normalize_access_level(level: int | None) -> int:
    try:
        value = int(level or 1)
    except (TypeError, ValueError):
        value = 1
    return min(5, max(1, value))


def normalize_access_label(level: int, access_label: str | None) -> str:
    cleaned = (access_label or "").strip()
    return cleaned or default_access_label(level)


def parse_rights_json(raw: str | None) -> dict:
    try:
        value = json.loads(raw or "{}")
    except Exception:
        value = {}
    return value if isinstance(value, dict) else {}


def serialize_access_row(row: AtlasAppAccess) -> dict:
    level = normalize_access_level(getattr(row, "AccessLevel", 1))
    label = normalize_access_label(level, getattr(row, "AccessLabel", None))
    return {
        "app_key": row.AppKey,
        "role": row.Role,
        "access_level": level,
        "access_label": label,
        "rights": parse_rights_json(row.RightsJson),
        "is_active": bool(row.IsActive),
    }


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
            SELECT EmployeeID, AppKey, COALESCE(IsActive, 1) AS IsActive
            FROM {_APP_ACCESS_TABLE}
            ORDER BY EmployeeID ASC
            """
        )
    else:
        access_stmt = text(
            f"""
            SELECT EmployeeID, AppKey, ISNULL(IsActive, 1) AS IsActive
            FROM {_APP_ACCESS_TABLE}
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
    access_by_employee: dict[int, list[dict]] = {}
    for row in access_rows:
        employee_id = int(row.get("EmployeeID") or 0)
        if employee_id > 0:
            access_by_employee.setdefault(employee_id, []).append(dict(row))
            merged[employee_id] = {"EmployeeID": employee_id, "IsActive": True}
    for row in user_rows:
        employee_id = int(row.get("EmployeeID") or 0)
        if employee_id <= 0:
            continue
        merged[employee_id] = {
            "EmployeeID": employee_id,
            "IsActive": bool(row.get("IsActive", True)),
        }
    output: list[dict] = []
    for employee_id in sorted(merged.keys())[:safe_limit]:
        app_rows = access_by_employee.get(employee_id, [])
        app_keys = sorted({str(r.get("AppKey") or "") for r in app_rows if str(r.get("AppKey") or "").strip()})
        output.append(
            {
                "EmployeeID": employee_id,
                "IsActive": bool(merged[employee_id].get("IsActive", True)),
                "AppAccessCount": len(app_rows),
                "ActiveAppCount": sum(1 for r in app_rows if bool(r.get("IsActive", True))),
                "AppKeys": app_keys,
            }
        )
    return output


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


def list_user_access_entries(db: Session, *, employee_id: int) -> list[AtlasAppAccess]:
    rows = db.scalars(
        select(AtlasAppAccess).where(AtlasAppAccess.EmployeeID == employee_id).order_by(AtlasAppAccess.AppKey.asc())
    ).all()
    return list(rows)


def get_user_detail(db: Session, *, employee_id: int) -> dict | None:
    user = get_user_by_employee_id(db, employee_id)
    access_entries = list_user_access_entries(db, employee_id=employee_id)
    if not user and not access_entries:
        return None
    app_keys = [entry.AppKey for entry in access_entries]
    return {
        "EmployeeID": employee_id,
        "IsActive": bool((user or {}).get("IsActive", True)),
        "AppAccessCount": len(access_entries),
        "ActiveAppCount": sum(1 for entry in access_entries if bool(entry.IsActive)),
        "AppKeys": sorted(set(app_keys)),
        "AccessEntries": [serialize_access_row(entry) for entry in access_entries],
    }


def dashboard_summary(db: Session) -> dict:
    try:
        user_ids = {int(row[0]) for row in db.execute(text(f"SELECT EmployeeID FROM {_USERS_TABLE}")).all() if row and row[0] is not None}
    except Exception:
        user_ids = set()
    try:
        access_rows = db.execute(
            text(
                f"""
                SELECT EmployeeID, AppKey, COALESCE(IsActive, 1) AS IsActive
                FROM {_APP_ACCESS_TABLE}
                """
                if _IS_SQLITE
                else f"""
                SELECT EmployeeID, AppKey, ISNULL(IsActive, 1) AS IsActive
                FROM {_APP_ACCESS_TABLE}
                """
            )
        ).mappings().all()
    except Exception:
        access_rows = []
    access_ids = {int(row.get("EmployeeID") or 0) for row in access_rows if int(row.get("EmployeeID") or 0) > 0}
    all_user_ids = user_ids | access_ids
    app_counts: dict[str, int] = {}
    active_access_entries = 0
    for row in access_rows:
        app_key = str(row.get("AppKey") or "").strip()
        if not app_key:
            continue
        if bool(row.get("IsActive", True)):
            active_access_entries += 1
        app_counts[app_key] = app_counts.get(app_key, 0) + 1
    top_apps = [
        {"app_key": app_key, "user_count": count}
        for app_key, count in sorted(app_counts.items(), key=lambda item: (-item[1], item[0]))[:6]
    ]
    admin_users = sum(1 for employee_id in all_user_ids if is_admin_user(db, employee_id))
    return {
        "total_users": len(all_user_ids),
        "admin_users": admin_users,
        "total_access_entries": len(access_rows),
        "active_access_entries": active_access_entries,
        "unique_apps": len(app_counts),
        "top_apps": top_apps,
    }


def upsert_app_access(
    db: Session,
    *,
    employee_id: int,
    app_key: str,
    role: str,
    access_level: int,
    access_label: str | None,
    rights: dict,
    is_active: bool,
) -> AtlasAppAccess:
    existing = db.scalar(
        select(AtlasAppAccess).where(AtlasAppAccess.EmployeeID == employee_id, AtlasAppAccess.AppKey == app_key)
    )
    normalized_level = normalize_access_level(access_level)
    normalized_label = normalize_access_label(normalized_level, access_label)
    rights_json = json.dumps(rights, ensure_ascii=True)
    if existing:
        existing.Role = role
        existing.AccessLevel = normalized_level
        existing.AccessLabel = normalized_label
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
        AccessLevel=normalized_level,
        AccessLabel=normalized_label,
        RightsJson=rights_json,
        IsActive=is_active,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
