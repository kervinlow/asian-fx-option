import pytest

from asian_fx_option.core import (
    AsianFXOptionSpec,
    AveragingMethod,
    CurrencyType,
    OptionType,
    QuotationType,
    SettlementType,
)
from asian_fx_option.physical_settlement import expected_strike_physical


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
        "settlement_type": SettlementType.PHYSICAL,
    }
    defaults.update(overrides)
    return AsianFXOptionSpec(**defaults)  # type: ignore[arg-type]


class TestExpectedStrikePhysical:
    def test_example4_from_research(self) -> None:
        """Research doc Example 4: direct, scale=100, arithmetic, spread=0.02."""
        spec = _make_spec(
            strike_spread=0.02,
            quotation_type=QuotationType.DIRECT,
            pair_scaling=100,
        )
        raw_fixings = [0.85, 0.86, 0.84]
        result = expected_strike_physical(raw_fixings, spec)
        # S_avg_norm = mean([0.0085, 0.0086, 0.0084]) = 0.0085
        # K_norm = 0.0085 + 0.0002 = 0.0087
        # K_original = 0.0087 * 100 = 0.87
        assert result == pytest.approx(0.87, rel=1e-9)

    def test_single_fixing_direct(self) -> None:
        spec = _make_spec(quotation_type=QuotationType.DIRECT, pair_scaling=1)
        result = expected_strike_physical([1.35], spec)
        assert result == pytest.approx(1.35)

    def test_direct_no_spread_returns_average(self) -> None:
        spec = _make_spec(quotation_type=QuotationType.DIRECT, pair_scaling=1)
        result = expected_strike_physical([1.34, 1.35, 1.36], spec)
        assert result == pytest.approx(1.35)

    def test_indirect_scale_1_no_spread(self) -> None:
        spec = _make_spec(
            strike_spread=0.0,
            quotation_type=QuotationType.INDIRECT,
            pair_scaling=1,
            averaging_method=AveragingMethod.ARITHMETIC,
        )
        raw_fixings = [1.2, 1.2]
        result = expected_strike_physical(raw_fixings, spec)
        # norm = 1/1.2 each, avg_norm = 1/1.2, K_original = 1 / (1/1.2) = 1.2
        assert result == pytest.approx(1.2)

    def test_floating_with_multiplier_direct(self) -> None:
        spec = _make_spec(
            strike_multiplier=0.99,
            quotation_type=QuotationType.DIRECT,
            pair_scaling=1,
        )
        result = expected_strike_physical([1.35, 1.35], spec)
        # K_norm = 0.99 * 1.35 = 1.3365 -> K_original = 1.3365
        assert result == pytest.approx(1.3365)

    def test_rounding_in_original_convention(self) -> None:
        """Rounding is applied to K_norm before converting back."""
        spec = _make_spec(
            strike_spread=0.02,
            quotation_type=QuotationType.DIRECT,
            pair_scaling=100,
            rounding_decimals=4,
        )
        raw_fixings = [0.85, 0.86, 0.84]
        result = expected_strike_physical(raw_fixings, spec)
        # K_norm = 0.0087 (already 4dp), K_original = 0.87
        assert result == pytest.approx(0.87)

    def test_harmonic_arithmetic_differ(self) -> None:
        spec_arith = _make_spec(
            quotation_type=QuotationType.DIRECT,
            pair_scaling=1,
            averaging_method=AveragingMethod.ARITHMETIC,
        )
        spec_harm = _make_spec(
            quotation_type=QuotationType.DIRECT,
            pair_scaling=1,
            averaging_method=AveragingMethod.HARMONIC,
        )
        fixings = [1.0, 2.0]
        arith = expected_strike_physical(fixings, spec_arith)
        harm = expected_strike_physical(fixings, spec_harm)
        assert arith == pytest.approx(1.5)
        # harmonic mean of 1 and 2 = 2/(1+0.5) = 4/3
        assert harm == pytest.approx(4.0 / 3.0, rel=1e-9)

    def test_fixed_strike_physical(self) -> None:
        spec = _make_spec(
            is_floating_strike=False,
            strike_fixed=1.34,
            quotation_type=QuotationType.DIRECT,
            pair_scaling=1,
        )
        # Fixed strike ignores fixings for strike; still must process them for physical
        result = expected_strike_physical([1.35, 1.36], spec)
        assert result == pytest.approx(1.34)

    def test_custom_weights_physical(self) -> None:
        spec = _make_spec(
            quotation_type=QuotationType.DIRECT,
            pair_scaling=1,
            fixings_weights=[1.0, 3.0],
        )
        fixings = [1.30, 1.40]
        # norm fixings = [1.30, 1.40], weighted avg = 0.25*1.30 + 0.75*1.40 = 1.375
        result = expected_strike_physical(fixings, spec)
        assert result == pytest.approx(1.375)
