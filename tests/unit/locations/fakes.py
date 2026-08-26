from types import TracebackType
from uuid import UUID

from app.modules.locations.infrastructure.models.location import Location


class FakeLocationRepository:
    def __init__(self) -> None:
        self._locations: list[Location] = []

    async def get_by_id(
        self,
        location_id: UUID,
    ) -> Location | None:
        for location in self._locations:
            if location.id == location_id and location.deleted_at is None:
                return location

        return None

    async def get_by_id_and_tenant(
        self,
        location_id: UUID,
        tenant_id: UUID,
    ) -> Location | None:
        for location in self._locations:
            if (
                location.id == location_id
                and location.tenant_id == tenant_id
                and location.deleted_at is None
            ):
                return location

        return None

    async def get_by_code_and_tenant(
        self,
        code: str,
        tenant_id: UUID,
    ) -> Location | None:
        for location in self._locations:
            if (
                location.code == code
                and location.tenant_id == tenant_id
                and location.deleted_at is None
            ):
                return location

        return None

    async def list_by_tenant(
        self,
        tenant_id: UUID,
    ) -> list[Location]:
        return [
            location
            for location in self._locations
            if (location.tenant_id == tenant_id and location.deleted_at is None)
        ]

    def add(
        self,
        location: Location,
    ) -> None:
        self._locations.append(location)


class FakeUnitOfWork:
    def __init__(self) -> None:
        self.locations = FakeLocationRepository()

        self.flushed = False
        self.committed = False
        self.rolled_back = False
        self.refreshed = False

    async def __aenter__(self) -> "FakeUnitOfWork":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            await self.rollback()

    async def flush(self) -> None:
        self.flushed = True

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True

    async def refresh(
        self,
        location: Location,
    ) -> None:
        self.refreshed = True
