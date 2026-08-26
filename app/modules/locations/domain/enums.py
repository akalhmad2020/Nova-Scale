from enum import StrEnum


class LocationStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class LocationType(StrEnum):
    WAREHOUSE = "warehouse"
    OFFICE = "office"
    STORE = "store"
    PICKUP = "pickup"
    DELIVERY = "delivery"
    OTHER = "other"
