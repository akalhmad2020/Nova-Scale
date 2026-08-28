from collections.abc import Iterable
from decimal import ROUND_HALF_UP, Decimal

MONEY_QUANTUM = Decimal("0.01")


def round_money(value: Decimal) -> Decimal:
    return value.quantize(
        MONEY_QUANTUM,
        rounding=ROUND_HALF_UP,
    )


def calculate_line_amount(
    *,
    quantity: Decimal,
    unit_price: Decimal,
) -> Decimal:
    return round_money(quantity * unit_price)


def calculate_subtotal(
    amounts: Iterable[Decimal],
) -> Decimal:
    return round_money(sum(amounts, Decimal("0.00")))


def calculate_invoice_total(
    *,
    subtotal: Decimal,
    tax_amount: Decimal,
) -> Decimal:
    return round_money(subtotal + tax_amount)
