from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from app.modules.locations.application.exceptions import (
    LocationCodeAlreadyExistsError,
)
from app.modules.locations.application.ports.unit_of_work import UnitOfWork
from app.modules.locations.domain.enums import (
    LocationStatus,
    LocationType,
)
from app.modules.locations.infrastructure.models.location import Location


@dataclass(frozen=True, slots=True)
class CreateLocationCommand:
    tenant_id: UUID
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


class CreateLocation:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        command: CreateLocationCommand,
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
            existing = await uow.locations.get_by_code_and_tenant(
                code,
                command.tenant_id,
            )

            if existing is not None:
                raise LocationCodeAlreadyExistsError

            location = Location(
                tenant_id=command.tenant_id,
                name=name,
                code=code,
                type=command.type,
                contact_name=contact_name,
                email=email,
                phone=phone,
                country_code=country_code,
                state=state,
                city=city,
                postal_code=postal_code,
                address_line1=address_line1,
                address_line2=address_line2,
                latitude=command.latitude,
                longitude=command.longitude,
                status=LocationStatus.ACTIVE,
                notes=notes,
            )

            uow.locations.add(location)

            await uow.flush()
            await uow.commit()
            await uow.refresh(location)

            return location
