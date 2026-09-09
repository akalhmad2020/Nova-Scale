from dataclasses import dataclass
from typing import Literal
from uuid import UUID

ShipmentIdentifierKind = Literal[
    "uuid",
    "tracking_number",
    "reference",
]


@dataclass(frozen=True, slots=True)
class ResolvedShipment:
    shipment_id: UUID
    identifier: str
    identifier_kind: ShipmentIdentifierKind
