from pydantic import BaseModel
from app.schemas.user import UserOut


class MeResponse(BaseModel):
    user: UserOut
    upgrade_available: bool
    needs_companies_house_link: bool
    needs_vat: bool
    requires_manual_eori: bool
