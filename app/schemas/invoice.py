from datetime import datetime
from typing import Any
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


class UploadResponse(BaseModel):
    upload_id: UUID


class ExtractResponse(BaseModel):
    draft_id: UUID
    status: str


class LineItemExtract(BaseModel):
    description: str
    quantity: float | None = None
    unit_price: float | None = None
    tax_rate: float | None = None
    line_total: float | None = None
    sku: str | None = None
    confidence: float | None = None


class ExtractedInvoicePayload(BaseModel):
    vendor_name: str | None = None
    invoice_number: str | None = None
    invoice_date: str | None = None
    due_date: str | None = None
    currency: str | None = None
    subtotal: float | None = None
    tax: float | None = None
    total: float | None = None
    line_items: list[LineItemExtract] = Field(default_factory=list)
    field_confidence: dict[str, float] = Field(default_factory=dict)


class DraftInvoiceOut(BaseModel):
    id: UUID
    upload_id: UUID
    status: str
    extracted_payload: ExtractedInvoicePayload | None = None
    confirmed_payload: dict[str, Any] | None = None
    confidence: float | None = None
    warnings: list[str] = Field(default_factory=list)
    raw_text_excerpt: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConfirmLineItem(BaseModel):
    description: str
    quantity: float
    unit_price: float | None = None
    tax_rate: float | None = None
    line_total: float | None = None
    sku: str | None = None


class ConfirmInvoiceRequest(BaseModel):
    vendor_name: str | None = None
    invoice_number: str | None = None
    invoice_date: str
    due_date: str | None = None
    currency: str
    subtotal: float | None = None
    tax: float | None = None
    total: float | None = None
    line_items: list[ConfirmLineItem]


class InvoiceItemOut(BaseModel):
    id: UUID
    description: str
    sku: str | None = None
    quantity: float
    unit_price: float | None = None
    tax_rate: float | None = None
    line_total: float | None = None
    sort_order: int

    model_config = ConfigDict(from_attributes=True)


class InvoiceOut(BaseModel):
    id: UUID
    vendor_name: str | None = None
    invoice_number: str | None = None
    invoice_date: str | None = None
    due_date: str | None = None
    currency: str
    subtotal: float | None = None
    tax: float | None = None
    total: float | None = None
    created_at: datetime
    items: list[InvoiceItemOut] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class ListResponse(BaseModel):
    items: list[Any]
    total: int
    limit: int
    offset: int
