from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class ValidationTaskOut(BaseModel):
    id: UUID
    invoice_id: UUID
    line_item_id: UUID | None = None
    task_type: str
    status: str
    payload: dict | None = None
    resolution: dict | None = None
    created_at: datetime
    resolved_at: datetime | None = None


class ValidationResolveRequest(BaseModel):
    resolution: dict
