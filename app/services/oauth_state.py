import secrets
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import OAuthState
from app.core.security import hash_token

STATE_TTL_MINUTES = 10


async def create_oauth_state(db: AsyncSession, provider: str, user_id=None, redirect_uri: str | None = None) -> str:
    raw_state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(16)
    expires_at = datetime.utcnow() + timedelta(minutes=STATE_TTL_MINUTES)
    state_hash = hash_token(raw_state)
    record = OAuthState(
        provider=provider,
        state_hash=state_hash,
        nonce=nonce,
        redirect_uri=redirect_uri,
        expires_at=expires_at,
        user_id=user_id,
    )
    db.add(record)
    await db.commit()
    return raw_state


async def consume_oauth_state(db: AsyncSession, provider: str, raw_state: str) -> OAuthState:
    state_hash = hash_token(raw_state)
    result = await db.execute(
        select(OAuthState).where(OAuthState.provider == provider, OAuthState.state_hash == state_hash)
    )
    record = result.scalar_one_or_none()
    now = datetime.utcnow()
    if record and record.expires_at and record.expires_at.tzinfo is not None:
        now = now.replace(tzinfo=record.expires_at.tzinfo)
    if not record or record.used_at is not None or record.expires_at < now:
        raise ValueError("Invalid or expired state")
    record.used_at = datetime.utcnow()
    await db.commit()
    return record
