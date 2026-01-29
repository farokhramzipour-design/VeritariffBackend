import uuid
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Uuid

from app.db.base import Base


class ShipmentForwarder(Base):
    __tablename__ = "shipment_forwarders"

    shipment_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("shipments.id"), primary_key=True)
    team_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("teams.id"), primary_key=True)

    shipment = relationship("Shipment", back_populates="forwarders")
    team = relationship("Team", back_populates="forwarder_assignments")
