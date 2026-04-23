import pytest

from asian_fx_option.api import asian_fx_option_payout
from asian_fx_option.core import (
    AsianFXOptionSpec,
    AveragingMethod,
    CurrencyType,
    OptionType,
    QuotationType,
    SettlementType,
)


def _make_cash_spec(**overrides: object) -> AsianFXOptionSpec:
    defaults: dict[str, object] = {
        "option_type": OptionType.CALL,
        "is_floating_strike": False,
        "strike_fixed": 1.34,
        "strike_spread": 0.0,
        "quotation_type": QuotationType.DIRECT,
        "pair_scaling": 1,
        "notional_currency": CurrencyType.BASE,
        "notional_amount": 1_000_000.0,
        "averaging_method": AveragingMethod.ARITHMETIC,
        "settlement_currency": CurrencyType.QUOTE,
        "settlement_type": SettlementType.CASH,
    }
    defaults.update(overrides)
    return AsianFXOptionSpec(**defaults)  # type: ignore[arg-type]


def _make_physical_spec(**overrides: object) -> AsianFXOptionSpec:
    defaults: dict[str, object] = {
        "option_type": OptionType.CALL,
        "is_floating_strike": True,
        "strike_spread": 0.0,
        "quotation_type": QuotationType.DIRECT,
        "pair_scaling": 1,
        "notional_currency": CurrencyType.BASE,
        "notional_amount": 1_000_000.0,
        "averaging_method": AveragingMethod.ARITHMETIC,
        "settlement_currency": CurrencyType.QUOTE,
        "settlement_type": SettlementType.PHYSICAL,
    }
    defaults.update(overrides)
    return AsianFXOptionSpec(**defaults)  # type: ignore[arg-type]


class TestAsianFXOptionPayout:
    def test_cash_settlement_dispatches_correctly(self) -> None:
        spec = _make_cash_spec()
        result = asian_fx_option_payout([1.35], spec)
        assert result == pytest.approx(10_000.0)

    def test_physical_settlement_dispatches_correctly(self) -> None:
        spec = _make_physical_spec()
        result = asian_fx_option_payout([1.35, 1.36, 1.34], spec)
        assert result == pytest.approx(1.35)

    def test_cash_put_out_of_money(self) -> None:
        spec = _make_cash_spec(option_type=OptionType.PUT, strike_fixed=1.30)
        result = asian_fx_option_payout([1.35], spec)
        assert result == pytest.approx(0.0)

    def test_physical_with_spread(self) -> None:
        spec = _make_physical_spec(
            strike_spread=0.02,
            quotation_type=QuotationType.DIRECT,
            pair_scaling=100,
        )
        result = asian_fx_option_payout([0.85, 0.86, 0.84], spec)
        assert result == pytest.approx(0.87)
