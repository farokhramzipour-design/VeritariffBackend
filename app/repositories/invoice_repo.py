from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import Invoice, InvoiceLineItem, ValidationTask


class InvoiceRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_invoice(self, invoice_id):
        result = await self.db.execute(select(Invoice).where(Invoice.id == invoice_id))
        return result.scalar_one_or_none()

    async def list_line_items(self, invoice_id):
        result = await self.db.execute(
            select(InvoiceLineItem).where(InvoiceLineItem.invoice_id == invoice_id).order_by(InvoiceLineItem.sort_order)
        )
        return result.scalars().all()

    async def create_task(self, task: ValidationTask) -> ValidationTask:
        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def save_task(self, task: ValidationTask) -> ValidationTask:
        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def list_open_tasks(self, invoice_id):
        result = await self.db.execute(
            select(ValidationTask).where(
                ValidationTask.invoice_id == invoice_id,
                ValidationTask.status == "OPEN",
            ).order_by(ValidationTask.created_at.asc())
        )
        return result.scalars().all()

    async def get_task(self, task_id):
        result = await self.db.execute(select(ValidationTask).where(ValidationTask.id == task_id))
        return result.scalar_one_or_none()
