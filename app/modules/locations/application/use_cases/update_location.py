from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from app.modules.locations.application.exceptions import (
    LocationCodeAlreadyExistsError,
    LocationNotFoundError,
)
from app.modules.locations.application.ports.unit_of_work import UnitOfWork
from app.modules.locations.domain.enums import LocationType
from app.modules.locations.infrastructure.models.location import Location


@dataclass(frozen=True, slots=True)
class UpdateLocationCommand:
    tenant_id: UUID
    location_id: UUID
    name: str
    code: str
    type: LocationType
    country_code: str
    city: str
    address_line1: str
    state: str | None = None
    postal_code: str | None = None
    address_line2: str | None = None
    contact_name: str | None = None
    email: str | None = None
    phone: str | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    notes: str | None = None


class UpdateLocation:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        command: UpdateLocationCommand,
    ) -> Location:
        name = command.name.strip()
        code = command.code.strip().upper()
        country_code = command.country_code.strip().upper()
        city = command.city.strip()
        address_line1 = command.address_line1.strip()

        state = command.state.strip() if command.state is not None else None

        postal_code = command.postal_code.strip() if command.postal_code is not None else None

        address_line2 = command.address_line2.strip() if command.address_line2 is not None else None

        contact_name = command.contact_name.strip() if command.contact_name is not None else None

        email = command.email.strip().lower() if command.email is not None else None

        phone = command.phone.strip() if command.phone is not None else None

        notes = command.notes.strip() if command.notes is not None else None

        async with self._unit_of_work as uow:
            location = await uow.locations.get_by_id_and_tenant(
                command.location_id,
                command.tenant_id,
            )

            if location is None:
                raise LocationNotFoundError

            existing = await uow.locations.get_by_code_and_tenant(
                code,
                command.tenant_id,
            )

            if existing is not None and existing.id != location.id:
                raise LocationCodeAlreadyExistsError

            location.name = name
            location.code = code
            location.type = command.type
            location.country_code = country_code
            location.state = state
            location.city = city
            location.postal_code = postal_code
            location.address_line1 = address_line1
            location.address_line2 = address_line2
            location.contact_name = contact_name
            location.email = email
            location.phone = phone
            location.latitude = command.latitude
            location.longitude = command.longitude
            location.notes = notes

            await uow.flush()
            await uow.commit()
            await uow.refresh(location)

            return location
