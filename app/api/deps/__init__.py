from datetime import datetime
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_token
from app.db.session import SessionLocal
from app.models import User, RefreshToken
from app.schemas.token import TokenPayload
from app.models.enums import PlanEnum, AccountTypeEnum

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/refresh")


async def get_db() -> AsyncSession:
    async with SessionLocal() as session:
        yield session


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        token_data = TokenPayload(**payload)
    except (JWTError, ValueError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Could not validate credentials")

    if token_data.token_type != "access":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid token type")

    result = await db.execute(select(User).where(User.id == token_data.sub))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def require_plan(plan: PlanEnum):
    async def _checker(user: User = Depends(get_current_user)) -> User:
        if user.plan != plan:
            raise HTTPException(status_code=403, detail="Insufficient plan")
        return user

    return _checker


def require_account_type(account_type: AccountTypeEnum):
    async def _checker(user: User = Depends(get_current_user)) -> User:
        if user.account_type != account_type:
            raise HTTPException(status_code=403, detail="Insufficient account type")
        return user

    return _checker


async def require_free_account(user: User = Depends(get_current_user)) -> User:
    if user.account_type != AccountTypeEnum.free:
        raise HTTPException(status_code=409, detail="Account type switching is not allowed. Contact support.")
    return user


async def validate_refresh_token(
    refresh_token: str,
    db: AsyncSession,
) -> User:
    try:
        payload = jwt.decode(refresh_token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        token_data = TokenPayload(**payload)
    except (JWTError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    if token_data.token_type != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    result = await db.execute(select(User).where(User.id == token_data.sub))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    token_hash = hash_token(refresh_token)
    result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    stored = result.scalar_one_or_none()
    if not stored or stored.revoked_at is not None or stored.expires_at < datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired or revoked")

    return user
