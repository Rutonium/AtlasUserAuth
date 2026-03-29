import base64
from dataclasses import dataclass
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from app.core.security import new_salt, pbkdf2_hash, verify_pbkdf2
from app.core.settings import Settings
from app.db.models import AtlasUser, DB_SCHEMA


@dataclass
class AuthResult:
    ok: bool
    employee_id: int | None = None
    message: str = 'Invalid credentials'


def normalize_employee_id(value: str) -> str:
    cleaned = ''.join(ch for ch in value if ch.isdigit())
    if not cleaned:
        return ''
    return str(int(cleaned))


def verify_credentials(db: Session, *, employee_id_raw: str, password: str, settings: Settings) -> AuthResult:
    employee_id_str = normalize_employee_id(employee_id_raw)
    if not employee_id_str:
        return AuthResult(ok=False)

    # Break-glass local admin from env.
    if employee_id_str == settings.local_admin_employee_id and password == settings.local_admin_password:
        return AuthResult(ok=True, employee_id=int(settings.local_admin_employee_id), message='Authenticated')

    user = db.scalar(select(AtlasUser).where(AtlasUser.EmployeeID == int(employee_id_str)))
    if not user or not user.IsActive or not user.PasswordHash or not user.PasswordSalt:
        return AuthResult(ok=False)

    if not verify_pbkdf2(password, user.PasswordHash, user.PasswordSalt):
        return AuthResult(ok=False)

    return AuthResult(ok=True, employee_id=user.EmployeeID, message='Authenticated')


def reset_credential(db: Session, *, employee_id: int, new_password: str) -> None:
    salt = new_salt()
    password_hash = pbkdf2_hash(new_password, base64.b64decode(salt))
    users_table = f"{DB_SCHEMA}.AtlasUsers" if DB_SCHEMA else "AtlasUsers"

    # Strategy 1: update existing row.
    update_stmt = text(
        f"""
        UPDATE {users_table}
        SET PasswordSalt = :salt,
            PasswordHash = :password_hash,
            IsActive = 1
        WHERE EmployeeID = :employee_id
        """
    )
    result = db.execute(
        update_stmt,
        {"employee_id": employee_id, "salt": salt, "password_hash": password_hash},
    )
    if int(result.rowcount or 0) > 0:
        db.commit()
        return

    # Strategy 2: insert new row.
    try:
        db.execute(
            text(
                f"""
                INSERT INTO {users_table} (EmployeeID, PasswordSalt, PasswordHash, IsActive)
                VALUES (:employee_id, :salt, :password_hash, 1)
                """
            ),
            {"employee_id": employee_id, "salt": salt, "password_hash": password_hash},
        )
        db.commit()
        return
    except Exception:
        db.rollback()

    # Strategy 3 (SQL Server identity compatibility): explicit insert with IDENTITY_INSERT.
    if (db.get_bind().dialect.name or "").startswith("mssql"):
        db.execute(text(f"SET IDENTITY_INSERT {users_table} ON"))
        try:
            db.execute(
                text(
                    f"""
                    INSERT INTO {users_table} (EmployeeID, PasswordSalt, PasswordHash, IsActive)
                    VALUES (:employee_id, :salt, :password_hash, 1)
                    """
                ),
                {"employee_id": employee_id, "salt": salt, "password_hash": password_hash},
            )
            db.commit()
            return
        except Exception:
            db.rollback()
        finally:
            try:
                db.execute(text(f"SET IDENTITY_INSERT {users_table} OFF"))
                db.commit()
            except Exception:
                db.rollback()

    raise ValueError("Unable to reset credential for this user")
