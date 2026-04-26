# asian-fx-option

A Python library for pricing Asian FX options with flexible features, supporting arithmetic and harmonic averaging, direct and indirect quotation conventions, custom fixing weights, floating or fixed strikes, and both cash and physical settlement.

## Installation

### With uv

```bash
uv add asian-fx-option
```

### With pip

```bash
pip install asian-fx-option
```

## Quick Start

```python
from asian_fx_option import (
    asian_fx_option_payout,
    AsianFXOptionSpec,
    AveragingMethod,
    CurrencyType,
    OptionType,
    QuotationType,
    SettlementType,
)
```

## Public API

### Enums

| Enum | Values | Description |
|------|--------|-------------|
| `OptionType` | `CALL`, `PUT` | Right to buy or sell the base currency |
| `QuotationType` | `DIRECT`, `INDIRECT` | How the FX rate is quoted (e.g. SGD per JPY vs JPY per SGD) |
| `AveragingMethod` | `ARITHMETIC`, `HARMONIC` | Weighted average method applied to fixings |
| `SettlementType` | `CASH`, `PHYSICAL` | Whether the option settles in cash or by physical delivery |
| `CurrencyType` | `BASE`, `QUOTE` | Which leg of the currency pair a notional or settlement amount refers to |

### `AsianFXOptionSpec`

Holds the full specification of an Asian FX option. All rate parameters use the original quotation convention (including scaling); the library normalises internally.

| Field | Type | Description |
|-------|------|-------------|
| `option_type` | `OptionType` | Call or put |
| `is_floating_strike` | `bool` | `True` for floating strike, `False` for fixed |
| `strike_spread` | `float` | Additive spread in original quotation units (use `0.0` for no spread) |
| `quotation_type` | `QuotationType` | Direct or indirect quotation |
| `pair_scaling` | `int` | Scaling factor (e.g. `100` for SGD per 100 JPY) |
| `notional_currency` | `CurrencyType` | Currency in which `notional_amount` is expressed |
| `notional_amount` | `float` | Notional size |
| `averaging_method` | `AveragingMethod` | Arithmetic or harmonic |
| `settlement_currency` | `CurrencyType` | Currency in which the payout is delivered |
| `settlement_type` | `SettlementType` | Cash or physical |
| `strike_multiplier` | `float` | Multiplier applied to `S_avg` for floating strike (default `1.0`) |
| `strike_fixed` | `float \| None` | Fixed strike in original quotation units (required when `is_floating_strike=False`) |
| `final_rate_raw` | `float \| None` | Final/spot rate in original quotation units used as the underlying for floating-strike cash settlement (required when `is_floating_strike=True` and `settlement_type=CASH`) |
| `fixings_weights` | `list[float] \| None` | Per-fixing weights; `None` means equal weights |
| `rounding_decimals` | `int \| None` | Decimal places to round the normalised strike to; `None` means no rounding |
| `settlement_fixing` | `float \| None` | Raw fixing used to convert payoff to base currency (required when `settlement_currency=BASE`) |

### `asian_fx_option_payout(fixings, spec) -> float`

Top-level function. Returns:

- **Cash settlement**: expected cash flow in the settlement currency.
- **Physical settlement**: expected strike in the original quotation convention (including scaling).

### Lower-level functions

| Function | Description |
|----------|-------------|
| `expected_cash_flow(raw_fixings, spec)` | Cash settlement payout |
| `expected_strike_physical(raw_fixings, spec)` | Physical settlement expected strike |
| `normalize_rate(raw_rate, quotation, scale)` | Convert a raw rate to quote-per-base |
| `normalize_spread(raw_spread, quotation, scale)` | Normalise an additive spread (handles zero correctly) |
| `weighted_average(values, weights, method)` | Weighted arithmetic or harmonic average |
| `compute_strike(avg_reference, spec, normalized_spread)` | Compute normalised strike with optional rounding |

## Usage Examples

### Example 1: Cash settlement — notional in base, settle in quote

A call on USD/SGD. Notional is 1,000,000 USD (base). The average fixing comes out at 1.35 SGD/USD against a fixed strike of 1.34.

```python
spec = AsianFXOptionSpec(
    option_type=OptionType.CALL,
    is_floating_strike=False,
    strike_fixed=1.34,
    strike_spread=0.0,
    quotation_type=QuotationType.DIRECT,
    pair_scaling=1,
    notional_currency=CurrencyType.BASE,
    notional_amount=1_000_000.0,
    averaging_method=AveragingMethod.ARITHMETIC,
    settlement_currency=CurrencyType.QUOTE,
    settlement_type=SettlementType.CASH,
)

payout = asian_fx_option_payout([1.35], spec)
# payoff_per_base = 1.35 - 1.34 = 0.01 SGD/USD
# total = 1,000,000 * 0.01 = 10,000 SGD
print(payout)  # ≈ 10000.0
```

### Example 2: Cash settlement — notional in quote, settle in quote

Same economic position as Example 1, but the notional is expressed in SGD (quote).

```python
spec = AsianFXOptionSpec(
    option_type=OptionType.CALL,
    is_floating_strike=False,
    strike_fixed=1.34,
    strike_spread=0.0,
    quotation_type=QuotationType.DIRECT,
    pair_scaling=1,
    notional_currency=CurrencyType.QUOTE,
    notional_amount=1_350_000.0,  # 1,350,000 SGD
    averaging_method=AveragingMethod.ARITHMETIC,
    settlement_currency=CurrencyType.QUOTE,
    settlement_type=SettlementType.CASH,
)

payout = asian_fx_option_payout([1.35], spec)
# base_notional = 1,350,000 / 1.35 = 1,000,000 USD
# total = 1,000,000 * 0.01 = 10,000 SGD
print(payout)  # ≈ 10000.0
```

### Example 3: Cash settlement — floating-strike put (average strike option)

A put on USD/SGD with a floating strike. The strike is set as the average of fixings (S_avg) plus a spread. The underlying for the payoff is a separate final/spot rate at expiry (`final_rate_raw`).

```python
spec = AsianFXOptionSpec(
    option_type=OptionType.PUT,
    is_floating_strike=True,
    strike_spread=0.02,          # +0.02 SGD/USD added to S_avg
    final_rate_raw=1.36,         # spot rate at expiry, the payoff underlying
    quotation_type=QuotationType.DIRECT,
    pair_scaling=1,
    notional_currency=CurrencyType.BASE,
    notional_amount=1_000_000.0,
    averaging_method=AveragingMethod.ARITHMETIC,
    settlement_currency=CurrencyType.QUOTE,
    settlement_type=SettlementType.CASH,
)

payout = asian_fx_option_payout([1.35, 1.36, 1.34], spec)
# S_avg = 1.35, K_norm = 1.35 + 0.02 = 1.37
# underlying (final_rate) = 1.36
# payoff = max(0, 1.37 - 1.36) = 0.01 SGD/USD
# total = 1,000,000 * 0.01 = 10,000 SGD
print(payout)  # ≈ 10000.0
```

### Example 4: Cash settlement — notional in quote, settle in base

Same position as Example 2, but the payout is delivered in USD (base). A separate settlement fixing is required for the conversion.

```python
spec = AsianFXOptionSpec(
    option_type=OptionType.CALL,
    is_floating_strike=False,
    strike_fixed=1.34,
    strike_spread=0.0,
    quotation_type=QuotationType.DIRECT,
    pair_scaling=1,
    notional_currency=CurrencyType.QUOTE,
    notional_amount=1_350_000.0,
    averaging_method=AveragingMethod.ARITHMETIC,
    settlement_currency=CurrencyType.BASE,
    settlement_type=SettlementType.CASH,
    settlement_fixing=1.35,  # SGD/USD rate used to convert payout to USD
)

payout = asian_fx_option_payout([1.35], spec)
# total_payoff_quote = 10,000 SGD
# payout_base = 10,000 / 1.35 ≈ 7,407.41 USD
print(payout)  # 7407.407...
```

If the settlement fixing differs from the average (e.g. 1.36), the conversion uses 1.36 instead.

### Example 5: Physical settlement — direct quotation with scaling and spread

A floating-strike option on SGD/JPY quoted as SGD per 100 JPY (direct, scale 100). The expected strike is returned in the original convention.

```python
spec = AsianFXOptionSpec(
    option_type=OptionType.CALL,
    is_floating_strike=True,
    strike_spread=0.02,          # 0.02 SGD per 100 JPY
    quotation_type=QuotationType.DIRECT,
    pair_scaling=100,
    notional_currency=CurrencyType.BASE,
    notional_amount=1_000_000.0,
    averaging_method=AveragingMethod.ARITHMETIC,
    settlement_currency=CurrencyType.QUOTE,
    settlement_type=SettlementType.PHYSICAL,
)

strike = asian_fx_option_payout([0.85, 0.86, 0.84], spec)
# S_avg_norm = mean([0.0085, 0.0086, 0.0084]) = 0.0085 SGD/JPY
# norm_spread = 0.02 / 100 = 0.0002
# K_norm = 0.0085 + 0.0002 = 0.0087
# K_original = 0.0087 * 100 = 0.87 SGD per 100 JPY
print(strike)  # ≈ 0.87
```

### Example 6: Custom weights and harmonic averaging

Fixings can carry different weights, and the harmonic mean can be used instead of the arithmetic mean.

```python
spec = AsianFXOptionSpec(
    option_type=OptionType.CALL,
    is_floating_strike=True,
    strike_spread=0.0,
    quotation_type=QuotationType.DIRECT,
    pair_scaling=1,
    notional_currency=CurrencyType.BASE,
    notional_amount=1_000_000.0,
    averaging_method=AveragingMethod.HARMONIC,
    fixings_weights=[1.0, 3.0],  # second fixing weighted 3x; normalised to [0.25, 0.75]
    settlement_currency=CurrencyType.QUOTE,
    settlement_type=SettlementType.PHYSICAL,
)

strike = asian_fx_option_payout([1.30, 1.40], spec)
# H = 1 / (0.25/1.30 + 0.75/1.40) ≈ 1.3736
print(strike)  # ≈ 1.3736
```

## Error Handling

All exceptions inherit from `AsianFXOptionError`.

| Exception | Raised when |
|-----------|-------------|
| `InvalidWeightsError` | Weights are negative, do not match the number of fixings, or sum to zero |
| `ZeroDivisionInAverageError` | A fixing is zero and harmonic averaging is selected |
| `ZeroAverageRateError` | `S_avg` is zero and `notional_currency=QUOTE` (impossible for valid FX rates) |
| `MissingFixedStrikeError` | `is_floating_strike=False` but `strike_fixed` is not provided |
| `MissingFinalRateError` | `is_floating_strike=True` and `settlement_type=CASH` but `final_rate_raw` is not provided |
| `MissingSettlementFixingError` | `settlement_currency=BASE` but `settlement_fixing` is not provided |

```python
from asian_fx_option import (
    asian_fx_option_payout,
    AsianFXOptionSpec,
    AveragingMethod,
    CurrencyType,
    MissingSettlementFixingError,
    OptionType,
    QuotationType,
    SettlementType,
)

spec = AsianFXOptionSpec(
    option_type=OptionType.CALL,
    is_floating_strike=False,
    strike_fixed=1.34,
    strike_spread=0.0,
    quotation_type=QuotationType.DIRECT,
    pair_scaling=1,
    notional_currency=CurrencyType.BASE,
    notional_amount=1_000_000.0,
    averaging_method=AveragingMethod.ARITHMETIC,
    settlement_currency=CurrencyType.BASE,  # base settlement requires settlement_fixing
    settlement_type=SettlementType.CASH,
    # settlement_fixing omitted → raises MissingSettlementFixingError
)

try:
    payout = asian_fx_option_payout([1.35], spec)
except MissingSettlementFixingError as e:
    print(f"Configuration error: {e}")
# Configuration error: settlement_fixing must be provided when settlement_currency == BASE
```
