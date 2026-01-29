from pydantic import BaseModel, EmailStr


class ForwarderInviteCreate(BaseModel):
    email: EmailStr


class ForwarderInviteResponse(BaseModel):
    invite_id: str
    expires_at: str
    token: str


class ForwarderInviteAccept(BaseModel):
    token: str
