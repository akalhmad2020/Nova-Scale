from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import get_settings
from app.modules.carriers.infrastructure.models import (  # noqa: F401
    Carrier,
    CarrierService,
)
from app.modules.customers.infrastructure.models import Customer  # noqa: F401
from app.modules.documents.infrastructure.models import Document, ShipmentLabel  # noqa: F401
from app.modules.identity.infrastructure import models  # noqa: F401
from app.modules.locations.infrastructure.models import Location  # noqa: F401
from app.modules.packages.infrastructure.models import Package  # noqa: F401
from app.modules.pricing.infrastructure.models import PricingRule  # noqa: F401
from app.modules.rates.infrastructure.models.rate_quote import RateQuote  # noqa: F401
from app.modules.shipment_events.infrastructure.models import ShipmentEvent  # noqa: F401
from app.modules.shipments.infrastructure.models import Shipment  # noqa: F401
from app.shared.infrastructure.database import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

settings = get_settings()

config.set_main_option(
    "sqlalchemy.url",
    settings.database_url,
)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    import asyncio

    asyncio.run(run_migrations_online())
