from types import TracebackType

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.modules.pricing.infrastructure.models.pricing_rule import PricingRule
from app.modules.pricing.infrastructure.repositories.pricing_rule_repository import (
    PricingRuleRepository,
)
from app.modules.rates.infrastructure.models.rate_quote import RateQuote
from app.modules.rates.infrastructure.repositories.rate_quote_repository import (
    RateQuoteRepository,
)
from app.modules.shipments.infrastructure.repositories.shipment_repository import (
    ShipmentRepository,
)


class SQLAlchemyUnitOfWork:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None

        self.pricing_rules: PricingRuleRepository
        self.shipments: ShipmentRepository
        self.rate_quotes: RateQuoteRepository

    async def __aenter__(self) -> "SQLAlchemyUnitOfWork":
        self._session = self._session_factory()

        self.pricing_rules = PricingRuleRepository(self._session)
        self.shipments = ShipmentRepository(self._session)
        self.rate_quotes = RateQuoteRepository(self._session)

        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._session is None:
            return

        try:
            if exc_type is not None:
                await self.rollback()
        finally:
            await self._session.close()
            self._session = None

    async def flush(self) -> None:
        if self._session is None:
            raise RuntimeError("Unit of work is not active")

        await self._session.flush()

    async def commit(self) -> None:
        if self._session is None:
            raise RuntimeError("Unit of work is not active")

        await self._session.commit()

    async def rollback(self) -> None:
        if self._session is None:
            raise RuntimeError("Unit of work is not active")

        await self._session.rollback()

    async def refresh(
        self,
        model: PricingRule | RateQuote,
    ) -> None:
        if self._session is None:
            raise RuntimeError("Unit of work is not active")

        await self._session.refresh(model)
