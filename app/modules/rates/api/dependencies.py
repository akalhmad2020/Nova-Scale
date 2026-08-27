from app.core.database import SessionFactory
from app.modules.rates.application.use_cases.create_rate_quote import (
    CreateRateQuote,
)
from app.modules.rates.application.use_cases.get_rate_quote import (
    GetRateQuote,
)
from app.modules.rates.application.use_cases.list_rate_quotes import (
    ListRateQuotes,
)
from app.modules.rates.application.use_cases.transition_rate_quote_status import (
    TransitionRateQuoteStatus,
)
from app.modules.rates.infrastructure.unit_of_work import (
    SQLAlchemyUnitOfWork,
)


def get_create_rate_quote_use_case() -> CreateRateQuote:
    return CreateRateQuote(
        unit_of_work=SQLAlchemyUnitOfWork(SessionFactory),
    )


def get_get_rate_quote_use_case() -> GetRateQuote:
    return GetRateQuote(
        unit_of_work=SQLAlchemyUnitOfWork(SessionFactory),
    )


def get_list_rate_quotes_use_case() -> ListRateQuotes:
    return ListRateQuotes(
        unit_of_work=SQLAlchemyUnitOfWork(SessionFactory),
    )


def get_transition_rate_quote_status_use_case() -> TransitionRateQuoteStatus:
    return TransitionRateQuoteStatus(
        unit_of_work=SQLAlchemyUnitOfWork(SessionFactory),
    )
