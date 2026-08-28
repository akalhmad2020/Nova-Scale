class PricingRuleError(Exception):
    """Base exception for pricing rule application errors."""


class PricingRuleNotFoundError(PricingRuleError):
    """Raised when a pricing rule cannot be found."""


class PricingShipmentNotFoundError(PricingRuleError):
    """Raised when a shipment cannot be found for the tenant."""


class PricingRuleInactiveError(PricingRuleError):
    """Raised when an inactive pricing rule is used."""


class PricingRuleServiceMismatchError(PricingRuleError):
    """Raised when the pricing rule does not match the shipment service."""


class PricingRuleNotEffectiveError(PricingRuleError):
    """Raised when the pricing rule is outside its validity period."""


class PricingRuleAlreadyInactiveError(PricingRuleError):
    """Raised when trying to deactivate an inactive pricing rule."""


class PricingRuleInvalidValidityRangeError(PricingRuleError):
    pass
