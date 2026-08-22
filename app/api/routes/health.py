from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: Literal["ok", "ready"]


@router.get("/health", response_model=HealthResponse)
@router.get("/health/live", response_model=HealthResponse)
async def liveness() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/health/ready", response_model=HealthResponse)
async def readiness(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> HealthResponse:
    try:
        await session.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not ready",
        ) from exc

    return HealthResponse(status="ready")
