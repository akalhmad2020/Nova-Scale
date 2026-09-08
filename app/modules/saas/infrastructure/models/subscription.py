from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.modules.saas.domain.enums import PlanCode, SubscriptionStatus
from app.shared.infrastructure.database import Base
from app.shared.infrastructure.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class TenantSubscription(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "tenant_subscriptions"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            name="tenant_subscription_tenant_id",
        ),
        CheckConstraint(
            "plan_code IN ('starter', 'professional', 'enterprise')",
            name="plan_code_valid",
        ),
        CheckConstraint(
            "status IN ('active', 'past_due', 'canceled', 'suspended')",
            name="status_valid",
        ),
        Index(
            "ix_tenant_subscriptions_status",
            "status",
        ),
    )

    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )

    plan_code: Mapped[PlanCode] = mapped_column(
        SQLEnum(
            PlanCode,
            name="saas_plan_code",
            native_enum=True,
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
        default=PlanCode.STARTER,
        server_default=PlanCode.STARTER.value,
    )

    status: Mapped[SubscriptionStatus] = mapped_column(
        SQLEnum(
            SubscriptionStatus,
            name="saas_subscription_status",
            native_enum=True,
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
        default=SubscriptionStatus.ACTIVE,
        server_default=SubscriptionStatus.ACTIVE.value,
    )

    current_period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    cancel_at_period_end: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    provider_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
