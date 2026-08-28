from decimal import Decimal

from app.modules.pricing.domain.calculator import (
    calculate_total_amount,
    calculate_weight_charge,
)
from app.modules.shipments.domain.enums import WeightUnit


def test_calculate_weight_charge_for_kg() -> None:
    result = calculate_weight_charge(
        weight=Decimal("10.000"),
        weight_unit=WeightUnit.KG,
        price_per_kg=Decimal("3.5000"),
    )

    assert result == Decimal("35.00")


def test_calculate_weight_charge_converts_lb_to_kg() -> None:
    result = calculate_weight_charge(
        weight=Decimal("10.000"),
        weight_unit=WeightUnit.LB,
        price_per_kg=Decimal("3.0000"),
    )

    assert result == Decimal("13.61")


def test_calculate_total_amount() -> None:
    result = calculate_total_amount(
        base_amount=Decimal("25.00"),
        surcharge_amount=Decimal("40.00"),
    )

    assert result == Decimal("65.00")
