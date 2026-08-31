from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.api.router import create_api_router
from app.core.config import get_settings
from app.core.database import dispose_engine
from app.core.exception_handlers import unhandled_exception_handler
from app.core.logging import configure_logging
from app.core.request_id import RequestIdMiddleware
from app.core.security_headers import SecurityHeadersMiddleware


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(
        settings.log_level,
        service="api",
        environment=settings.app_env,
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
        yield
        await dispose_engine()

    application = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        debug=settings.debug,
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url="/redoc" if settings.docs_enabled else None,
        openapi_url="/openapi.json" if settings.docs_enabled else None,
        lifespan=lifespan,
    )

    application.add_exception_handler(
        Exception,
        unhandled_exception_handler,
    )

    application.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.allowed_hosts,
    )

    application.add_middleware(RequestIdMiddleware)

    if settings.cors_allowed_origins:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_allowed_origins,
            allow_credentials=False,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    application.add_middleware(
        SecurityHeadersMiddleware,
        hsts_enabled=settings.hsts_enabled,
    )

    application.include_router(create_api_router(settings.api_v1_prefix))

    return application


app = create_app()
