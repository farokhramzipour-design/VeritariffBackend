from pydantic import BaseModel


class ShipmentCreate(BaseModel):
    pass


class ShipmentOut(BaseModel):
    id: str
    created_by_user_id: str
