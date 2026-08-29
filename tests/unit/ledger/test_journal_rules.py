from decimal import Decimal

import pytest

from app.modules.ledger.application.exceptions import (
    InvalidJournalLineError,
    JournalEntryNotBalancedError,
    JournalEntryRequiresAtLeastTwoLinesError,
)
from app.modules.ledger.domain.rules import JournalAmount, validate_balanced_journal


def test_balanced_journal_is_valid() -> None:
    validate_balanced_journal(
        [
            JournalAmount(
                debit=Decimal("100.00"),
                credit=Decimal("0.00"),
            ),
            JournalAmount(
                debit=Decimal("0.00"),
                credit=Decimal("100.00"),
            ),
        ]
    )


def test_journal_requires_at_least_two_lines() -> None:
    with pytest.raises(JournalEntryRequiresAtLeastTwoLinesError):
        validate_balanced_journal(
            [
                JournalAmount(
                    debit=Decimal("100.00"),
                    credit=Decimal("0.00"),
                )
            ]
        )


def test_journal_rejects_unbalanced_amounts() -> None:
    with pytest.raises(JournalEntryNotBalancedError):
        validate_balanced_journal(
            [
                JournalAmount(
                    debit=Decimal("100.00"),
                    credit=Decimal("0.00"),
                ),
                JournalAmount(
                    debit=Decimal("0.00"),
                    credit=Decimal("90.00"),
                ),
            ]
        )


@pytest.mark.parametrize(
    ("debit", "credit"),
    [
        (Decimal("-1.00"), Decimal("0.00")),
        (Decimal("0.00"), Decimal("-1.00")),
        (Decimal("10.00"), Decimal("10.00")),
        (Decimal("0.00"), Decimal("0.00")),
    ],
)
def test_journal_rejects_invalid_lines(
    debit: Decimal,
    credit: Decimal,
) -> None:
    with pytest.raises(InvalidJournalLineError):
        validate_balanced_journal(
            [
                JournalAmount(
                    debit=debit,
                    credit=credit,
                ),
                JournalAmount(
                    debit=Decimal("0.00"),
                    credit=Decimal("10.00"),
                ),
            ]
        )
