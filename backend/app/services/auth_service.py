import base64
from dataclasses import dataclass
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.security import new_salt, pbkdf2_hash, verify_pbkdf2
from app.core.settings import Settings
from app.db.models import AtlasUser


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
    user = db.scalar(select(AtlasUser).where(AtlasUser.EmployeeID == employee_id))
    if not user:
        raise ValueError('User not found')
    salt = new_salt()
    password_hash = pbkdf2_hash(new_password, base64.b64decode(salt))
    user.PasswordSalt = salt
    user.PasswordHash = password_hash
    db.add(user)
    db.commit()
