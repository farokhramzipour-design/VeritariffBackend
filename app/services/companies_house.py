import httpx


class CompaniesHouseService:
    def __init__(self, client_id: str, client_secret: str, auth_url: str, token_url: str, api_base_url: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.auth_url = auth_url
        self.token_url = token_url
        self.api_base_url = api_base_url.rstrip("/")

    def build_authorization_url(self, state: str, redirect_uri: str) -> str:
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "state": state,
        }
        return str(httpx.URL(self.auth_url, params=params))

    async def exchange_code(self, code: str, redirect_uri: str) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.token_url,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
                timeout=10,
            )
            response.raise_for_status()
            return response.json()

    async def fetch_company_profile(self, access_token: str, company_number: str) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_base_url}/company/{company_number}",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10,
            )
            response.raise_for_status()
            return response.json()
