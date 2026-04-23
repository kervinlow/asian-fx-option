import pytest

from asian_fx_option.core import (
    AsianFXOptionSpec,
    AveragingMethod,
    CurrencyType,
    OptionType,
    QuotationType,
    SettlementType,
    compute_strike,
    normalize_rate,
    weighted_average,
)
from asian_fx_option.exceptions import (
    InvalidWeightsError,
    MissingFixedStrikeError,
    ZeroDivisionInAverageError,
)


class TestNormalizeRate:
    def test_direct_scale_1(self) -> None:
        assert normalize_rate(1.35, QuotationType.DIRECT, 1) == pytest.approx(1.35)

    def test_direct_scale_100(self) -> None:
        assert normalize_rate(0.85, QuotationType.DIRECT, 100) == pytest.approx(0.0085)

    def test_direct_scale_1000(self) -> None:
        assert normalize_rate(8.5, QuotationType.DIRECT, 1000) == pytest.approx(0.0085)

    def test_indirect_scale_1(self) -> None:
        # indirect: raw = 1.2 USD/SGD -> normalised = 1/1.2 SGD/USD
        assert normalize_rate(1.2, QuotationType.INDIRECT, 1) == pytest.approx(
            1.0 / 1.2, rel=1e-9
        )

    def test_indirect_scale_100(self) -> None:
        # indirect, scale=100: raw = 117.5 -> normalised = 100/117.5
        assert normalize_rate(117.5, QuotationType.INDIRECT, 100) == pytest.approx(
            100 / 117.5, rel=1e-9
        )


class TestWeightedAverage:
    def test_arithmetic_equal_weights(self) -> None:
        result = weighted_average([1.0, 2.0, 3.0], None, AveragingMethod.ARITHMETIC)
        assert result == pytest.approx(2.0)

    def test_arithmetic_custom_weights(self) -> None:
        values = [1.0, 2.0, 3.0]
        weights = [1.0, 2.0, 1.0]
        result = weighted_average(values, weights, AveragingMethod.ARITHMETIC)
        assert result == pytest.approx((1 * 0.25 + 2 * 0.5 + 3 * 0.25))

    def test_arithmetic_single_fixing(self) -> None:
        result = weighted_average([1.35], None, AveragingMethod.ARITHMETIC)
        assert result == pytest.approx(1.35)

    def test_harmonic_equal_weights(self) -> None:
        values = [0.0085, 0.0086, 0.0084]
        result = weighted_average(values, None, AveragingMethod.HARMONIC)
        expected = 3.0 / (1 / 0.0085 + 1 / 0.0086 + 1 / 0.0084)
        assert result == pytest.approx(expected, rel=1e-9)

    def test_harmonic_custom_weights(self) -> None:
        values = [0.0085, 0.0086]
        weights = [1.0, 3.0]
        result = weighted_average(values, weights, AveragingMethod.HARMONIC)
        expected = 1.0 / (0.25 / 0.0085 + 0.75 / 0.0086)
        assert result == pytest.approx(expected, rel=1e-9)

    def test_weights_unnormalised_and_normalised_are_equivalent(self) -> None:
        values = [1.0, 2.0]
        result_raw = weighted_average(values, [2.0, 2.0], AveragingMethod.ARITHMETIC)
        result_norm = weighted_average(values, [0.5, 0.5], AveragingMethod.ARITHMETIC)
        assert result_raw == pytest.approx(result_norm)

    def test_invalid_weight_count(self) -> None:
        with pytest.raises(InvalidWeightsError, match="Number of weights"):
            weighted_average([1.0, 2.0], [1.0], AveragingMethod.ARITHMETIC)

    def test_negative_weight(self) -> None:
        with pytest.raises(InvalidWeightsError, match="non-negative"):
            weighted_average([1.0, 2.0], [-1.0, 2.0], AveragingMethod.ARITHMETIC)

    def test_zero_sum_weights(self) -> None:
        with pytest.raises(InvalidWeightsError, match="zero"):
            weighted_average([1.0, 2.0], [0.0, 0.0], AveragingMethod.ARITHMETIC)

    def test_harmonic_zero_value_raises(self) -> None:
        with pytest.raises(ZeroDivisionInAverageError):
            weighted_average([1.0, 0.0], None, AveragingMethod.HARMONIC)


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


class TestComputeStrike:
    def test_floating_no_spread(self) -> None:
        spec = _make_spec()
        k = compute_strike(1.35, spec, 0.0)
        assert k == pytest.approx(1.35)

    def test_floating_with_spread(self) -> None:
        spec = _make_spec(strike_spread=0.02, quotation_type=QuotationType.DIRECT, pair_scaling=100)
        norm_spread = normalize_rate(0.02, QuotationType.DIRECT, 100)
        k = compute_strike(0.0085, spec, norm_spread)
        assert k == pytest.approx(0.0087)

    def test_floating_with_multiplier(self) -> None:
        spec = _make_spec(strike_multiplier=1.05)
        k = compute_strike(1.35, spec, 0.0)
        assert k == pytest.approx(1.35 * 1.05)

    def test_floating_with_rounding(self) -> None:
        spec = _make_spec(rounding_decimals=4)
        k = compute_strike(0.0085, spec, 0.0002)
        assert k == pytest.approx(0.0087)

    def test_fixed_strike(self) -> None:
        spec = _make_spec(
            is_floating_strike=False,
            strike_fixed=1.34,
            quotation_type=QuotationType.DIRECT,
            pair_scaling=1,
        )
        k = compute_strike(1.35, spec, 0.0)
        assert k == pytest.approx(1.34)

    def test_fixed_strike_missing_raises(self) -> None:
        spec = _make_spec(is_floating_strike=False, strike_fixed=None)
        with pytest.raises(MissingFixedStrikeError):
            compute_strike(1.35, spec, 0.0)

    def test_rounding_applied(self) -> None:
        spec = _make_spec(rounding_decimals=2)
        k = compute_strike(0.00856789, spec, 0.0)
        assert k == pytest.approx(0.01)
