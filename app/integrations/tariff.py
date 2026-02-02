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
        results = data.get("data", []) if isinstance(data, dict) else data
        self._set_cache(cache_key, results)
        return results

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
