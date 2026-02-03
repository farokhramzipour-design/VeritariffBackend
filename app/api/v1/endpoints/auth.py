from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
import logging
from fastapi.responses import RedirectResponse
from urllib.parse import urlsplit, urlunsplit, urlencode, parse_qsl
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_db, validate_refresh_token
from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token, hash_token
from app.models import User, RefreshToken
from app.models.enums import PlanEnum, AccountTypeEnum, StatusEnum, AuthProviderEnum
from app.schemas.token import TokenPair
from app.services.oauth_state import create_oauth_state, consume_oauth_state
from app.services.oauth_google import GoogleOAuthService
from app.services.oauth_microsoft import MicrosoftOAuthService

router = APIRouter(prefix="/auth")
logger = logging.getLogger("uvicorn.error")


google_oauth = GoogleOAuthService(
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    redirect_uri=settings.GOOGLE_REDIRECT_URI,
)

microsoft_oauth = MicrosoftOAuthService(
    client_id=settings.MICROSOFT_CLIENT_ID,
    client_secret=settings.MICROSOFT_CLIENT_SECRET,
    redirect_uri=settings.MICROSOFT_REDIRECT_URI,
    tenant=settings.MICROSOFT_TENANT,
)


async def _issue_tokens(db: AsyncSession, user: User) -> TokenPair:
    access_token = create_access_token(str(user.id))
    refresh_token, expires_at = create_refresh_token(str(user.id))
    db.add(RefreshToken(user_id=user.id, token_hash=hash_token(refresh_token), expires_at=expires_at))
    await db.commit()
    return TokenPair(access_token=access_token, refresh_token=refresh_token)


@router.get("/google/login")
async def google_login(db: AsyncSession = Depends(get_db)):
    state = await create_oauth_state(db, provider="google")
    auth_url = google_oauth.build_authorization_url(state=state)
    return RedirectResponse(auth_url)


@router.get("/google/callback")
async def google_callback(code: str, state: str, db: AsyncSession = Depends(get_db)):
    logger.info("Google OAuth callback received state=%s code_prefix=%s", state, code[:10])
    try:
        await consume_oauth_state(db, provider="google", raw_state=state)
    except ValueError:
        logger.warning("Google OAuth invalid state=%s", state)
        raise HTTPException(status_code=400, detail="Invalid OAuth state")

    token_data = await google_oauth.exchange_code(code)
    access_token = token_data.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="OAuth token exchange failed")

    profile = await google_oauth.fetch_userinfo(access_token)
    email = profile.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Email not available from Google")

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        user = User(
            email=email,
            first_name=profile.get("given_name"),
            last_name=profile.get("family_name"),
            plan=PlanEnum.free,
            account_type=AccountTypeEnum.free,
            status=StatusEnum.active,
            auth_provider=AuthProviderEnum.google,
            last_login_at=datetime.utcnow(),
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    else:
        user.last_login_at = datetime.utcnow()
        user.auth_provider = AuthProviderEnum.google
        await db.commit()

    tokens = await _issue_tokens(db, user)
    if settings.FRONTEND_URL:
        parts = urlsplit(settings.FRONTEND_URL)
        query = dict(parse_qsl(parts.query))
        query["token"] = tokens.access_token
        redirect_url = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))
        logger.info("Google OAuth redirecting to %s", redirect_url)
        return RedirectResponse(redirect_url)
    return tokens


@router.get("/microsoft/login")
async def microsoft_login(db: AsyncSession = Depends(get_db)):
    state = await create_oauth_state(db, provider="microsoft")
    auth_url = microsoft_oauth.build_authorization_url(state=state)
    return RedirectResponse(auth_url)


@router.get("/microsoft/callback")
async def microsoft_callback(code: str, state: str, db: AsyncSession = Depends(get_db)):
    logger.info("Microsoft OAuth callback received state=%s code_prefix=%s", state, code[:10])
    try:
        await consume_oauth_state(db, provider="microsoft", raw_state=state)
    except ValueError:
        logger.warning("Microsoft OAuth invalid state=%s", state)
        raise HTTPException(status_code=400, detail="Invalid OAuth state")

    token_data = await microsoft_oauth.exchange_code(code)
    access_token = token_data.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="OAuth token exchange failed")

    profile = await microsoft_oauth.fetch_userinfo(access_token)
    email = profile.get("mail") or profile.get("userPrincipalName")
    if not email:
        raise HTTPException(status_code=400, detail="Email not available from Microsoft")

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        user = User(
            email=email,
            first_name=profile.get("givenName"),
            last_name=profile.get("surname"),
            plan=PlanEnum.free,
            account_type=AccountTypeEnum.free,
            status=StatusEnum.active,
            auth_provider=AuthProviderEnum.microsoft,
            last_login_at=datetime.utcnow(),
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    else:
        user.last_login_at = datetime.utcnow()
        user.auth_provider = AuthProviderEnum.microsoft
        await db.commit()

    tokens = await _issue_tokens(db, user)
    if settings.FRONTEND_URL:
        parts = urlsplit(settings.FRONTEND_URL)
        query = dict(parse_qsl(parts.query))
        query["token"] = tokens.access_token
        redirect_url = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))
        logger.info("Microsoft OAuth redirecting to %s", redirect_url)
        return RedirectResponse(redirect_url)
    return tokens


@router.post("/refresh", response_model=TokenPair)
async def refresh_token(
    refresh_token: str = Query(..., description="Refresh token"),
    db: AsyncSession = Depends(get_db),
):
    user, stored = await validate_refresh_token(refresh_token, db)
    stored.revoked_at = datetime.utcnow()
    await db.commit()
    return await _issue_tokens(db, user)
