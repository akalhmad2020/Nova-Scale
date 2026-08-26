from fastapi import APIRouter

from app.api.routes.health import router as health_router
from app.modules.customers.api.routes import router as customers_router
from app.modules.identity.api.invitation_routes import (
    router as invitation_router,
)
from app.modules.identity.api.routes import router as identity_router
from app.modules.identity.api.tenant_routes import router as tenant_router
from app.modules.locations.api.routes import router as locations_router
from app.modules.shipments.api.routes import router as shipments_router

api_router = APIRouter()

api_router.include_router(health_router)

api_router.include_router(
    identity_router,
    prefix="/api/v1",
)

api_router.include_router(
    tenant_router,
    prefix="/api/v1",
)

api_router.include_router(
    invitation_router,
    prefix="/api/v1",
)

api_router.include_router(
    customers_router,
    prefix="/api/v1",
)
api_router.include_router(
    locations_router,
    prefix="/api/v1",
)

api_router.include_router(
    shipments_router,
    prefix="/api/v1",
)
