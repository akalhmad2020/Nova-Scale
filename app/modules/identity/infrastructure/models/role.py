from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.infrastructure.database import Base
from app.shared.infrastructure.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Role(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
    )

    description: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
