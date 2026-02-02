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
    logger.info("Tariff search response type=%s size=%s", type(results).__name__, len(results) if hasattr(results, "__len__") else "n/a")
    normalized = []
    for item in results:
        if not isinstance(item, dict):
            normalized.append({"code": str(item), "description": str(item), "score": 0})
            continue
        normalized.append(
            {
                "code": item.get("goods_nomenclature_item_id") or item.get("code"),
                "description": item.get("description") or item.get("goods_nomenclature_item_id"),
                "score": item.get("score", 0),
            }
        )
    return {"results": normalized}


@router.get("/commodities/{code}/children")
async def tariff_children(code: str):
    children = await client.children(code)
    return {"children": children}
