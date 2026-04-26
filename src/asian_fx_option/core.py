from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from .exceptions import (
    InvalidWeightsError,
    MissingFixedStrikeError,
    ZeroDivisionInAverageError,
)


class OptionType(Enum):
    CALL = "call"
    PUT = "put"


class QuotationType(Enum):
    DIRECT = "direct"
    INDIRECT = "indirect"


class AveragingMethod(Enum):
    ARITHMETIC = "arithmetic"
    HARMONIC = "harmonic"


class SettlementType(Enum):
    CASH = "cash"
    PHYSICAL = "physical"


class CurrencyType(Enum):
    BASE = "base"
    QUOTE = "quote"


@dataclass
class AsianFXOptionSpec:
    """Specification for an Asian FX option.

    All monetary/rate parameters use the original quotation convention
    (including scaling). Internally the library normalises to quote-per-base.
    """

    option_type: OptionType
    is_floating_strike: bool
    strike_spread: float
    quotation_type: QuotationType
    pair_scaling: int
    notional_currency: CurrencyType
    notional_amount: float
    averaging_method: AveragingMethod
    settlement_currency: CurrencyType
    settlement_type: SettlementType
    strike_multiplier: float = field(default=1.0)
    strike_fixed: Optional[float] = field(default=None)
    final_rate_raw: Optional[float] = field(default=None)
    fixings_weights: Optional[list[float]] = field(default=None)
    rounding_decimals: Optional[int] = field(default=None)
    settlement_fixing: Optional[float] = field(default=None)


def normalize_rate(raw_rate: float, quotation: QuotationType, scale: int) -> float:
    """Convert a raw rate (original quotation with scaling) to quote per 1 base."""
    if quotation == QuotationType.DIRECT:
        return raw_rate / scale
    return scale / raw_rate


def normalize_spread(raw_spread: float, quotation: QuotationType, scale: int) -> float:
    """Normalise an additive spread to quote-per-base space.

    A zero spread is always zero in normalised space regardless of quotation.
    Non-zero spreads are normalised with the same formula as rates.
    """
    if raw_spread == 0.0:
        return 0.0
    return normalize_rate(raw_spread, quotation, scale)


def weighted_average(
    values: list[float],
    weights: Optional[list[float]],
    method: AveragingMethod,
) -> float:
    """Compute weighted arithmetic or harmonic average of normalised fixings.

    Weights are normalised to sum to 1. If weights is None, equal weights are used.
    """
    n = len(values)
    if weights is None:
        normalised: list[float] = [1.0 / n] * n
    else:
        if len(weights) != n:
            raise InvalidWeightsError(
                f"Number of weights ({len(weights)}) must equal number of values ({n})"
            )
        if any(w < 0 for w in weights):
            raise InvalidWeightsError("Weights must be non-negative")
        total = sum(weights)
        if total == 0:
            raise InvalidWeightsError("Sum of weights cannot be zero")
        normalised = [w / total for w in weights]

    if method == AveragingMethod.ARITHMETIC:
        return sum(w * v for w, v in zip(normalised, values))

    # HARMONIC
    for v in values:
        if v == 0.0:
            raise ZeroDivisionInAverageError(
                "Harmonic average requires all fixings to be non-zero"
            )
    return 1.0 / sum(w / v for w, v in zip(normalised, values))


def compute_strike(
    avg_reference: float,
    spec: AsianFXOptionSpec,
    normalized_spread: float,
) -> float:
    """Compute the normalised strike (quote per base), applying rounding if specified."""
    if spec.is_floating_strike:
        k_norm = spec.strike_multiplier * avg_reference + normalized_spread
    else:
        if spec.strike_fixed is None:
            raise MissingFixedStrikeError(
                "strike_fixed must be provided when is_floating_strike=False"
            )
        k_norm = normalize_rate(spec.strike_fixed, spec.quotation_type, spec.pair_scaling)

    if spec.rounding_decimals is not None:
        k_norm = round(k_norm, spec.rounding_decimals)
    return k_norm
