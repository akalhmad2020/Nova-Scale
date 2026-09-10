from dataclasses import dataclass
from typing import Literal
from uuid import UUID

ShipmentIdentifierKind = Literal[
    "uuid",
    "tracking_number",
    "reference",
]

MultiShipmentResolutionStatus = Literal[
    "resolved",
    "not_found",
    "ambiguous",
]


@dataclass(frozen=True, slots=True)
class ResolvedShipment:
    shipment_id: UUID
    identifier: str
    identifier_kind: ShipmentIdentifierKind


@dataclass(frozen=True, slots=True)
class MultiShipmentResolutionItem:
    identifier: str
    status: MultiShipmentResolutionStatus
    shipment_id: UUID | None = None
    identifier_kind: ShipmentIdentifierKind | None = None
