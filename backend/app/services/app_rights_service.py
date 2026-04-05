from sqlalchemy import select, text
from sqlalchemy.orm import Session
from app.db.models import AtlasAppRightDefinition, DB_SCHEMA
from app.services.app_catalog_service import DEFAULT_RIGHTS_DEFINITIONS, KNOWN_APP_KEYS
from app.services.user_access_service import list_distinct_apps

_RIGHTS_TABLE = f"{DB_SCHEMA + '.' if DB_SCHEMA else ''}AtlasAppRightDefinitions"

LEVEL_KEYS = ["1", "2", "3", "4", "5"]


def _row_levels(row: AtlasAppRightDefinition) -> dict[str, bool]:
    return {
        "1": bool(row.Level1),
        "2": bool(row.Level2),
        "3": bool(row.Level3),
        "4": bool(row.Level4),
        "5": bool(row.Level5),
    }


def list_apps(db: Session) -> list[str]:
    access_apps = [str(row.get("AppKey") or "").strip() for row in list_distinct_apps(db)]
    rights_apps = [
        str(row[0]).strip()
        for row in db.execute(text(f"SELECT DISTINCT AppKey FROM {_RIGHTS_TABLE} ORDER BY AppKey ASC")).all()
        if row and str(row[0]).strip()
    ]
    return sorted({app for app in [*KNOWN_APP_KEYS, *access_apps, *rights_apps] if app})


def get_matrix(db: Session, *, app_key: str) -> list[dict]:
    rows = db.scalars(
        select(AtlasAppRightDefinition)
        .where(AtlasAppRightDefinition.AppKey == app_key)
        .order_by(AtlasAppRightDefinition.RightKey.asc())
    ).all()
    return [{"right_key": row.RightKey, "levels": _row_levels(row)} for row in rows]


def upsert_right(db: Session, *, app_key: str, right_key: str, levels: dict[str, bool]) -> AtlasAppRightDefinition:
    normalized_levels = {key: bool(levels.get(key, False)) for key in LEVEL_KEYS}
    row = db.scalar(
        select(AtlasAppRightDefinition).where(
            AtlasAppRightDefinition.AppKey == app_key,
            AtlasAppRightDefinition.RightKey == right_key,
        )
    )
    if not row:
        row = AtlasAppRightDefinition(AppKey=app_key, RightKey=right_key)
    row.Level1 = normalized_levels["1"]
    row.Level2 = normalized_levels["2"]
    row.Level3 = normalized_levels["3"]
    row.Level4 = normalized_levels["4"]
    row.Level5 = normalized_levels["5"]
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def delete_right(db: Session, *, app_key: str, right_key: str) -> bool:
    row = db.scalar(
        select(AtlasAppRightDefinition).where(
            AtlasAppRightDefinition.AppKey == app_key,
            AtlasAppRightDefinition.RightKey == right_key,
        )
    )
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True


def ensure_default_right_definitions(db: Session) -> None:
    changed = False
    for app_key, rights in DEFAULT_RIGHTS_DEFINITIONS.items():
        for right_key, levels in rights.items():
            normalized_levels = {key: bool(levels.get(key, False)) for key in LEVEL_KEYS}
            row = db.scalar(
                select(AtlasAppRightDefinition).where(
                    AtlasAppRightDefinition.AppKey == app_key,
                    AtlasAppRightDefinition.RightKey == right_key,
                )
            )
            if not row:
                row = AtlasAppRightDefinition(AppKey=app_key, RightKey=right_key)
                changed = True
            previous = _row_levels(row)
            row.Level1 = normalized_levels["1"]
            row.Level2 = normalized_levels["2"]
            row.Level3 = normalized_levels["3"]
            row.Level4 = normalized_levels["4"]
            row.Level5 = normalized_levels["5"]
            if previous != normalized_levels:
                changed = True
            db.add(row)
    if changed:
        db.commit()
