from enum import StrEnum


class ShipmentStatus(StrEnum):
    DRAFT = "draft"
    READY = "ready"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class ServiceType(StrEnum):
    STANDARD = "standard"
    EXPRESS = "express"


class WeightUnit(StrEnum):
    KG = "kg"
    LB = "lb"
