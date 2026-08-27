from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.packages.domain.enums import DimensionUnit
from app.modules.shipments.domain.enums import WeightUnit


class PackageDimensionsMixin(BaseModel):
    length: Decimal | None = Field(
        default=None,
        gt=0,
    )
    width: Decimal | None = Field(
        default=None,
        gt=0,
    )
    height: Decimal | None = Field(
        default=None,
        gt=0,
    )
    dimension_unit: DimensionUnit | None = None

    @model_validator(mode="after")
    def validate_dimensions(self) -> "PackageDimensionsMixin":
        dimensions = (
            self.length,
            self.width,
            self.height,
        )

        has_any_dimension = any(value is not None for value in dimensions)

        has_all_dimensions = all(value is not None for value in dimensions)

        if has_any_dimension and not has_all_dimensions:
            raise ValueError("length, width, and height must be provided together")

        if has_all_dimensions and self.dimension_unit is None:
            raise ValueError("dimension_unit is required when dimensions are provided")

        if not has_any_dimension and self.dimension_unit is not None:
            raise ValueError("dimension_unit requires package dimensions")

        return self


class CreatePackageRequest(PackageDimensionsMixin):
    package_number: str = Field(
        min_length=1,
        max_length=100,
    )

    description: str | None = Field(
        default=None,
        max_length=500,
    )

    weight: Decimal = Field(
        gt=0,
    )

    weight_unit: WeightUnit

    notes: str | None = None


class UpdatePackageRequest(PackageDimensionsMixin):
    shipment_id: UUID

    package_number: str = Field(
        min_length=1,
        max_length=100,
    )

    description: str | None = Field(
        default=None,
        max_length=500,
    )

    weight: Decimal = Field(
        gt=0,
    )

    weight_unit: WeightUnit

    notes: str | None = None


class PackageResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID
    tenant_id: UUID
    shipment_id: UUID

    package_number: str
    description: str | None

    weight: Decimal
    weight_unit: WeightUnit

    length: Decimal | None
    width: Decimal | None
    height: Decimal | None
    dimension_unit: DimensionUnit | None

    notes: str | None

    created_at: datetime
    updated_at: datetime
