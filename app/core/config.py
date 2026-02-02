from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyHttpUrl, field_validator


class Settings(BaseSettings):
    PROJECT_NAME: str = "Veritariff Backend"
    API_V1_STR: str = "/api/v1"

    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/veritariff"

    JWT_SECRET_KEY: str = "CHANGE_ME"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/google/callback"

    MICROSOFT_CLIENT_ID: str = ""
    MICROSOFT_CLIENT_SECRET: str = ""
    MICROSOFT_TENANT: str = "common"
    MICROSOFT_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/microsoft/callback"

    COMPANIES_HOUSE_CLIENT_ID: str = ""
    COMPANIES_HOUSE_CLIENT_SECRET: str = ""
    COMPANIES_HOUSE_AUTH_URL: str = "https://account.companieshouse.gov.uk/oauth2/authorize"
    COMPANIES_HOUSE_TOKEN_URL: str = "https://account.companieshouse.gov.uk/oauth2/token"
    COMPANIES_HOUSE_API_BASE_URL: str = "https://api.company-information.service.gov.uk"
    COMPANIES_HOUSE_REDIRECT_URI: str = "http://localhost:8000/api/v1/upgrade/uk-exporter/callback"

    FRONTEND_URL: str = "https://veritariffai.co"

    BACKEND_CORS_ORIGINS: str = ""

    AUTO_CREATE_TABLES: bool = False
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_MB: int = 20
    LLM_PROVIDER: str | None = None
    OPENAI_MODEL: str = "gpt-4o"
    TARIFF_API_BASE_URL: str = "https://www.trade-tariff.service.gov.uk/api/v2"
    FX_API_BASE_URL: str = "https://example-fx.local"
    FX_API_KEY: str | None = None

    @property
    def cors_origins(self) -> List[str]:
        if not self.BACKEND_CORS_ORIGINS:
            return []
        return [i.strip() for i in self.BACKEND_CORS_ORIGINS.split(",") if i.strip()]

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
