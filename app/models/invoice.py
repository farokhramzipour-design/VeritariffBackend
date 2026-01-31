import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Numeric, JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Uuid

from app.db.base import Base


class UploadedDocument(Base):
    __tablename__ = "uploaded_documents"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Numeric(20, 0), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class DraftInvoice(Base):
    __tablename__ = "draft_invoices"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    upload_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("uploaded_documents.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    extracted_payload_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    confirmed_payload_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Numeric(4, 3), nullable=True)
    warnings_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    raw_text_excerpt: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    confirmed_invoice_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("invoices.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    vendor_name: Mapped[str | None] = mapped_column(String(255))
    invoice_number: Mapped[str | None] = mapped_column(String(100))
    invoice_date: Mapped[str | None] = mapped_column(String(20))
    due_date: Mapped[str | None] = mapped_column(String(20))
    currency: Mapped[str] = mapped_column(String(10), nullable=False)
    subtotal: Mapped[float | None] = mapped_column(Numeric(14, 2))
    tax: Mapped[float | None] = mapped_column(Numeric(14, 2))
    total: Mapped[float | None] = mapped_column(Numeric(14, 2))
    source_upload_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("uploaded_documents.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    items = relationship("InvoiceItem", back_populates="invoice")


class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("invoices.id"), nullable=False)
    description: Mapped[str] = mapped_column(String(512), nullable=False)
    sku: Mapped[str | None] = mapped_column(String(64))
    quantity: Mapped[float] = mapped_column(Numeric(12, 3), nullable=False)
    unit_price: Mapped[float | None] = mapped_column(Numeric(12, 2))
    tax_rate: Mapped[float | None] = mapped_column(Numeric(6, 3))
    line_total: Mapped[float | None] = mapped_column(Numeric(14, 2))
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)

    invoice = relationship("Invoice", back_populates="items")
