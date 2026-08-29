from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

from app.modules.ledger.application.exceptions import (
    InvalidJournalLineError,
    JournalEntryAmountMustBePositiveError,
    JournalEntryNotBalancedError,
    JournalEntryRequiresAtLeastTwoLinesError,
)


@dataclass(frozen=True, slots=True)
class JournalAmount:
    debit: Decimal
    credit: Decimal


def validate_balanced_journal(
    lines: Iterable[JournalAmount],
) -> None:
    materialized_lines = list(lines)

    if len(materialized_lines) < 2:
        raise JournalEntryRequiresAtLeastTwoLinesError

    for line in materialized_lines:
        if line.debit < 0 or line.credit < 0:
            raise InvalidJournalLineError

        if line.debit > 0 and line.credit > 0:
            raise InvalidJournalLineError

        if line.debit == 0 and line.credit == 0:
            raise InvalidJournalLineError

    total_debit = sum(
        (line.debit for line in materialized_lines),
        start=Decimal("0.00"),
    )

    total_credit = sum(
        (line.credit for line in materialized_lines),
        start=Decimal("0.00"),
    )

    if total_debit <= Decimal("0.00"):
        raise JournalEntryAmountMustBePositiveError

    if total_debit != total_credit:
        raise JournalEntryNotBalancedError
