from fastapi import APIRouter, HTTPException
from app.core.config import settings
from app.integrations.fx import FXClient

router = APIRouter(prefix="/fx")

client = FXClient(settings.FX_API_BASE_URL, api_key=settings.FX_API_KEY)


@router.get("/quote")
async def fx_quote(base: str, quote: str, amount: float):
    if not base or not quote:
        raise HTTPException(status_code=400, detail="base and quote required")
    data = await client.quote(base, quote, amount)
    return data
