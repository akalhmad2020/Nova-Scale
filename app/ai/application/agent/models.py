from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ShipmentToolResult:
    id: UUID
    tracking_number: str
    reference: str | None
    status: str
    service_type: str
    description: str | None
    weight: str
    weight_unit: str
    notes: str | None
