from decimal import ROUND_HALF_UP, Decimal

from app.modules.shipments.domain.enums import WeightUnit

MONEY_QUANTUM = Decimal("0.01")
LB_TO_KG = Decimal("0.45359237")


def normalize_weight_to_kg(
    weight: Decimal,
    unit: WeightUnit,
) -> Decimal:
    if unit == WeightUnit.KG:
        return weight

    if unit == WeightUnit.LB:
        return weight * LB_TO_KG

    raise ValueError(f"Unsupported weight unit: {unit}")


def calculate_weight_charge(
    *,
    weight: Decimal,
    weight_unit: WeightUnit,
    price_per_kg: Decimal,
) -> Decimal:
    weight_kg = normalize_weight_to_kg(
        weight,
        weight_unit,
    )

    return (weight_kg * price_per_kg).quantize(
        MONEY_QUANTUM,
        rounding=ROUND_HALF_UP,
    )


def calculate_total_amount(
    *,
    base_amount: Decimal,
    surcharge_amount: Decimal,
) -> Decimal:
    return (base_amount + surcharge_amount).quantize(
        MONEY_QUANTUM,
        rounding=ROUND_HALF_UP,
    )
