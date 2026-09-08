from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def set_session_tenant_context(
    session: AsyncSession,
    tenant_id: UUID,
) -> None:
    await session.execute(
        text(
            """
            SELECT set_config(
                'app.current_tenant_id',
                :tenant_id,
                true
            )
            """
        ),
        {"tenant_id": str(tenant_id)},
    )
