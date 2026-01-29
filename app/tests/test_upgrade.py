import uuid
import pytest
from datetime import datetime, timedelta
from httpx import AsyncClient
from sqlalchemy import select

from app.api.deps import get_current_user
from app.models import User, CompanyUK, ForwarderInvite, Team
from app.models.enums import PlanEnum, AccountTypeEnum, StatusEnum, AuthProviderEnum, InviteStatusEnum
from app.core.security import hash_token


@pytest.mark.asyncio
async def test_upgrade_state_transitions(client, db_session):
    user = User(
        id=uuid.uuid4(),
        email="free@example.com",
        first_name="Free",
        last_name="User",
        plan=PlanEnum.free,
        account_type=AccountTypeEnum.free,
        status=StatusEnum.active,
        auth_provider=AuthProviderEnum.google,
    )
    db_session.add(user)
    await db_session.commit()

    async def override_user():
        return user

    client.dependency_overrides[get_current_user] = override_user

    async with AsyncClient(app=client, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/upgrade/options")
        assert resp.status_code == 200
        assert resp.json()["next_step"] == "link_companies_house"

    user.account_type = AccountTypeEnum.uk_exporter
    user.plan = PlanEnum.pro
    company = CompanyUK(
        user_id=user.id,
        company_number="12345678",
        company_name="Test Co",
        company_status="active",
        registered_office_address={},
        sic_codes=["1234"],
    )
    db_session.add(company)
    await db_session.commit()

    async with AsyncClient(app=client, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/upgrade/options")
        assert resp.status_code == 200
        assert resp.json()["next_step"] == "submit_vat"
    client.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_vat_to_eori_flow(client, db_session):
    user = User(
        id=uuid.uuid4(),
        email="exporter@example.com",
        first_name="UK",
        last_name="Exporter",
        plan=PlanEnum.pro,
        account_type=AccountTypeEnum.uk_exporter,
        status=StatusEnum.active,
        auth_provider=AuthProviderEnum.google,
    )
    company = CompanyUK(
        user_id=user.id,
        company_number="87654321",
        company_name="Export Ltd",
        company_status="active",
        registered_office_address={},
        sic_codes=["4321"],
    )
    db_session.add_all([user, company])
    await db_session.commit()

    async def override_user():
        return user

    client.dependency_overrides[get_current_user] = override_user

    async with AsyncClient(app=client, base_url="http://test") as ac:
        resp = await ac.post("/api/v1/upgrade/uk-exporter/vat", json={"vat_number": "123456789"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["eori_autodetected"] is True
        assert data["eori_number"] == "GB123456789000"
    client.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_forwarder_invite_accept(client, db_session):
    team = Team(seat_limit=1, seat_used=0)
    db_session.add(team)
    await db_session.commit()

    token = "invite-token"
    invite = ForwarderInvite(
        team_id=team.id,
        email="forwarder@example.com",
        token_hash=hash_token(token),
        expires_at=datetime.utcnow() + timedelta(hours=1),
        status=InviteStatusEnum.pending,
    )
    db_session.add(invite)
    await db_session.commit()

    async with AsyncClient(app=client, base_url="http://test") as ac:
        resp = await ac.post("/api/v1/forwarders/invites/accept", json={"token": token})
        assert resp.status_code == 200

    result = await db_session.execute(select(User).where(User.email == "forwarder@example.com"))
    user = result.scalar_one()
    assert user.account_type == AccountTypeEnum.forwarder
    assert user.plan == PlanEnum.pro
