from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_db
from app.core.security import hash_token
from app.models import ForwarderInvite, User, Team, TeamMembership
from app.models.enums import AccountTypeEnum, PlanEnum, InviteStatusEnum, StatusEnum, AuthProviderEnum
from app.schemas.forwarder import ForwarderInviteAccept

router = APIRouter(prefix="/forwarders")


@router.post("/invites/accept")
async def accept_invite(payload: ForwarderInviteAccept, db: AsyncSession = Depends(get_db)):
    token_hash = hash_token(payload.token)
    result = await db.execute(select(ForwarderInvite).where(ForwarderInvite.token_hash == token_hash))
    invite = result.scalar_one_or_none()
    if not invite:
        raise HTTPException(status_code=404, detail="Invite not found")

    if invite.expires_at < datetime.utcnow():
        invite.status = InviteStatusEnum.expired
        await db.commit()
        raise HTTPException(status_code=410, detail="Invite expired")

    if invite.status == InviteStatusEnum.accepted:
        return {"status": "already_accepted"}

    result = await db.execute(select(Team).where(Team.id == invite.team_id))
    team = result.scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    if team.seat_used >= team.seat_limit:
        raise HTTPException(status_code=409, detail="SEAT_LIMIT_REACHED")

    result = await db.execute(select(User).where(User.email == invite.email))
    user = result.scalar_one_or_none()
    if not user:
        user = User(
            email=invite.email,
            first_name=None,
            last_name=None,
            plan=PlanEnum.pro,
            account_type=AccountTypeEnum.forwarder,
            status=StatusEnum.active,
            auth_provider=AuthProviderEnum.google,
            last_login_at=None,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    else:
        if user.account_type not in (AccountTypeEnum.free, AccountTypeEnum.forwarder):
            raise HTTPException(status_code=409, detail="Account type switching is not allowed. Contact support.")
        user.plan = PlanEnum.pro
        user.account_type = AccountTypeEnum.forwarder
        user.status = StatusEnum.active

    membership_result = await db.execute(
        select(TeamMembership).where(TeamMembership.team_id == team.id, TeamMembership.user_id == user.id)
    )
    membership = membership_result.scalar_one_or_none()
    if not membership:
        team.seat_used += 1
        db.add(TeamMembership(team_id=team.id, user_id=user.id, role_in_team="member"))

    if not team.owner_user_id:
        team.owner_user_id = user.id

    invite.status = InviteStatusEnum.accepted
    invite.accepted_at = datetime.utcnow()
    await db.commit()
    return {"status": "accepted"}
