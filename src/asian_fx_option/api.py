from .cash_settlement import expected_cash_flow
from .core import AsianFXOptionSpec, SettlementType
from .physical_settlement import expected_strike_physical


def asian_fx_option_payout(fixings: list[float], spec: AsianFXOptionSpec) -> float:
    """Compute the Asian FX option payout or expected strike.

    Args:
        fixings: List of raw fixings in the original quotation convention.
        spec: Full option specification.

    Returns:
        For cash settlement: expected cash flow in the settlement currency.
        For physical settlement: expected strike in the original quotation convention.
    """
    if spec.settlement_type == SettlementType.CASH:
        return expected_cash_flow(fixings, spec)
    return expected_strike_physical(fixings, spec)
