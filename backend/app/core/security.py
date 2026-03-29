import base64
import hashlib
import hmac
import os
from datetime import datetime, timezone
from itsdangerous import BadSignature, URLSafeSerializer


def pbkdf2_hash(password: str, salt: bytes, iterations: int = 200_000) -> str:
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, iterations)
    return base64.b64encode(dk).decode('ascii')


def verify_pbkdf2(password: str, expected_hash_b64: str, salt_b64_or_text: str) -> bool:
    try:
        try:
            salt = base64.b64decode(salt_b64_or_text)
        except Exception:
            salt = salt_b64_or_text.encode('utf-8')
        calculated = pbkdf2_hash(password, salt)
        return hmac.compare_digest(calculated, expected_hash_b64)
    except Exception:
        return False


def new_salt() -> str:
    return base64.b64encode(os.urandom(16)).decode('ascii')


def sign_value(secret: str, payload: dict) -> str:
    s = URLSafeSerializer(secret_key=secret, salt='atlas-auth-cookie')
    return s.dumps(payload)


def unsign_value(secret: str, token: str) -> dict | None:
    s = URLSafeSerializer(secret_key=secret, salt='atlas-auth-cookie')
    try:
        data = s.loads(token)
        if isinstance(data, dict):
            return data
        return None
    except BadSignature:
        return None


def now_epoch() -> int:
    return int(datetime.now(timezone.utc).timestamp())
