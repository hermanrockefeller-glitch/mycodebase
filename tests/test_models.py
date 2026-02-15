"""Tests for data models."""

from datetime import date

from options_pricer.models import OptionLeg, OptionStructure, OptionType, Side


class TestOptionLeg:
    def test_create_call(self):
        leg = OptionLeg(
            underlying="AAPL",
            expiry=date(2025, 1, 16),
            strike=150.0,
            option_type=OptionType.CALL,
            side=Side.BUY,
            quantity=100,
        )
        assert leg.underlying == "AAPL"
        assert leg.strike == 150.0
        assert leg.option_type == OptionType.CALL
        assert leg.side == Side.BUY
        assert leg.quantity == 100

    def test_direction_buy(self):
        leg = OptionLeg("AAPL", date(2025, 1, 16), 150.0, OptionType.CALL, Side.BUY)
        assert leg.direction == 1

    def test_direction_sell(self):
        leg = OptionLeg("AAPL", date(2025, 1, 16), 150.0, OptionType.CALL, Side.SELL)
        assert leg.direction == -1

    def test_call_payoff_itm(self):
        leg = OptionLeg("AAPL", date(2025, 1, 16), 150.0, OptionType.CALL, Side.BUY, 1)
        assert leg.payoff(160.0) == 10.0

    def test_call_payoff_otm(self):
        leg = OptionLeg("AAPL", date(2025, 1, 16), 150.0, OptionType.CALL, Side.BUY, 1)
        assert leg.payoff(140.0) == 0.0

    def test_put_payoff_itm(self):
        leg = OptionLeg("AAPL", date(2025, 1, 16), 150.0, OptionType.PUT, Side.BUY, 1)
        assert leg.payoff(140.0) == 10.0

    def test_put_payoff_otm(self):
        leg = OptionLeg("AAPL", date(2025, 1, 16), 150.0, OptionType.PUT, Side.BUY, 1)
        assert leg.payoff(160.0) == 0.0

    def test_sell_call_payoff(self):
        leg = OptionLeg("AAPL", date(2025, 1, 16), 150.0, OptionType.CALL, Side.SELL, 1)
        assert leg.payoff(160.0) == -10.0

    def test_quantity_scaling(self):
        leg = OptionLeg("AAPL", date(2025, 1, 16), 150.0, OptionType.CALL, Side.BUY, 10)
        assert leg.payoff(160.0) == 100.0


class TestOptionStructure:
    def _make_call_spread(self):
        return OptionStructure(
            name="call spread",
            legs=[
                OptionLeg("AAPL", date(2025, 1, 16), 150.0, OptionType.CALL, Side.BUY, 1),
                OptionLeg("AAPL", date(2025, 1, 16), 160.0, OptionType.CALL, Side.SELL, 1),
            ],
            description="BUY AAPL 150/160 call spread",
        )

    def test_structure_creation(self):
        s = self._make_call_spread()
        assert s.name == "call spread"
        assert len(s.legs) == 2

    def test_underlyings(self):
        s = self._make_call_spread()
        assert s.underlyings == {"AAPL"}

    def test_net_quantity(self):
        s = self._make_call_spread()
        assert s.net_quantity == 0  # 1 buy - 1 sell

    def test_call_spread_payoff_below(self):
        s = self._make_call_spread()
        assert s.total_payoff(140.0) == 0.0

    def test_call_spread_payoff_between(self):
        s = self._make_call_spread()
        assert s.total_payoff(155.0) == 5.0

    def test_call_spread_payoff_above(self):
        s = self._make_call_spread()
        assert s.total_payoff(170.0) == 10.0

    def test_straddle_payoff(self):
        s = OptionStructure(
            name="straddle",
            legs=[
                OptionLeg("AAPL", date(2025, 1, 16), 150.0, OptionType.CALL, Side.BUY, 1),
                OptionLeg("AAPL", date(2025, 1, 16), 150.0, OptionType.PUT, Side.BUY, 1),
            ],
        )
        assert s.total_payoff(150.0) == 0.0
        assert s.total_payoff(160.0) == 10.0
        assert s.total_payoff(140.0) == 10.0

    def test_payoff_range(self):
        s = self._make_call_spread()
        points = s.payoff_range(140.0, 170.0, steps=3)
        assert len(points) == 4
        assert points[0] == (140.0, 0.0)
        assert points[-1] == (170.0, 10.0)
