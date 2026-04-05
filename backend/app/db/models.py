from datetime import datetime
from sqlalchemy import Boolean, DateTime, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from app.core.settings import get_settings

settings = get_settings()
DB_SCHEMA = None if settings.atlas_auth_db_url.startswith('sqlite') else 'dbo'


class Base(DeclarativeBase):
    pass


class AtlasUser(Base):
    __tablename__ = 'AtlasUsers'
    if DB_SCHEMA:
        __table_args__ = {'schema': DB_SCHEMA}

    EmployeeID: Mapped[int] = mapped_column(Integer, primary_key=True)
    AssetManagementRole: Mapped[str | None] = mapped_column(String(50), nullable=True)
    AssetManagementRights: Mapped[str | None] = mapped_column(Text, nullable=True)
    DrawingExtractorRole: Mapped[str | None] = mapped_column(String(50), nullable=True)
    DrawingExtractorRights: Mapped[str | None] = mapped_column(Text, nullable=True)
    PasswordHash: Mapped[str | None] = mapped_column(String(512), nullable=True)
    PasswordSalt: Mapped[str | None] = mapped_column(String(255), nullable=True)
    IsActive: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default='1')
    UpdatedAt: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, server_default=func.getdate(), onupdate=func.getdate())


class AtlasAppAccess(Base):
    __tablename__ = 'AtlasAppAccess'
    if DB_SCHEMA:
        __table_args__ = (UniqueConstraint('EmployeeID', 'AppKey', name='UQ_AtlasAppAccess_Employee_App'), {'schema': DB_SCHEMA})
    else:
        __table_args__ = (UniqueConstraint('EmployeeID', 'AppKey', name='UQ_AtlasAppAccess_Employee_App'),)

    Id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    EmployeeID: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    AppKey: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    Role: Mapped[str] = mapped_column(String(100), nullable=False, server_default='user')
    AccessLevel: Mapped[int] = mapped_column(Integer, nullable=False, server_default='1')
    AccessLabel: Mapped[str | None] = mapped_column(String(100), nullable=True)
    RightsJson: Mapped[str] = mapped_column(Text, nullable=False, server_default='{}')
    IsActive: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default='1')
    CreatedAt: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.getdate())
    UpdatedAt: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.getdate(), onupdate=func.getdate())


class AtlasSession(Base):
    __tablename__ = 'AtlasSessions'
    if DB_SCHEMA:
        __table_args__ = {'schema': DB_SCHEMA}

    SessionId: Mapped[str] = mapped_column(String(128), primary_key=True)
    EmployeeID: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    CreatedAtEpoch: Mapped[int] = mapped_column(Integer, nullable=False)
    LastSeenAtEpoch: Mapped[int] = mapped_column(Integer, nullable=False)
    CsrfToken: Mapped[str] = mapped_column(String(128), nullable=False)


class AtlasAppRightDefinition(Base):
    __tablename__ = 'AtlasAppRightDefinitions'
    if DB_SCHEMA:
        __table_args__ = (UniqueConstraint('AppKey', 'RightKey', name='UQ_AtlasAppRightDefinitions_App_Right'), {'schema': DB_SCHEMA})
    else:
        __table_args__ = (UniqueConstraint('AppKey', 'RightKey', name='UQ_AtlasAppRightDefinitions_App_Right'),)

    Id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    AppKey: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    RightKey: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    Level1: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default='0')
    Level2: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default='0')
    Level3: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default='0')
    Level4: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default='0')
    Level5: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default='0')
    CreatedAt: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.getdate())
    UpdatedAt: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.getdate(), onupdate=func.getdate())
