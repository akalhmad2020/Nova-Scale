from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.modules.shipment_events.domain.enums import ShipmentEventType
from app.modules.shipments.domain.enums import ShipmentStatus
from app.shared.infrastructure.database import Base
from app.shared.infrastructure.mixins import (
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class ShipmentEvent(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "shipment_events"

    __table_args__ = (
        Index(
            "ix_shipment_events_tenant_id",
            "tenant_id",
        ),
        Index(
            "ix_shipment_events_shipment_id",
            "shipment_id",
        ),
        Index(
            "ix_shipment_events_occurred_at",
            "occurred_at",
        ),
        Index(
            "ix_shipment_events_shipment_occurred_at",
            "shipment_id",
            "occurred_at",
        ),
    )

    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "tenants.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    shipment_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "shipments.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    event_type: Mapped[ShipmentEventType] = mapped_column(
        String(50),
        nullable=False,
    )

    status: Mapped[ShipmentStatus | None] = mapped_column(
        String(50),
        nullable=True,
    )

    location_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "locations.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    metadata_: Mapped[dict[str, object] | None] = mapped_column(
        "metadata",
        JSONB,
        nullable=True,
    )

    created_by_user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )
