import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.repositories.invoice_repo import InvoiceRepository
from app.schemas.validation import ValidationResolveRequest, ValidationTaskOut
from app.models import ValidationTask
from datetime import datetime

router = APIRouter(prefix="/validation-tasks")


@router.post("/{task_id}/resolve", response_model=ValidationTaskOut)
async def resolve_task(
    task_id: str,
    payload: ValidationResolveRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        task_uuid = uuid.UUID(task_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid task id")

    repo = InvoiceRepository(db)
    task = await repo.get_task(task_uuid)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.resolution_jsonb = payload.resolution
    task.status = "RESOLVED"
    task.resolved_at = datetime.utcnow()
    await db.commit()
    await db.refresh(task)
    return ValidationTaskOut(
        id=task.id,
        invoice_id=task.invoice_id,
        line_item_id=task.line_item_id,
        task_type=task.task_type,
        status=task.status,
        payload=task.payload_jsonb,
        resolution=task.resolution_jsonb,
        created_at=task.created_at,
        resolved_at=task.resolved_at,
    )
