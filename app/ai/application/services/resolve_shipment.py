from uuid import UUID

from app.ai.application.agent.shipment_resolution_exceptions import (
    ShipmentIdentifierAmbiguousError,
)
from app.ai.application.agent.shipment_resolution_models import (
    ResolvedShipment,
)
from app.modules.shipments.application.exceptions import ShipmentNotFoundError
from app.modules.shipments.application.ports.unit_of_work import UnitOfWork


class ResolveShipmentService:
    def __init__(
        self,
        *,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        *,
        tenant_id: UUID,
        identifier: str,
    ) -> ResolvedShipment:
        normalized_identifier = identifier.strip()

        if not normalized_identifier:
            raise ShipmentNotFoundError

        async with self._unit_of_work as uow:
            shipment_id = self._parse_uuid(
                normalized_identifier,
            )

            if shipment_id is not None:
                shipment = await uow.shipments.get_by_id_and_tenant(
                    shipment_id,
                    tenant_id,
                )

                if shipment is None:
                    raise ShipmentNotFoundError

                return ResolvedShipment(
                    shipment_id=shipment.id,
                    identifier=normalized_identifier,
                    identifier_kind="uuid",
                )

            shipment = await uow.shipments.get_by_tracking_number_and_tenant(
                normalized_identifier,
                tenant_id,
            )

            if shipment is not None:
                return ResolvedShipment(
                    shipment_id=shipment.id,
                    identifier=normalized_identifier,
                    identifier_kind="tracking_number",
                )

            reference_matches = await uow.shipments.list_by_reference_and_tenant(
                normalized_identifier,
                tenant_id,
            )

            if not reference_matches:
                raise ShipmentNotFoundError

            if len(reference_matches) > 1:
                raise ShipmentIdentifierAmbiguousError(
                    "Shipment reference matches multiple shipments"
                )

            resolved_shipment = reference_matches[0]

            return ResolvedShipment(
                shipment_id=resolved_shipment.id,
                identifier=normalized_identifier,
                identifier_kind="reference",
            )

    @staticmethod
    def _parse_uuid(
        value: str,
    ) -> UUID | None:
        try:
            return UUID(value)
        except ValueError:
            return None
