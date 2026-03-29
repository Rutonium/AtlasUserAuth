from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    app_name: str = 'AtlasUserAuth'
    app_env: str = 'dev'
    app_debug: bool = False

    atlas_auth_db_url: str = Field(alias='ATLAS_AUTH_DB_URL')
    atlas_auth_port: int = Field(default=5020, alias='ATLAS_AUTH_PORT')

    session_cookie_name: str = 'atlas_auth_session'
    session_signing_secret: str = Field(alias='SESSION_SIGNING_SECRET')
    session_idle_timeout_seconds: int = Field(default=1800, alias='SESSION_IDLE_TIMEOUT_SECONDS')
    session_absolute_timeout_seconds: int = Field(default=43200, alias='SESSION_ABSOLUTE_TIMEOUT_SECONDS')
    session_cookie_secure: bool = Field(default=True, alias='SESSION_COOKIE_SECURE')
    session_cookie_samesite: str = Field(default='lax', alias='SESSION_COOKIE_SAMESITE')
    session_cookie_domain: str | None = Field(default=None, alias='SESSION_COOKIE_DOMAIN')
    session_cookie_path: str = Field(default='/', alias='SESSION_COOKIE_PATH')

    csrf_header_name: str = Field(default='X-CSRF-Token', alias='CSRF_HEADER_NAME')

    local_admin_employee_id: str = Field(default='0', alias='LOCAL_ADMIN_EMPLOYEE_ID')
    local_admin_password: str = Field(alias='LOCAL_ADMIN_PASSWORD')
    local_admin_name: str = Field(default='Local Admin', alias='LOCAL_ADMIN_NAME')

    cors_allow_origins: str = Field(default='', alias='CORS_ALLOW_ORIGINS')
    cors_allow_credentials: bool = Field(default=True, alias='CORS_ALLOW_CREDENTIALS')

    employee_api_base_url: str = Field(alias='EMPLOYEE_API_BASE_URL')
    employee_api_token: str = Field(alias='EMPLOYEE_API_TOKEN')
    employee_api_auth_header: str = Field(default='Authorization', alias='EMPLOYEE_API_AUTH_HEADER')
    employee_api_auth_scheme: str = Field(default='', alias='EMPLOYEE_API_AUTH_SCHEME')
    employee_api_timeout_seconds: int = Field(default=20, alias='EMPLOYEE_API_TIMEOUT_SECONDS')
    employee_cache_ttl_seconds: int = Field(default=300, alias='EMPLOYEE_CACHE_TTL_SECONDS')

    auth_attempt_window_seconds: int = Field(default=300, alias='AUTH_ATTEMPT_WINDOW_SECONDS')
    auth_max_attempts_per_ip: int = Field(default=50, alias='AUTH_MAX_ATTEMPTS_PER_IP')
    auth_max_attempts_per_account: int = Field(default=8, alias='AUTH_MAX_ATTEMPTS_PER_ACCOUNT')
    auth_lockout_seconds: int = Field(default=900, alias='AUTH_LOCKOUT_SECONDS')


@lru_cache
def get_settings() -> Settings:
    return Settings()
