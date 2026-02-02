from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from app.models import Invoice, InvoiceLineItem, ValidationTask
from app.repositories.invoice_repo import InvoiceRepository
from app.integrations.tariff import TariffClient
from app.integrations.fx import FXClient

INCOTERM_FREIGHT = {"EXW", "FOB"}
INCOTERM_SAFE = {"CIF", "DDP"}


class InvoiceValidationService:
    def __init__(self, repo: InvoiceRepository, tariff: TariffClient, fx: FXClient):
        self.repo = repo
        self.tariff = tariff
        self.fx = fx

    async def validate_invoice(self, invoice: Invoice) -> dict:
        tasks = []
        existing = await self.repo.list_open_tasks(invoice.id)
        if existing:
            return {
                "invoice_id": str(invoice.id),
                "status": "needs_user_input",
                "tasks": existing,
                "computed_suggestions": {},
            }
        computed = {}

        incoterm = (invoice.incoterm or "").upper()
        if incoterm in INCOTERM_FREIGHT and (invoice.freight_cost is None or invoice.insurance_cost is None):
            task = ValidationTask(
                invoice_id=invoice.id,
                task_type="FREIGHT_REQUIRED",
                status="OPEN",
                payload_jsonb={
                    "message": "Shipping costs not included. Please enter estimated Freight & Insurance costs to calculate Duty.",
                    "need_freight": invoice.freight_cost is None,
                    "need_insurance": invoice.insurance_cost is None,
                },
            )
            tasks.append(await self.repo.create_task(task))

        if invoice.insurance_cost is None:
            task = ValidationTask(
                invoice_id=invoice.id,
                task_type="INSURANCE_REQUIRED",
                status="OPEN",
                payload_jsonb={
                    "options": [
                        {"type": "manual", "label": "Enter manually"},
                        {
                            "type": "estimate",
                            "label": "Estimate conservative insurance rate",
                            "formula": "insurance = invoice_value * 0.005",
                        },
                    ],
                    "default_estimate_rate": 0.005,
                },
            )
            tasks.append(await self.repo.create_task(task))
            if invoice.total_value is not None:
                computed["insurance_estimate"] = float(Decimal(invoice.total_value) * Decimal("0.005"))

        line_items = await self.repo.list_line_items(invoice.id)
        for item in line_items:
            if not item.extracted_hs_code:
                suggestions = []
                try:
                    suggestions = await self.tariff.search(item.description, limit=5)
                except Exception:
                    suggestions = []
                task = ValidationTask(
                    invoice_id=invoice.id,
                    line_item_id=item.id,
                    task_type="HS_CODE_MISSING",
                    status="OPEN",
                    payload_jsonb={
                        "line_item_id": str(item.id),
                        "description": item.description,
                        "search_suggestions": suggestions,
                    },
                )
                tasks.append(await self.repo.create_task(task))
            else:
                task = ValidationTask(
                    invoice_id=invoice.id,
                    line_item_id=item.id,
                    task_type="HS_CODE_REFINEMENT",
                    status="OPEN",
                    payload_jsonb={
                        "line_item_id": str(item.id),
                        "parent_code": item.extracted_hs_code,
                        "question": "Select a more specific 10-digit code if available",
                    },
                )
                tasks.append(await self.repo.create_task(task))

        status = "ready" if not tasks else "needs_user_input"
        return {
            "invoice_id": str(invoice.id),
            "status": status,
            "tasks": tasks,
            "computed_suggestions": computed,
        }

    async def resolve_task(self, task: ValidationTask, resolution: dict) -> ValidationTask:
        task.resolution_jsonb = resolution
        task.status = "RESOLVED"
        task.resolved_at = datetime.utcnow()
        return await self.repo.save_task(task)

    async def normalize_currency(self, invoice: Invoice, target_currency: str) -> dict:
        if not invoice.currency:
            raise ValueError("invoice currency missing")
        quote = await self.fx.quote(invoice.currency, target_currency, float(invoice.total_value or 0))
        rate = quote.get("rate") or quote.get("fx_rate") or quote.get("price")
        if not rate:
            raise ValueError("fx rate unavailable")
        rate = Decimal(str(rate))

        def _convert(value: float | None) -> float | None:
            if value is None:
                return None
            return float((Decimal(str(value)) * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

        normalized = {
            "normalized_currency": target_currency,
            "fx_rate": float(rate),
            "normalized_totals": {
                "total_value": _convert(invoice.total_value),
                "freight_cost": _convert(invoice.freight_cost),
                "insurance_cost": _convert(invoice.insurance_cost),
            },
        }
        return normalized
