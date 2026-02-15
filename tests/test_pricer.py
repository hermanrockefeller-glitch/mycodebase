"""Tests for the Black-Scholes pricing engine."""

import math
from datetime import date

import pytest

from options_pricer.models import OptionLeg, OptionStructure, OptionType, Side
from options_pricer.pricer import (
    OptionPrice,
    black_scholes_price,
    greeks,
    price_structure,
)


class TestBlackScholesPrice:
    """Test Black-Scholes pricing against known values."""

    def test_atm_call(self):
        # ATM call: S=100, K=100, T=1, r=0.05, sigma=0.20
        price = black_scholes_price(100, 100, 1.0, 0.05, 0.20, OptionType.CALL)
        # Known value ~10.45
        assert 10.0 < price < 11.0

    def test_atm_put(self):
        price = black_scholes_price(100, 100, 1.0, 0.05, 0.20, OptionType.PUT)
        # Known value ~5.57
        assert 5.0 < price < 6.5

    def test_put_call_parity(self):
        """C - P = S*exp(-qT) - K*exp(-rT) for European options."""
        S, K, T, r, sigma = 100.0, 100.0, 1.0, 0.05, 0.25
        call = black_scholes_price(S, K, T, r, sigma, OptionType.CALL)
        put = black_scholes_price(S, K, T, r, sigma, OptionType.PUT)
        parity = S - K * math.exp(-r * T)
        assert abs((call - put) - parity) < 1e-10

    def test_put_call_parity_with_dividend(self):
        S, K, T, r, sigma, q = 100.0, 105.0, 0.5, 0.05, 0.30, 0.02
        call = black_scholes_price(S, K, T, r, sigma, OptionType.CALL, q)
        put = black_scholes_price(S, K, T, r, sigma, OptionType.PUT, q)
        parity = S * math.exp(-q * T) - K * math.exp(-r * T)
        assert abs((call - put) - parity) < 1e-10

    def test_deep_itm_call(self):
        # Deep ITM call should be close to intrinsic
        price = black_scholes_price(200, 100, 0.01, 0.05, 0.20, OptionType.CALL)
        assert price > 99.0

    def test_deep_otm_call(self):
        # Deep OTM call should be near zero
        price = black_scholes_price(50, 100, 0.1, 0.05, 0.20, OptionType.CALL)
        assert price < 0.01

    def test_expired_call_itm(self):
        price = black_scholes_price(110, 100, 0.0, 0.05, 0.20, OptionType.CALL)
        assert price == 10.0

    def test_expired_put_itm(self):
        price = black_scholes_price(90, 100, 0.0, 0.05, 0.20, OptionType.PUT)
        assert price == 10.0

    def test_expired_call_otm(self):
        price = black_scholes_price(90, 100, 0.0, 0.05, 0.20, OptionType.CALL)
        assert price == 0.0

    def test_higher_vol_higher_price(self):
        low_vol = black_scholes_price(100, 100, 1.0, 0.05, 0.15, OptionType.CALL)
        high_vol = black_scholes_price(100, 100, 1.0, 0.05, 0.35, OptionType.CALL)
        assert high_vol > low_vol

    def test_longer_expiry_higher_price(self):
        short = black_scholes_price(100, 100, 0.25, 0.05, 0.20, OptionType.CALL)
        long = black_scholes_price(100, 100, 1.0, 0.05, 0.20, OptionType.CALL)
        assert long > short


class TestGreeks:
    def test_call_delta_positive(self):
        result = greeks(100, 100, 1.0, 0.05, 0.20, OptionType.CALL)
        assert 0.0 < result.delta < 1.0

    def test_put_delta_negative(self):
        result = greeks(100, 100, 1.0, 0.05, 0.20, OptionType.PUT)
        assert -1.0 < result.delta < 0.0

    def test_atm_call_delta_near_half(self):
        result = greeks(100, 100, 1.0, 0.05, 0.20, OptionType.CALL)
        assert 0.5 < result.delta < 0.7  # Slightly above 0.5 due to drift

    def test_gamma_positive(self):
        call = greeks(100, 100, 1.0, 0.05, 0.20, OptionType.CALL)
        put = greeks(100, 100, 1.0, 0.05, 0.20, OptionType.PUT)
        assert call.gamma > 0
        assert put.gamma > 0
        assert abs(call.gamma - put.gamma) < 1e-10

    def test_theta_negative_for_long(self):
        result = greeks(100, 100, 1.0, 0.05, 0.20, OptionType.CALL)
        assert result.theta < 0

    def test_vega_positive(self):
        result = greeks(100, 100, 1.0, 0.05, 0.20, OptionType.CALL)
        assert result.vega > 0

    def test_call_rho_positive(self):
        result = greeks(100, 100, 1.0, 0.05, 0.20, OptionType.CALL)
        assert result.rho > 0

    def test_put_rho_negative(self):
        result = greeks(100, 100, 1.0, 0.05, 0.20, OptionType.PUT)
        assert result.rho < 0

    def test_delta_call_put_relation(self):
        """Delta(call) - Delta(put) ≈ exp(-qT) for same strike."""
        call = greeks(100, 100, 1.0, 0.05, 0.20, OptionType.CALL)
        put = greeks(100, 100, 1.0, 0.05, 0.20, OptionType.PUT)
        assert abs((call.delta - put.delta) - 1.0) < 0.01

    def test_expired_option_greeks(self):
        result = greeks(110, 100, 0.0, 0.05, 0.20, OptionType.CALL)
        assert result.price == 10.0
        assert result.delta == 1.0
        assert result.gamma == 0.0
        assert result.theta == 0.0
        assert result.vega == 0.0


class TestPriceStructure:
    def test_call_spread(self):
        structure = OptionStructure(
            name="spread",
            legs=[
                OptionLeg("AAPL", date(2025, 6, 16), 150.0, OptionType.CALL, Side.BUY, 1),
                OptionLeg("AAPL", date(2025, 6, 16), 160.0, OptionType.CALL, Side.SELL, 1),
            ],
        )
        result = price_structure(structure, spot=155.0, r=0.05, sigma=0.25, T=0.5)
        # Long call spread: net debit, positive delta, limited risk
        assert result.total_price > 0  # net debit (we own more value than we sold)
        assert result.total_delta > 0  # bullish
        assert len(result.leg_prices) == 2

    def test_straddle_pricing(self):
        structure = OptionStructure(
            name="straddle",
            legs=[
                OptionLeg("SPY", date(2025, 6, 16), 500.0, OptionType.CALL, Side.BUY, 1),
                OptionLeg("SPY", date(2025, 6, 16), 500.0, OptionType.PUT, Side.BUY, 1),
            ],
        )
        result = price_structure(structure, spot=500.0, r=0.05, sigma=0.18, T=0.5)
        # ATM straddle: near-zero delta, positive gamma, positive vega
        assert abs(result.total_delta) < 0.25  # near-zero, slight drift from r>0
        assert result.total_gamma > 0
        assert result.total_vega > 0
        assert result.total_price > 0

    def test_vol_dict(self):
        """Test passing a per-strike vol dictionary."""
        structure = OptionStructure(
            name="spread",
            legs=[
                OptionLeg("AAPL", date(2025, 6, 16), 150.0, OptionType.CALL, Side.BUY, 1),
                OptionLeg("AAPL", date(2025, 6, 16), 160.0, OptionType.CALL, Side.SELL, 1),
            ],
        )
        vol_map = {150.0: 0.25, 160.0: 0.22}
        result = price_structure(structure, spot=155.0, r=0.05, sigma=vol_map, T=0.5)
        assert result.total_price > 0
        assert len(result.leg_prices) == 2
