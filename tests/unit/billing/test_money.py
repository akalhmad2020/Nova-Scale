from decimal import Decimal

from app.modules.billing.domain.money import (
    calculate_invoice_total,
    calculate_line_amount,
    calculate_subtotal,
    round_money,
)


def test_round_money_to_two_decimal_places() -> None:
    assert round_money(Decimal("10.125")) == Decimal("10.13")


def test_round_money_uses_half_up_rounding() -> None:
    assert round_money(Decimal("10.115")) == Decimal("10.12")


def test_calculate_line_amount() -> None:
    amount = calculate_line_amount(
        quantity=Decimal("2.0000"),
        unit_price=Decimal("10.50"),
    )

    assert amount == Decimal("21.00")


def test_calculate_line_amount_rounds_to_two_decimal_places() -> None:
    amount = calculate_line_amount(
        quantity=Decimal("1.2345"),
        unit_price=Decimal("10.99"),
    )

    assert amount == Decimal("13.57")


def test_calculate_subtotal() -> None:
    subtotal = calculate_subtotal(
        [
            Decimal("10.25"),
            Decimal("20.50"),
            Decimal("5.00"),
        ]
    )

    assert subtotal == Decimal("35.75")


def test_calculate_subtotal_for_empty_collection() -> None:
    assert calculate_subtotal([]) == Decimal("0.00")


def test_calculate_invoice_total() -> None:
    total = calculate_invoice_total(
        subtotal=Decimal("100.00"),
        tax_amount=Decimal("15.50"),
    )

    assert total == Decimal("115.50")
