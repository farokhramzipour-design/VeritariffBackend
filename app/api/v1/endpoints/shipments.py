import secrets
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from app.api.deps import get_current_user, get_db
from app.core.security import hash_token
from app.models import Shipment, ForwarderInvite, Team, ShipmentForwarder, BuyerEU, TeamMembership
from app.models.enums import AccountTypeEnum, PlanEnum, InviteStatusEnum
from app.schemas.shipment import ShipmentCreate, ShipmentOut
from app.schemas.forwarder import ForwarderInviteCreate, ForwarderInviteResponse
from app.schemas.buyer import BuyerVATVerifyRequest, BuyerVATVerifyResponse
from app.services.email import EmailService
from app.services.vies import ViesService

router = APIRouter(prefix="/shipments")

INVITE_TTL_HOURS = 48
email_service = EmailService()


async def _require_exporter_or_team_member(user, db: AsyncSession, shipment_id: uuid.UUID):
    if user.plan == PlanEnum.pro and user.account_type == AccountTypeEnum.uk_exporter:
        return

    if user.account_type == AccountTypeEnum.forwarder:
        result = await db.execute(
            select(TeamMembership).where(TeamMembership.user_id == user.id)
        )
        membership = result.scalar_one_or_none()
        if not membership:
            raise HTTPException(status_code=403, detail="Forwarder team membership required")

        result = await db.execute(
            select(ShipmentForwarder).where(
                ShipmentForwarder.shipment_id == shipment_id,
                ShipmentForwarder.team_id == membership.team_id,
            )
        )
        assigned = result.scalar_one_or_none()
        if assigned:
            return

    raise HTTPException(status_code=403, detail="Exporter or team member access required")


def _require_eu_or_exporter(user):
    if user.plan != PlanEnum.pro or user.account_type not in (AccountTypeEnum.uk_exporter, AccountTypeEnum.eu_member):
        raise HTTPException(status_code=403, detail="Pro EU/Exporter access required")


@router.post("", response_model=ShipmentOut)
async def create_shipment(
    payload: ShipmentCreate,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_eu_or_exporter(user)
    shipment = Shipment(created_by_user_id=user.id)
    db.add(shipment)
    await db.commit()
    await db.refresh(shipment)
    return ShipmentOut(id=str(shipment.id), created_by_user_id=str(shipment.created_by_user_id))


@router.post("/{shipment_id}/forwarders/invite", response_model=ForwarderInviteResponse)
async def invite_forwarder(
    shipment_id: str,
    payload: ForwarderInviteCreate,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        shipment_uuid = uuid.UUID(shipment_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid shipment id")
    await _require_exporter_or_team_member(user, db, shipment_uuid)
    result = await db.execute(select(Shipment).where(Shipment.id == shipment_uuid))
    shipment = result.scalar_one_or_none()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
    if user.account_type == AccountTypeEnum.uk_exporter and shipment.created_by_user_id != user.id:
        raise HTTPException(status_code=403, detail="Exporter access required")

    team = Team(seat_limit=5, seat_used=0)
    db.add(team)
    await db.commit()
    await db.refresh(team)

    token = secrets.token_urlsafe(32)
    token_hash = hash_token(token)
    invite = ForwarderInvite(
        team_id=team.id,
        email=payload.email,
        token_hash=token_hash,
        expires_at=datetime.utcnow() + timedelta(hours=INVITE_TTL_HOURS),
        status=InviteStatusEnum.pending,
    )
    db.add(invite)
    db.add(ShipmentForwarder(shipment_id=shipment.id, team_id=team.id))
    await db.commit()

    await email_service.send_forwarder_invite(payload.email, token)
    return ForwarderInviteResponse(invite_id=str(invite.id), expires_at=invite.expires_at.isoformat(), token=token)


@router.post("/{shipment_id}/buyers/verify-vat", response_model=BuyerVATVerifyResponse)
async def verify_buyer_vat(
    shipment_id: str,
    payload: BuyerVATVerifyRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_eu_or_exporter(user)

    try:
        shipment_uuid = uuid.UUID(shipment_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid shipment id")
    result = await db.execute(select(Shipment).where(Shipment.id == shipment_uuid))
    shipment = result.scalar_one_or_none()
    if not shipment or shipment.created_by_user_id != user.id:
        raise HTTPException(status_code=404, detail="Shipment not found")

    vies = ViesService()
    result = await vies.check_vat(payload.country_code, payload.vat_number)
    buyer = BuyerEU(
        shipment_id=shipment.id,
        country_code=payload.country_code,
        vat_number=payload.vat_number,
        name=result.get("name"),
        address={"raw": result.get("address")} if result.get("address") else None,
        is_vat_valid=result.get("valid", False),
    )
    db.add(buyer)
    await db.commit()
    return BuyerVATVerifyResponse(
        is_valid=result.get("valid", False),
        name=result.get("name"),
        address=result.get("address"),
    )
