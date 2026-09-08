import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.integration


async def test_runtime_database_role_is_not_privileged(
    db_session: AsyncSession,
) -> None:
    result = await db_session.execute(
        text(
            """
            SELECT
                current_user,
                rolsuper,
                rolcreatedb,
                rolcreaterole,
                rolbypassrls
            FROM pg_roles
            WHERE rolname = current_user
            """
        )
    )

    row = result.one()

    assert row.current_user == "novascale_app"
    assert row.rolsuper is False
    assert row.rolcreatedb is False
    assert row.rolcreaterole is False
    assert row.rolbypassrls is False


async def test_runtime_database_role_cannot_bypass_rls(
    db_session: AsyncSession,
) -> None:
    result = await db_session.execute(
        text(
            """
            SELECT rolbypassrls
            FROM pg_roles
            WHERE rolname = current_user
            """
        )
    )

    assert result.scalar_one() is False
