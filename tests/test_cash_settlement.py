import pytest

from asian_fx_option.cash_settlement import expected_cash_flow
from asian_fx_option.core import (
    AsianFXOptionSpec,
    AveragingMethod,
    CurrencyType,
    OptionType,
    QuotationType,
    SettlementType,
)
from asian_fx_option.exceptions import MissingSettlementFixingError, ZeroAverageRateError


def _make_spec(**overrides: object) -> AsianFXOptionSpec:
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
        "settlement_type": SettlementType.CASH,
    }
    defaults.update(overrides)
    return AsianFXOptionSpec(**defaults)  # type: ignore[arg-type]


class TestExpectedCashFlow:
    def test_example1_notional_base_settle_quote(self) -> None:
        """Research Example 1: Call, notional=1M USD base, S_avg=1.35, K=1.34."""
        spec = _make_spec(
            option_type=OptionType.CALL,
            is_floating_strike=False,
            strike_fixed=1.34,
            strike_spread=0.0,
            notional_amount=1_000_000.0,
            notional_currency=CurrencyType.BASE,
            settlement_currency=CurrencyType.QUOTE,
        )
        result = expected_cash_flow([1.35], spec)
        # payoff_per_base = 1.35 - 1.34 = 0.01, base_notional = 1M, total = 10_000
        assert result == pytest.approx(10_000.0)

    def test_example2_notional_quote_settle_quote(self) -> None:
        """Research Example 2: notional=1.35M SGD quote -> same result as Example 1."""
        spec = _make_spec(
            option_type=OptionType.CALL,
            is_floating_strike=False,
            strike_fixed=1.34,
            strike_spread=0.0,
            notional_amount=1_350_000.0,
            notional_currency=CurrencyType.QUOTE,
            settlement_currency=CurrencyType.QUOTE,
        )
        result = expected_cash_flow([1.35], spec)
        # base_notional = 1_350_000 / 1.35 = 1_000_000, payoff = 0.01, total = 10_000
        assert result == pytest.approx(10_000.0)

    def test_example3_notional_quote_settle_base(self) -> None:
        """Research Example 3: settle in base with settlement_fixing=1.35."""
        spec = _make_spec(
            option_type=OptionType.CALL,
            is_floating_strike=False,
            strike_fixed=1.34,
            strike_spread=0.0,
            notional_amount=1_350_000.0,
            notional_currency=CurrencyType.QUOTE,
            settlement_currency=CurrencyType.BASE,
            settlement_fixing=1.35,
        )
        result = expected_cash_flow([1.35], spec)
        # total_payoff_quote = 10_000, settle_rate = 1.35, result = 10_000/1.35
        assert result == pytest.approx(10_000.0 / 1.35, rel=1e-9)

    def test_example3_different_settlement_fixing(self) -> None:
        spec = _make_spec(
            option_type=OptionType.CALL,
            is_floating_strike=False,
            strike_fixed=1.34,
            strike_spread=0.0,
            notional_amount=1_350_000.0,
            notional_currency=CurrencyType.QUOTE,
            settlement_currency=CurrencyType.BASE,
            settlement_fixing=1.36,
        )
        result = expected_cash_flow([1.35], spec)
        assert result == pytest.approx(10_000.0 / 1.36, rel=1e-9)

    def test_put_option_in_the_money(self) -> None:
        spec = _make_spec(
            option_type=OptionType.PUT,
            is_floating_strike=False,
            strike_fixed=1.36,
            strike_spread=0.0,
            notional_amount=1_000_000.0,
            notional_currency=CurrencyType.BASE,
            settlement_currency=CurrencyType.QUOTE,
        )
        result = expected_cash_flow([1.35], spec)
        # payoff = max(0, 1.36 - 1.35) = 0.01, total = 10_000
        assert result == pytest.approx(10_000.0)

    def test_call_out_of_money_returns_zero(self) -> None:
        spec = _make_spec(
            option_type=OptionType.CALL,
            is_floating_strike=False,
            strike_fixed=1.36,
            strike_spread=0.0,
            notional_amount=1_000_000.0,
        )
        result = expected_cash_flow([1.35], spec)
        assert result == pytest.approx(0.0)

    def test_put_out_of_money_returns_zero(self) -> None:
        spec = _make_spec(
            option_type=OptionType.PUT,
            is_floating_strike=False,
            strike_fixed=1.34,
            strike_spread=0.0,
            notional_amount=1_000_000.0,
        )
        result = expected_cash_flow([1.35], spec)
        assert result == pytest.approx(0.0)

    def test_floating_strike_zero_spread_atm(self) -> None:
        """Floating strike with zero spread means strike equals S_avg → zero payoff."""
        spec = _make_spec(strike_spread=0.0)
        result = expected_cash_flow([1.35, 1.35], spec)
        assert result == pytest.approx(0.0)

    def test_floating_strike_positive_spread_call(self) -> None:
        spec = _make_spec(
            option_type=OptionType.CALL,
            strike_spread=-0.01,  # negative spread lowers strike → call is ITM
            quotation_type=QuotationType.DIRECT,
            pair_scaling=1,
            notional_amount=1_000_000.0,
        )
        result = expected_cash_flow([1.35], spec)
        # K_norm = 1.35 + (-0.01) = 1.34, payoff = 0.01 * 1M = 10_000
        assert result == pytest.approx(10_000.0)

    def test_arithmetic_multiple_fixings(self) -> None:
        spec = _make_spec(
            option_type=OptionType.CALL,
            is_floating_strike=False,
            strike_fixed=1.345,
            strike_spread=0.0,
            notional_amount=1_000_000.0,
        )
        result = expected_cash_flow([1.34, 1.35, 1.36], spec)
        # S_avg = 1.35, K = 1.345, payoff = 0.005 * 1M = 5_000
        assert result == pytest.approx(5_000.0)

    def test_harmonic_averaging(self) -> None:
        fixings = [0.0085, 0.0086, 0.0084]
        harm_avg = 3.0 / (1 / 0.0085 + 1 / 0.0086 + 1 / 0.0084)
        spec = _make_spec(
            option_type=OptionType.CALL,
            is_floating_strike=False,
            strike_fixed=harm_avg * 0.99,  # slightly below harmonic avg -> ITM
            strike_spread=0.0,
            quotation_type=QuotationType.DIRECT,
            pair_scaling=1,
            notional_amount=1_000_000.0,
            averaging_method=AveragingMethod.HARMONIC,
        )
        result = expected_cash_flow(fixings, spec)
        assert result == pytest.approx(harm_avg * 0.01 * 1_000_000, rel=1e-6)

    def test_custom_weights_cash(self) -> None:
        spec = _make_spec(
            option_type=OptionType.CALL,
            is_floating_strike=False,
            strike_fixed=1.375,
            strike_spread=0.0,
            notional_amount=1_000_000.0,
            fixings_weights=[1.0, 3.0],
        )
        fixings = [1.30, 1.40]
        # S_avg = 0.25*1.30 + 0.75*1.40 = 1.375 -> payoff = 0
        result = expected_cash_flow(fixings, spec)
        assert result == pytest.approx(0.0)

    def test_direct_scale100_with_fixings(self) -> None:
        spec = _make_spec(
            option_type=OptionType.CALL,
            is_floating_strike=False,
            strike_fixed=0.84,
            strike_spread=0.0,
            quotation_type=QuotationType.DIRECT,
            pair_scaling=100,
            notional_amount=1_000_000.0,
            notional_currency=CurrencyType.BASE,
            settlement_currency=CurrencyType.QUOTE,
        )
        fixings = [0.85, 0.86, 0.84]
        # S_avg_norm = mean([0.0085, 0.0086, 0.0084]) = 0.0085
        # K_norm = 0.84/100 = 0.0084
        # payoff = 0.0001 * 1M = 100
        result = expected_cash_flow(fixings, spec)
        assert result == pytest.approx(100.0, rel=1e-9)

    def test_indirect_quotation_cash(self) -> None:
        """Indirect quote: raw=1.2 -> norm=1/1.2; call ITM if strike_fixed < S_avg."""
        spec = _make_spec(
            option_type=OptionType.CALL,
            is_floating_strike=False,
            strike_fixed=1.25,  # normalised = 1/1.25 = 0.8
            strike_spread=0.0,
            quotation_type=QuotationType.INDIRECT,
            pair_scaling=1,
            notional_amount=1_000_000.0,
        )
        fixings = [1.2]
        # S_avg_norm = 1/1.2 = 0.8333; K_norm = 1/1.25 = 0.8
        # payoff = 0.8333 - 0.8 = 0.0333; total = 33_333.33
        result = expected_cash_flow(fixings, spec)
        assert result == pytest.approx((1 / 1.2 - 1 / 1.25) * 1_000_000, rel=1e-6)

    def test_missing_settlement_fixing_raises(self) -> None:
        spec = _make_spec(
            settlement_currency=CurrencyType.BASE,
            settlement_fixing=None,
        )
        with pytest.raises(MissingSettlementFixingError):
            expected_cash_flow([1.35], spec)

    def test_zero_average_with_quote_notional_raises(self) -> None:
        """S_avg=0 with quote notional is invalid."""
        spec = _make_spec(
            is_floating_strike=False,
            strike_fixed=0.0,
            notional_currency=CurrencyType.QUOTE,
        )
        with pytest.raises((ZeroAverageRateError, ZeroDivisionError, Exception)):
            # Zero fixings make S_avg=0
            expected_cash_flow([0.0], spec)
