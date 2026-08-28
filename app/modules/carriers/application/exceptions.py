class CarrierError(Exception):
    pass


class CarrierNotFoundError(CarrierError):
    pass


class CarrierCodeAlreadyExistsError(CarrierError):
    pass


class CarrierAlreadyInactiveError(CarrierError):
    pass


class CarrierServiceError(Exception):
    pass


class CarrierServiceNotFoundError(CarrierServiceError):
    pass


class CarrierServiceCodeAlreadyExistsError(CarrierServiceError):
    pass


class CarrierServiceAlreadyInactiveError(CarrierServiceError):
    pass


class CarrierInactiveError(CarrierServiceError):
    pass
