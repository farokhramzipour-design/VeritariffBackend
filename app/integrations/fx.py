import httpx


class FXClient:
    def __init__(self, base_url: str, api_key: str | None = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    async def quote(self, base: str, quote: str, amount: float) -> dict:
        params = {"base": base, "quote": quote, "amount": amount}
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{self.base_url}/quote", params=params, headers=headers)
            resp.raise_for_status()
            return resp.json()
