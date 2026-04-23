class AsianFXOptionError(Exception):
    """Base exception for Asian FX Option library."""


class InvalidWeightsError(AsianFXOptionError):
    """Raised when weights are invalid (negative, wrong count, or zero sum)."""


class ZeroDivisionInAverageError(AsianFXOptionError):
    """Raised when harmonic average encounters a zero fixing."""


class MissingSettlementFixingError(AsianFXOptionError):
    """Raised when settlement_fixing is required but not provided."""


class ZeroAverageRateError(AsianFXOptionError):
    """Raised when S_avg is zero and quote notional conversion is attempted."""


class MissingFixedStrikeError(AsianFXOptionError):
    """Raised when is_floating_strike=False but strike_fixed is not provided."""
