import time
import httpx
from typing import Any


class TariffClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self._cache: dict[str, tuple[float, Any]] = {}
        self.ttl_seconds = 3600

    def _get_cached(self, key: str):
        entry = self._cache.get(key)
        if not entry:
            return None
        expires_at, value = entry
        if time.time() > expires_at:
            self._cache.pop(key, None)
            return None
        return value

    def _set_cache(self, key: str, value: Any):
        self._cache[key] = (time.time() + self.ttl_seconds, value)

    async def search(self, query: str, limit: int = 5) -> list[dict]:
        cache_key = f"search:{query}:{limit}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached
        url = f"{self.base_url}/search"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params={"q": query, "limit": limit})
            resp.raise_for_status()
            data = resp.json()
        results = self._normalize_search_response(data, limit)
        self._set_cache(cache_key, results)
        return results

    def _normalize_search_response(self, data: dict, limit: int) -> list[dict]:
        if not isinstance(data, dict):
            return []
        payload = data.get("data", {})
        attributes = payload.get("attributes", {}) if isinstance(payload, dict) else {}
        match = attributes.get("goods_nomenclature_match", {}) if isinstance(attributes, dict) else {}
        commodities = match.get("commodities", []) if isinstance(match, dict) else []
        headings = match.get("headings", []) if isinstance(match, dict) else []

        combined = []
        for group in (commodities, headings):
            for item in group:
                source = item.get("_source", {}) if isinstance(item, dict) else {}
                combined.append(
                    {
                        "code": source.get("goods_nomenclature_item_id"),
                        "description": source.get("description"),
                        "score": item.get("_score", 0),
                    }
                )
        combined = [c for c in combined if c.get("code")]
        return combined[:limit]

    async def children(self, code: str) -> list[dict]:
        cache_key = f"children:{code}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached
        url = f"{self.base_url}/commodities/{code}/children"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
        children = data.get("data", []) if isinstance(data, dict) else data
        self._set_cache(cache_key, children)
        return children
