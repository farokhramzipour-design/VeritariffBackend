from fastapi import APIRouter, Depends, HTTPException
import logging
from app.core.config import settings
from app.integrations.tariff import TariffClient

router = APIRouter(prefix="/tariff")
logger = logging.getLogger("uvicorn.error")

client = TariffClient(settings.TARIFF_API_BASE_URL)


@router.post("/search")
async def tariff_search(payload: dict):
    q = payload.get("q")
    limit = payload.get("limit", 5)
    if not q:
        raise HTTPException(status_code=400, detail="q required")
    results = await client.search(q, limit=limit)
    logger.info("Tariff search normalized count=%s", len(results))
    return {"results": results}


@router.get("/commodities/{code}/children")
async def tariff_children(code: str):
    children = await client.children(code)
    return {"children": children}
