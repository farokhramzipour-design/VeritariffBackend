
import time
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from sqlalchemy.exc import OperationalError

from app.api.v1.api import api_router
from app.core.config import settings
from app.db.base import Base
from app.db.session import engine

# Retry logic for database connection
MAX_RETRIES = 5
WAIT_SECONDS = 2

for i in range(MAX_RETRIES):
    try:
        # Create database tables
        Base.metadata.create_all(bind=engine)
        break
    except OperationalError as e:
        if i == MAX_RETRIES - 1:
            print(f"Could not connect to database after {MAX_RETRIES} attempts.")
            raise e
        print(f"Database not ready, waiting {WAIT_SECONDS} seconds... (Attempt {i+1}/{MAX_RETRIES})")
        time.sleep(WAIT_SECONDS)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Set all CORS enabled origins
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix=settings.API_V1_STR)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
