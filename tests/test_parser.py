"""Tests for the order parser."""

from datetime import date

import pytest

from options_pricer.models import OptionType, Side
from options_pricer.parser import parse_order


class TestParseOrder:
    def test_single_call(self):
        s = parse_order("BUY 100 AAPL Jan25 150 call")
        assert s.name == "single"
        assert len(s.legs) == 1
        leg = s.legs[0]
        assert leg.underlying == "AAPL"
        assert leg.expiry == date(2025, 1, 16)
        assert leg.strike == 150.0
        assert leg.option_type == OptionType.CALL
        assert leg.side == Side.BUY
        assert leg.quantity == 100

    def test_single_put(self):
        s = parse_order("SELL 50 SPY Mar25 450 put")
        assert s.name == "single"
        assert len(s.legs) == 1
        assert s.legs[0].option_type == OptionType.PUT
        assert s.legs[0].side == Side.SELL

    def test_call_spread(self):
        s = parse_order("BUY 100 AAPL Jan25 150/160 call spread")
        assert s.name == "spread"
        assert len(s.legs) == 2
        assert s.legs[0].strike == 150.0
        assert s.legs[0].side == Side.BUY
        assert s.legs[0].option_type == OptionType.CALL
        assert s.legs[1].strike == 160.0
        assert s.legs[1].side == Side.SELL
        assert s.legs[1].option_type == OptionType.CALL

    def test_put_spread(self):
        s = parse_order("BUY 20 MSFT Apr25 300/320 put spread")
        assert s.name == "spread"
        assert s.legs[0].option_type == OptionType.PUT
        assert s.legs[1].option_type == OptionType.PUT

    def test_straddle(self):
        s = parse_order("BUY 10 TSLA Feb25 200 straddle")
        assert s.name == "straddle"
        assert len(s.legs) == 2
        assert s.legs[0].option_type == OptionType.CALL
        assert s.legs[1].option_type == OptionType.PUT
        assert s.legs[0].strike == s.legs[1].strike == 200.0
        assert s.legs[0].side == s.legs[1].side == Side.BUY

    def test_strangle(self):
        s = parse_order("BUY 10 AAPL Jun25 150/160 strangle")
        assert s.name == "strangle"
        assert len(s.legs) == 2
        # Lower strike is put, higher is call
        assert s.legs[0].option_type == OptionType.PUT
        assert s.legs[0].strike == 150.0
        assert s.legs[1].option_type == OptionType.CALL
        assert s.legs[1].strike == 160.0

    def test_butterfly(self):
        s = parse_order("BUY 5 AMZN Jul25 180/190/200 call butterfly")
        assert s.name == "butterfly"
        assert len(s.legs) == 3
        assert s.legs[0].strike == 180.0
        assert s.legs[0].side == Side.BUY
        assert s.legs[0].quantity == 5
        assert s.legs[1].strike == 190.0
        assert s.legs[1].side == Side.SELL
        assert s.legs[1].quantity == 10  # 2x middle
        assert s.legs[2].strike == 200.0
        assert s.legs[2].side == Side.BUY
        assert s.legs[2].quantity == 5

    def test_risk_reversal(self):
        s = parse_order("BUY 10 GOOGL Sep25 150P/160C risk reversal")
        assert s.name == "risk reversal"
        assert len(s.legs) == 2
        # Sell the put, buy the call
        assert s.legs[0].strike == 150.0
        assert s.legs[0].option_type == OptionType.PUT
        assert s.legs[0].side == Side.SELL
        assert s.legs[1].strike == 160.0
        assert s.legs[1].option_type == OptionType.CALL
        assert s.legs[1].side == Side.BUY

    def test_collar(self):
        s = parse_order("BUY 10 META Dec25 400P/450C collar")
        assert s.name == "collar"
        assert len(s.legs) == 2
        # Buy the put, sell the call
        assert s.legs[0].strike == 400.0
        assert s.legs[0].option_type == OptionType.PUT
        assert s.legs[0].side == Side.BUY
        assert s.legs[1].strike == 450.0
        assert s.legs[1].option_type == OptionType.CALL
        assert s.legs[1].side == Side.SELL

    def test_underlying_is_uppercased(self):
        s = parse_order("BUY 1 aapl Jan25 150 call")
        assert s.legs[0].underlying == "AAPL"

    def test_expiry_parsing(self):
        s = parse_order("BUY 1 SPY Dec25 500 call")
        assert s.legs[0].expiry == date(2025, 12, 16)

    def test_invalid_too_short(self):
        with pytest.raises(ValueError, match="too short"):
            parse_order("BUY AAPL")

    def test_invalid_side(self):
        with pytest.raises(ValueError, match="BUY or SELL"):
            parse_order("HOLD 100 AAPL Jan25 150 call")

    def test_invalid_quantity(self):
        with pytest.raises(ValueError, match="quantity"):
            parse_order("BUY abc AAPL Jan25 150 call")

    def test_invalid_expiry(self):
        with pytest.raises(ValueError, match="expiry"):
            parse_order("BUY 100 AAPL 2025-01 150 call")

    def test_sell_spread(self):
        s = parse_order("SELL 50 AAPL Jan25 150/160 call spread")
        assert s.legs[0].side == Side.SELL
        assert s.legs[1].side == Side.BUY
