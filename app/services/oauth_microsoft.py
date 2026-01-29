import httpx


class MicrosoftOAuthService:
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str, tenant: str = "common"):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.tenant = tenant

    @property
    def auth_url(self) -> str:
        return f"https://login.microsoftonline.com/{self.tenant}/oauth2/v2.0/authorize"

    @property
    def token_url(self) -> str:
        return f"https://login.microsoftonline.com/{self.tenant}/oauth2/v2.0/token"

    def build_authorization_url(self, state: str) -> str:
        scope = "openid email profile User.Read"
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "response_mode": "query",
            "scope": scope,
            "state": state,
        }
        return httpx.URL(self.auth_url, params=params).human_repr()

    async def exchange_code(self, code: str) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.token_url,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": self.redirect_uri,
                    "scope": "openid email profile User.Read",
                },
                timeout=10,
            )
            response.raise_for_status()
            return response.json()

    async def fetch_userinfo(self, access_token: str) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://graph.microsoft.com/v1.0/me",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10,
            )
            response.raise_for_status()
            return response.json()
