from fastapi import APIRouter
from app.api.v1.endpoints import auth, upgrade, forwarders, shipments, me

api_router = APIRouter()
api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(me.router, tags=["me"])
api_router.include_router(upgrade.router, tags=["upgrade"])
api_router.include_router(shipments.router, tags=["shipments"])
api_router.include_router(forwarders.router, tags=["forwarders"])
