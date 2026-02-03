import httpx


class FXClient:
    def __init__(self, base_url: str, api_key: str | None = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    async def quote(self, base: str, quote: str, amount: float) -> dict:
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        params = {"amount": amount, "from": base.upper(), "to": quote.upper()}
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(self.base_url, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        rates = data.get("rates", {}) if isinstance(data, dict) else {}
        converted = rates.get(quote.upper())
        if converted is None:
            raise ValueError("rate not found")
        rate = float(converted) / float(amount) if amount else None
        if rate is None:
            raise ValueError("rate not found")
        return {
            "base": base.upper(),
            "quote": quote.upper(),
            "amount": amount,
            "rate": rate,
            "converted": float(converted),
            "date": data.get("date") if isinstance(data, dict) else None,
        }
