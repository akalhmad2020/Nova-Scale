from enum import StrEnum


class ShipmentEventType(StrEnum):
    CREATED = "created"
    STATUS_CHANGED = "status_changed"
    PICKED_UP = "picked_up"
    ARRIVED_AT_LOCATION = "arrived_at_location"
    DEPARTED_LOCATION = "departed_location"
    NOTE_ADDED = "note_added"
