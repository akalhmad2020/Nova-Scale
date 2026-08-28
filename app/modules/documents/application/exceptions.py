class DocumentError(Exception):
    pass


class DocumentNotFoundError(DocumentError):
    pass


class ShipmentNotFoundError(DocumentError):
    pass


class PackageNotFoundError(DocumentError):
    pass


class PackageShipmentMismatchError(DocumentError):
    pass


class CarrierNotFoundError(DocumentError):
    pass


class CarrierServiceNotFoundError(DocumentError):
    pass


class CarrierServiceMismatchError(DocumentError):
    pass


class DocumentShipmentMismatchError(DocumentError):
    pass


class InvalidShippingLabelDocumentError(DocumentError):
    pass


class InvalidDocumentStateTransitionError(DocumentError):
    pass


class ShipmentLabelError(Exception):
    pass


class ShipmentLabelNotFoundError(ShipmentLabelError):
    pass


class ShipmentLabelAlreadyVoidedError(ShipmentLabelError):
    pass


class InvalidShipmentLabelStateTransitionError(ShipmentLabelError):
    pass
