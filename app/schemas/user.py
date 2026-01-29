from datetime import datetime
from pydantic import BaseModel, EmailStr, ConfigDict
from app.models.enums import PlanEnum, AccountTypeEnum, StatusEnum, AuthProviderEnum


class UserBase(BaseModel):
    email: EmailStr
    first_name: str | None = None
    last_name: str | None = None


class UserCreate(UserBase):
    auth_provider: AuthProviderEnum


class UserOut(UserBase):
    id: str
    plan: PlanEnum
    account_type: AccountTypeEnum
    status: StatusEnum
    auth_provider: AuthProviderEnum
    created_at: datetime
    updated_at: datetime
    last_login_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
