from .core import (
    AsianFXOptionSpec,
    CurrencyType,
    OptionType,
    compute_strike,
    normalize_rate,
    normalize_spread,
    weighted_average,
)
from .exceptions import MissingSettlementFixingError, ZeroAverageRateError


def expected_cash_flow(
    raw_fixings: list[float],
    spec: AsianFXOptionSpec,
) -> float:
    """Return the expected settlement cash flow in the settlement currency.

    Steps:
        1. Normalise fixings and compute weighted average S_avg.
        2. Normalise spread and compute normalised strike K_norm.
        3. Calculate payoff per unit of base currency.
        4. Convert notional to base notional using S_avg.
        5. Compute total payoff in quote currency.
        6. Convert to settlement currency using settlement_fixing if required.
    """
    norm_fixings = [
        normalize_rate(f, spec.quotation_type, spec.pair_scaling) for f in raw_fixings
    ]
    s_avg = weighted_average(norm_fixings, spec.fixings_weights, spec.averaging_method)

    norm_spread = normalize_spread(spec.strike_spread, spec.quotation_type, spec.pair_scaling)
    k_norm = compute_strike(s_avg, spec, norm_spread)

    if spec.option_type == OptionType.CALL:
        payoff_per_base = max(0.0, s_avg - k_norm)
    else:
        payoff_per_base = max(0.0, k_norm - s_avg)

    if spec.notional_currency == CurrencyType.BASE:
        base_notional = spec.notional_amount
    else:
        if s_avg == 0.0:
            raise ZeroAverageRateError(
                "Cannot convert quote notional to base when S_avg is zero"
            )
        base_notional = spec.notional_amount / s_avg

    total_payoff_quote = base_notional * payoff_per_base

    if spec.settlement_currency == CurrencyType.QUOTE:
        return total_payoff_quote

    if spec.settlement_fixing is None:
        raise MissingSettlementFixingError(
            "settlement_fixing must be provided when settlement_currency == BASE"
        )
    settle_rate_norm = normalize_rate(
        spec.settlement_fixing, spec.quotation_type, spec.pair_scaling
    )
    return total_payoff_quote / settle_rate_norm
