from .core import (
    AsianFXOptionSpec,
    QuotationType,
    compute_strike,
    normalize_rate,
    normalize_spread,
    weighted_average,
)


def expected_strike_physical(
    raw_fixings: list[float],
    spec: AsianFXOptionSpec,
) -> float:
    """Return the expected strike in the original quotation convention (including scaling).

    For physical delivery the output is `K_original`, reconstructed from the normalised
    strike `K_norm` using the inverse of `normalize_rate`.
    """
    norm_fixings = [
        normalize_rate(f, spec.quotation_type, spec.pair_scaling) for f in raw_fixings
    ]
    avg = weighted_average(norm_fixings, spec.fixings_weights, spec.averaging_method)
    norm_spread = normalize_spread(spec.strike_spread, spec.quotation_type, spec.pair_scaling)
    k_norm = compute_strike(avg, spec, norm_spread)

    if spec.quotation_type == QuotationType.DIRECT:
        return k_norm * spec.pair_scaling
    return spec.pair_scaling / k_norm
