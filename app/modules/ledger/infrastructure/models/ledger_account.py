from __future__ import annotations

from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKeyConstraint, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.modules.ledger.domain.enums import (
    LedgerAccountStatus,
)
from app.shared.infrastructure.database import Base
from app.shared.infrastructure.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class LedgerAccount(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ledger_accounts"

    tenant_id: Mapped[UUID] = mapped_column(nullable=False)

    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)

    type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    purpose: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=LedgerAccountStatus.ACTIVE,
        server_default=LedgerAccountStatus.ACTIVE.value,
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "id",
            name="ledger_account_tenant_id",
        ),
        UniqueConstraint(
            "tenant_id",
            "code",
            name="ledger_account_tenant_code",
        ),
        UniqueConstraint(
            "tenant_id",
            "purpose",
            name="ledger_account_tenant_purpose",
        ),
        ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "type IN ('asset', 'liability', 'equity', 'revenue', 'expense')",
            name="account_type",
        ),
        CheckConstraint(
            "purpose IN ('accounts_receivable', 'revenue', 'cash', 'tax_payable')",
            name="account_purpose",
        ),
        CheckConstraint(
            "status IN ('active', 'inactive')",
            name="account_status",
        ),
        CheckConstraint(
            "btrim(code) <> ''",
            name="account_code_not_blank",
        ),
        CheckConstraint(
            "btrim(name) <> ''",
            name="account_name_not_blank",
        ),
    )
