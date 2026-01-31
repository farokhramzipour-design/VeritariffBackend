import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.models import UploadedDocument, DraftInvoice, Invoice, InvoiceItem
from app.schemas.invoice import (
    UploadResponse,
    ExtractResponse,
    DraftInvoiceOut,
    ConfirmInvoiceRequest,
    InvoiceOut,
    ListResponse,
)
from app.services.storage import LocalStorageBackend
from app.services.invoice_extractor import (
    InvoiceExtractor,
    extract_text_from_pdf,
    extract_text_from_docx,
    ocr_fallback,
)
from app.services.llm_client import LLMClient
from app.services.invoice_validator import validate_required_fields, reconcile_totals, validate_quantities

router = APIRouter(prefix="/invoices")

storage = LocalStorageBackend(settings.UPLOAD_DIR)
llm_client = LLMClient(settings.LLM_PROVIDER, model=settings.OPENAI_MODEL)
extractor = InvoiceExtractor(llm_client)

ALLOWED_TYPES = {"application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}


def _validate_upload(file: UploadFile) -> None:
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported file type")


@router.post("/uploads", response_model=UploadResponse)
async def upload_invoice(
    file: UploadFile = File(...),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _validate_upload(file)

    storage_path, sha256, size = await storage.save(file)
    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    if size > max_bytes:
        try:
            import os
            os.remove(storage_path)
        except Exception:
            pass
        raise HTTPException(status_code=400, detail="File too large")

    uploaded = UploadedDocument(
        user_id=user.id,
        filename=file.filename or "upload",
        content_type=file.content_type or "application/octet-stream",
        storage_path=storage_path,
        sha256=sha256,
        size_bytes=size,
    )
    db.add(uploaded)
    await db.commit()
    await db.refresh(uploaded)
    return UploadResponse(upload_id=uploaded.id)


@router.post("/uploads/{upload_id}/extract", response_model=ExtractResponse)
async def extract_invoice(
    upload_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        upload_uuid = uuid.UUID(upload_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid upload id")

    result = await db.execute(select(UploadedDocument).where(UploadedDocument.id == upload_uuid))
    upload = result.scalar_one_or_none()
    if not upload or upload.user_id != user.id:
        raise HTTPException(status_code=404, detail="Upload not found")

    draft = DraftInvoice(
        user_id=user.id,
        upload_id=upload.id,
        status="EXTRACTING",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(draft)
    await db.commit()
    await db.refresh(draft)

    text = ""
    if upload.content_type == "application/pdf":
        text = await extract_text_from_pdf(upload.storage_path)
        if not text.strip():
            text = await ocr_fallback(upload.storage_path)
    else:
        text = await extract_text_from_docx(upload.storage_path)

    raw_excerpt = text[:2000] if text else None
    extracted = await extractor.extract(text or "")
    warnings = extracted.get("warnings") or []
    confidence = extracted.get("confidence_score")

    status = "EXTRACTED"
    if warnings or (confidence is not None and confidence < 0.7):
        status = "NEEDS_REVIEW"

    draft.status = status
    draft.extracted_payload_json = extracted
    draft.warnings_json = warnings
    draft.confidence = confidence
    draft.raw_text_excerpt = raw_excerpt
    draft.updated_at = datetime.utcnow()

    await db.commit()
    return ExtractResponse(draft_id=draft.id, status=draft.status)


@router.get("/drafts/{draft_id}", response_model=DraftInvoiceOut)
async def get_draft(
    draft_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        draft_uuid = uuid.UUID(draft_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid draft id")

    result = await db.execute(select(DraftInvoice).where(DraftInvoice.id == draft_uuid))
    draft = result.scalar_one_or_none()
    if not draft or draft.user_id != user.id:
        raise HTTPException(status_code=404, detail="Draft not found")

    extracted_payload = draft.extracted_payload_json
    return DraftInvoiceOut(
        id=draft.id,
        upload_id=draft.upload_id,
        status=draft.status,
        extracted_payload=extracted_payload,
        confirmed_payload=draft.confirmed_payload_json,
        confidence=float(draft.confidence) if draft.confidence is not None else None,
        warnings=draft.warnings_json or [],
        raw_text_excerpt=draft.raw_text_excerpt,
        created_at=draft.created_at,
        updated_at=draft.updated_at,
    )


@router.post("/drafts/{draft_id}/confirm")
async def confirm_draft(
    draft_id: str,
    payload: ConfirmInvoiceRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        draft_uuid = uuid.UUID(draft_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid draft id")

    result = await db.execute(select(DraftInvoice).where(DraftInvoice.id == draft_uuid))
    draft = result.scalar_one_or_none()
    if not draft or draft.user_id != user.id:
        raise HTTPException(status_code=404, detail="Draft not found")

    if draft.status == "CONFIRMED" and draft.confirmed_invoice_id:
        return {"invoice_id": str(draft.confirmed_invoice_id)}

    payload_dict = payload.model_dump()
    errors = []
    errors.extend(validate_required_fields(payload_dict))
    errors.extend(validate_quantities(payload_dict))
    ok, msg = reconcile_totals(payload_dict)
    if not ok and msg:
        errors.append(msg)

    if errors:
        raise HTTPException(status_code=400, detail={"errors": errors})

    invoice = Invoice(
        user_id=user.id,
        vendor_name=payload.vendor_name,
        invoice_number=payload.invoice_number,
        invoice_date=payload.invoice_date,
        due_date=payload.due_date,
        currency=payload.currency,
        subtotal=payload.subtotal,
        tax=payload.tax,
        total=payload.total,
        source_upload_id=draft.upload_id,
    )
    db.add(invoice)
    await db.commit()
    await db.refresh(invoice)

    items = []
    for idx, item in enumerate(payload.line_items):
        items.append(
            InvoiceItem(
                invoice_id=invoice.id,
                description=item.description,
                sku=item.sku,
                quantity=item.quantity,
                unit_price=item.unit_price,
                tax_rate=item.tax_rate,
                line_total=item.line_total,
                sort_order=idx,
            )
        )
    db.add_all(items)

    draft.status = "CONFIRMED"
    draft.confirmed_payload_json = payload_dict
    draft.confirmed_invoice_id = invoice.id
    draft.updated_at = datetime.utcnow()

    await db.commit()
    return {"invoice_id": str(invoice.id)}


@router.get("/{invoice_id}", response_model=InvoiceOut)
async def get_invoice(
    invoice_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        invoice_uuid = uuid.UUID(invoice_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid invoice id")

    result = await db.execute(select(Invoice).where(Invoice.id == invoice_uuid))
    invoice = result.scalar_one_or_none()
    if not invoice or invoice.user_id != user.id:
        raise HTTPException(status_code=404, detail="Invoice not found")

    result = await db.execute(select(InvoiceItem).where(InvoiceItem.invoice_id == invoice.id).order_by(InvoiceItem.sort_order))
    items = result.scalars().all()

    return InvoiceOut(
        id=invoice.id,
        vendor_name=invoice.vendor_name,
        invoice_number=invoice.invoice_number,
        invoice_date=invoice.invoice_date,
        due_date=invoice.due_date,
        currency=invoice.currency,
        subtotal=float(invoice.subtotal) if invoice.subtotal is not None else None,
        tax=float(invoice.tax) if invoice.tax is not None else None,
        total=float(invoice.total) if invoice.total is not None else None,
        created_at=invoice.created_at,
        items=items,
    )


@router.get("", response_model=ListResponse)
async def list_invoices(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    total_result = await db.execute(select(func.count()).select_from(Invoice).where(Invoice.user_id == user.id))
    total = total_result.scalar_one()
    result = await db.execute(
        select(Invoice).where(Invoice.user_id == user.id).order_by(Invoice.created_at.desc()).limit(limit).offset(offset)
    )
    items = result.scalars().all()
    payload_items = []
    for invoice in items:
        payload_items.append(
            InvoiceOut(
                id=invoice.id,
                vendor_name=invoice.vendor_name,
                invoice_number=invoice.invoice_number,
                invoice_date=invoice.invoice_date,
                due_date=invoice.due_date,
                currency=invoice.currency,
                subtotal=float(invoice.subtotal) if invoice.subtotal is not None else None,
                tax=float(invoice.tax) if invoice.tax is not None else None,
                total=float(invoice.total) if invoice.total is not None else None,
                created_at=invoice.created_at,
                items=[],
            )
        )
    return ListResponse(items=payload_items, total=total, limit=limit, offset=offset)


@router.get("/drafts", response_model=ListResponse)
async def list_drafts(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    total_result = await db.execute(select(func.count()).select_from(DraftInvoice).where(DraftInvoice.user_id == user.id))
    total = total_result.scalar_one()
    result = await db.execute(
        select(DraftInvoice).where(DraftInvoice.user_id == user.id).order_by(DraftInvoice.created_at.desc()).limit(limit).offset(offset)
    )
    items = result.scalars().all()
    payload_items = []
    for draft in items:
        payload_items.append(
            DraftInvoiceOut(
                id=draft.id,
                upload_id=draft.upload_id,
                status=draft.status,
                extracted_payload=draft.extracted_payload_json,
                confirmed_payload=draft.confirmed_payload_json,
                confidence=float(draft.confidence) if draft.confidence is not None else None,
                warnings=draft.warnings_json or [],
                raw_text_excerpt=draft.raw_text_excerpt,
                created_at=draft.created_at,
                updated_at=draft.updated_at,
            )
        )
    return ListResponse(items=payload_items, total=total, limit=limit, offset=offset)
