from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_current_user, get_db
from app.models import CompanyUK
from app.models.enums import AccountTypeEnum
from app.schemas.me import MeResponse
from app.schemas.user import UserOut

router = APIRouter(prefix="/me")


@router.get("", response_model=MeResponse)
async def read_me(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    needs_companies_house_link = user.account_type == AccountTypeEnum.free
    needs_vat = False
    requires_manual_eori = False

    if user.account_type == AccountTypeEnum.uk_exporter:
        result = await db.execute(select(CompanyUK).where(CompanyUK.user_id == user.id))
        company = result.scalar_one_or_none()
        needs_vat = not company or not company.vat_number
        requires_manual_eori = bool(company and company.vat_number and not company.eori_number)

    return MeResponse(
        user=UserOut.model_validate(user),
        upgrade_available=True,
        needs_companies_house_link=needs_companies_house_link,
        needs_vat=needs_vat,
        requires_manual_eori=requires_manual_eori,
    )
