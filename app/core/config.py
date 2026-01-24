
from pydantic_settings import BaseSettings
from typing import Optional, List

class Settings(BaseSettings):
    PROJECT_NAME: str = "Veritariff Backend"
    API_V1_STR: str = "/api/v1"
    
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "password"
    POSTGRES_DB: str = "veritariff"
    SQLALCHEMY_DATABASE_URI: Optional[str] = None

    GOOGLE_CLIENT_ID: str = "875867590179-solq59gvt3kn448jlsvtgfl0m1co53ol.apps.googleusercontent.com"
    GOOGLE_CLIENT_SECRET: str = "875867590179-solq59gvt3kn448jlsvtgfl0m1co53ol.apps.googleusercontent.com"
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/login/google/callback"
    
    # CORS Origins: Add your production domains here
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost",
        "http://localhost:8080",
        "http://localhost:3000",
        "https://veritariffai.co",
        "https://www.veritariffai.co",
        "https://api.veritariffai.co"
    ]

    @property
    def database_url(self) -> str:
        if self.SQLALCHEMY_DATABASE_URI:
            return self.SQLALCHEMY_DATABASE_URI
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"

    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()
