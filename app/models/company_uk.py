import uuid
from sqlalchemy import String, ForeignKey, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Uuid
from datetime import datetime

from app.db.base import Base


class CompanyUK(Base):
    __tablename__ = "companies_uk"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False)

    company_number: Mapped[str] = mapped_column(String(50), nullable=False)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    company_status: Mapped[str] = mapped_column(String(50), nullable=False)
    registered_office_address: Mapped[dict] = mapped_column(JSON, nullable=True)
    sic_codes: Mapped[list] = mapped_column(JSON, nullable=True)
    vat_number: Mapped[str | None] = mapped_column(String(50))
    eori_number: Mapped[str | None] = mapped_column(String(50))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="company_uk")
