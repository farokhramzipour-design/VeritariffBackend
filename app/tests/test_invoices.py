import uuid
import pytest
from httpx import AsyncClient

from app.api.deps import get_current_user
from app.models import User, DraftInvoice, UploadedDocument
from app.models import Invoice, InvoiceLineItem
from app.models.enums import PlanEnum, AccountTypeEnum, StatusEnum, AuthProviderEnum
from app.services.invoice_validator import reconcile_totals, validate_required_fields, validate_quantities


@pytest.mark.asyncio
async def test_totals_reconciliation():
    payload = {
        "currency": "USD",
        "invoice_date": "2026-01-01",
        "total_value": 100.0,
        "line_items": [
            {"description": "Item", "quantity": 2, "unit_price": 50.0, "line_total": 100.0}
        ],
    }
    ok, msg = reconcile_totals(payload)
    assert ok
    assert msg is None


@pytest.mark.asyncio
async def test_required_fields_validation():
    payload = {"line_items": []}
    errors = validate_required_fields(payload)
    assert "currency required" in errors
    assert "invoice_date required" in errors
    assert "at least one line item required" in errors


@pytest.mark.asyncio
async def test_idempotent_confirm(client, db_session):
    user = User(
        id=uuid.uuid4(),
        email="invoice@example.com",
        first_name="Test",
        last_name="User",
        plan=PlanEnum.free,
        account_type=AccountTypeEnum.free,
        status=StatusEnum.active,
        auth_provider=AuthProviderEnum.google,
    )
    upload = UploadedDocument(
        id=uuid.uuid4(),
        user_id=user.id,
        filename="test.pdf",
        content_type="application/pdf",
        storage_path="/tmp/test.pdf",
        sha256="abc",
        size_bytes=100,
    )
    draft = DraftInvoice(
        id=uuid.uuid4(),
        user_id=user.id,
        upload_id=upload.id,
        status="EXTRACTED",
    )
    db_session.add_all([user, upload, draft])
    await db_session.commit()

    async def override_user():
        return user

    client.dependency_overrides[get_current_user] = override_user

    body = {
        "supplier_name": "Vendor",
        "invoice_number": "INV-1",
        "invoice_date": "2026-01-01",
        "due_date": "2026-02-01",
        "incoterm": "EXW",
        "currency": "USD",
        "total_value": 100.0,
        "line_items": [
            {"description": "Item", "quantity": 1, "unit_price": 100.0, "line_total": 100.0}
        ],
    }

    async with AsyncClient(app=client, base_url="http://test") as ac:
        first = await ac.post(f"/api/v1/invoices/drafts/{draft.id}/confirm", json=body)
        assert first.status_code == 200
        invoice_id = first.json()["invoice_id"]

        second = await ac.post(f"/api/v1/invoices/drafts/{draft.id}/confirm", json=body)
        assert second.status_code == 200
        assert second.json()["invoice_id"] == invoice_id

    client.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_validate_creates_freight_task(client, db_session):
    user = User(
        id=uuid.uuid4(),
        email="validate@example.com",
        first_name="Val",
        last_name="User",
        plan=PlanEnum.free,
        account_type=AccountTypeEnum.free,
        status=StatusEnum.active,
        auth_provider=AuthProviderEnum.google,
    )
    invoice = Invoice(
        id=uuid.uuid4(),
        user_id=user.id,
        supplier_name="Supplier",
        invoice_number="INV-2",
        invoice_date="2026-01-02",
        incoterm="EXW",
        currency="USD",
        total_value=100.0,
        source_upload_id=uuid.uuid4(),
        status="DRAFT",
    )
    line = InvoiceLineItem(
        id=uuid.uuid4(),
        invoice_id=invoice.id,
        description="Item",
        quantity=1,
        unit_price=100.0,
        line_total=100.0,
        sort_order=0,
    )
    db_session.add_all([user, invoice, line])
    await db_session.commit()

    async def override_user():
        return user

    client.dependency_overrides[get_current_user] = override_user
    async with AsyncClient(app=client, base_url="http://test") as ac:
        resp = await ac.post(f"/api/v1/invoices/{invoice.id}/validate")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "needs_user_input"

    client.dependency_overrides.pop(get_current_user, None)
