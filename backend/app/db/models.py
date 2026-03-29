from datetime import datetime
from sqlalchemy import Boolean, DateTime, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class AtlasUser(Base):
    __tablename__ = 'AtlasUsers'
    __table_args__ = {'schema': 'dbo'}

    EmployeeID: Mapped[int] = mapped_column(Integer, primary_key=True)
    Name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    Initials: Mapped[str | None] = mapped_column(String(50), nullable=True)
    EMail: Mapped[str | None] = mapped_column(String(255), nullable=True)
    PasswordHash: Mapped[str | None] = mapped_column(String(512), nullable=True)
    PasswordSalt: Mapped[str | None] = mapped_column(String(255), nullable=True)
    IsActive: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default='1')
    IsAdmin: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default='0')
    UpdatedAt: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.getdate(), onupdate=func.getdate())


class AtlasAppAccess(Base):
    __tablename__ = 'AtlasAppAccess'
    __table_args__ = (UniqueConstraint('EmployeeID', 'AppKey', name='UQ_AtlasAppAccess_Employee_App'), {'schema': 'dbo'})

    Id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    EmployeeID: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    AppKey: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    Role: Mapped[str] = mapped_column(String(100), nullable=False, server_default='user')
    RightsJson: Mapped[str] = mapped_column(Text, nullable=False, server_default='{}')
    IsActive: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default='1')
    CreatedAt: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.getdate())
    UpdatedAt: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.getdate(), onupdate=func.getdate())


class AtlasSession(Base):
    __tablename__ = 'AtlasSessions'
    __table_args__ = {'schema': 'dbo'}

    SessionId: Mapped[str] = mapped_column(String(128), primary_key=True)
    EmployeeID: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    CreatedAtEpoch: Mapped[int] = mapped_column(Integer, nullable=False)
    LastSeenAtEpoch: Mapped[int] = mapped_column(Integer, nullable=False)
    CsrfToken: Mapped[str] = mapped_column(String(128), nullable=False)
