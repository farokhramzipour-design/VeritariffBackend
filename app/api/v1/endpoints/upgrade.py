from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_db, get_current_user, require_account_type
from app.core.config import settings
from app.models import User, CompanyUK
from app.models.enums import AccountTypeEnum, PlanEnum, StatusEnum
from app.schemas.upgrade import (
    UKExporterStartResponse,
    VATSubmission,
    VATSubmissionResponse,
    EORISubmission,
    UpgradeOptionsResponse,
    EUVerifyVATRequest,
    EUVerifyVATResponse,
)
from app.services.oauth_state import create_oauth_state, consume_oauth_state
from app.services.companies_house import CompaniesHouseService
from app.services.eori import EoriValidationService
from app.services.vies import ViesService

router = APIRouter(prefix="/upgrade")

eori_service = EoriValidationService()
companies_house = CompaniesHouseService(
    client_id=settings.COMPANIES_HOUSE_CLIENT_ID,
    client_secret=settings.COMPANIES_HOUSE_CLIENT_SECRET,
    auth_url=settings.COMPANIES_HOUSE_AUTH_URL,
    token_url=settings.COMPANIES_HOUSE_TOKEN_URL,
    api_base_url=settings.COMPANIES_HOUSE_API_BASE_URL,
)


def _ensure_upgrade_allowed(user: User):
    if user.account_type != AccountTypeEnum.free and user.account_type != AccountTypeEnum.uk_exporter:
        raise HTTPException(status_code=409, detail="Account type switching is not allowed. Contact support.")


@router.get("/options", response_model=UpgradeOptionsResponse)
async def upgrade_options(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    can_upgrade = user.account_type == AccountTypeEnum.free
    next_step = "contact_support"
    if user.account_type == AccountTypeEnum.free:
        next_step = "link_companies_house"
    elif user.account_type == AccountTypeEnum.uk_exporter:
        result = await db.execute(select(CompanyUK).where(CompanyUK.user_id == user.id))
        company = result.scalar_one_or_none()
        if not company or not company.vat_number:
            next_step = "submit_vat"
        elif company.vat_number and not company.eori_number:
            next_step = "submit_eori"
        else:
            next_step = "complete"
    elif user.account_type == AccountTypeEnum.eu_member:
        next_step = "complete"
    elif user.account_type == AccountTypeEnum.forwarder:
        next_step = "accept_invite"

    return UpgradeOptionsResponse(
        can_upgrade_uk_exporter=can_upgrade,
        can_upgrade_forwarder=can_upgrade,
        can_upgrade_eu_member=can_upgrade,
        next_step=next_step,
    )


@router.post("/uk-exporter/start", response_model=UKExporterStartResponse)
async def uk_exporter_start(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if user.account_type not in (AccountTypeEnum.free, AccountTypeEnum.uk_exporter):
        raise HTTPException(status_code=409, detail="Account type switching is not allowed. Contact support.")
    state = await create_oauth_state(db, provider="companies_house", user_id=user.id)
    auth_url = companies_house.build_authorization_url(state=state, redirect_uri=settings.COMPANIES_HOUSE_REDIRECT_URI)
    return UKExporterStartResponse(authorization_url=auth_url)


@router.get("/uk-exporter/callback")
async def uk_exporter_callback(
    code: str,
    state: str,
    company_number: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    try:
        oauth_state = await consume_oauth_state(db, provider="companies_house", raw_state=state)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")

    if not oauth_state.user_id:
        raise HTTPException(status_code=400, detail="Invalid state user")

    result = await db.execute(select(User).where(User.id == oauth_state.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    _ensure_upgrade_allowed(user)

    token_data = await companies_house.exchange_code(code, redirect_uri=settings.COMPANIES_HOUSE_REDIRECT_URI)
    access_token = token_data.get("access_token")
    company_number = company_number or token_data.get("company_number")
    if not access_token or not company_number:
        raise HTTPException(status_code=400, detail="Companies House token exchange failed")

    profile = await companies_house.fetch_company_profile(access_token, company_number)
    company_status = profile.get("company_status") or ""
    if company_status.lower() == "dissolved":
        user.status = StatusEnum.blocked
        await db.commit()
        raise HTTPException(status_code=403, detail="Company dissolved; upgrade denied")

    result = await db.execute(select(CompanyUK).where(CompanyUK.user_id == user.id))
    company = result.scalar_one_or_none()
    if not company:
        company = CompanyUK(
            user_id=user.id,
            company_number=profile.get("company_number", company_number),
            company_name=profile.get("company_name", ""),
            company_status=company_status,
            registered_office_address=profile.get("registered_office_address"),
            sic_codes=profile.get("sic_codes"),
        )
        db.add(company)
    else:
        company.company_number = profile.get("company_number", company.company_number)
        company.company_name = profile.get("company_name", company.company_name)
        company.company_status = company_status
        company.registered_office_address = profile.get("registered_office_address")
        company.sic_codes = profile.get("sic_codes")

    user.plan = PlanEnum.pro
    user.account_type = AccountTypeEnum.uk_exporter
    user.status = StatusEnum.active
    await db.commit()
    return {"status": "upgraded"}


@router.post("/uk-exporter/vat", response_model=VATSubmissionResponse)
async def submit_vat(
    payload: VATSubmission,
    user: User = Depends(require_account_type(AccountTypeEnum.uk_exporter)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(CompanyUK).where(CompanyUK.user_id == user.id))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company record not found")

    vat_number = payload.vat_number
    is_valid = eori_service.validate_vat(vat_number)
    company.vat_number = vat_number

    if is_valid:
        company.eori_number = eori_service.generate_eori(vat_number)
        await db.commit()
        return VATSubmissionResponse(
            eori_autodetected=True,
            requires_manual_eori=False,
            eori_number=company.eori_number,
        )

    company.eori_number = None
    await db.commit()
    return VATSubmissionResponse(eori_autodetected=False, requires_manual_eori=True)


@router.post("/uk-exporter/eori")
async def submit_eori(
    payload: EORISubmission,
    user: User = Depends(require_account_type(AccountTypeEnum.uk_exporter)),
    db: AsyncSession = Depends(get_db),
):
    if not eori_service.validate_eori(payload.eori_number):
        raise HTTPException(status_code=400, detail="Invalid EORI format")

    result = await db.execute(select(CompanyUK).where(CompanyUK.user_id == user.id))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company record not found")

    company.eori_number = payload.eori_number
    await db.commit()
    return {"status": "saved"}


@router.post("/eu-member/verify-vat", response_model=EUVerifyVATResponse)
async def eu_member_verify_vat(
    payload: EUVerifyVATRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if user.account_type != AccountTypeEnum.free and user.account_type != AccountTypeEnum.eu_member:
        raise HTTPException(status_code=409, detail="Account type switching is not allowed. Contact support.")

    vies = ViesService()
    result = await vies.check_vat(payload.country_code, payload.vat_number)
    if result.get("valid"):
        user.plan = PlanEnum.pro
        user.account_type = AccountTypeEnum.eu_member
        user.status = StatusEnum.active
        await db.commit()
    return EUVerifyVATResponse(is_valid=result.get("valid", False), name=result.get("name"), address=result.get("address"))
