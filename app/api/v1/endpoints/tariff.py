from fastapi import APIRouter, Depends, HTTPException
from app.core.config import settings
from app.integrations.tariff import TariffClient

router = APIRouter(prefix="/tariff")

client = TariffClient(settings.TARIFF_API_BASE_URL)


@router.post("/search")
async def tariff_search(payload: dict):
    q = payload.get("q")
    limit = payload.get("limit", 5)
    if not q:
        raise HTTPException(status_code=400, detail="q required")
    results = await client.search(q, limit=limit)
    normalized = []
    for item in results:
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
