import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Uuid

from app.db.base import Base
from app.models.enums import PlanEnum, AccountTypeEnum, StatusEnum, AuthProviderEnum


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    plan: Mapped[PlanEnum] = mapped_column(Enum(PlanEnum), default=PlanEnum.free, nullable=False)
    account_type: Mapped[AccountTypeEnum] = mapped_column(Enum(AccountTypeEnum), default=AccountTypeEnum.free, nullable=False)
    status: Mapped[StatusEnum] = mapped_column(Enum(StatusEnum), default=StatusEnum.active, nullable=False)
    auth_provider: Mapped[AuthProviderEnum] = mapped_column(Enum(AuthProviderEnum), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    company_uk = relationship("CompanyUK", back_populates="user", uselist=False)
    memberships = relationship("TeamMembership", back_populates="user")
    shipments_created = relationship("Shipment", back_populates="created_by")
