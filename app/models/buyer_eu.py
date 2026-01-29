import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Uuid

from app.db.base import Base


class BuyerEU(Base):
    __tablename__ = "buyers_eu"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shipment_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("shipments.id"), unique=True, nullable=False)

    country_code: Mapped[str] = mapped_column(String(5), nullable=False)
    vat_number: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str | None] = mapped_column(String(255))
    address: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_vat_valid: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    shipment = relationship("Shipment", back_populates="buyer_eu")
