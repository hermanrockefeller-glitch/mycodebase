"""Tests for the IDB broker shorthand parser."""

from datetime import date

import pytest

from options_pricer.models import OptionType, Side, QuoteSide
from options_pricer.parser import (
    parse_order,
    _extract_stock_ref,
    _extract_delta,
    _extract_delta_direction,
    _extract_quantity,
    _extract_price_and_side,
    _extract_ratio,
    _extract_modifier,
    _extract_structure_type,
)


class TestExtractStockRef:
    def test_vs_no_space(self):
        assert _extract_stock_ref("AAPL Jun26 300 calls vs250.32") == 250.32

    def test_vs_space(self):
        assert _extract_stock_ref("vs 262.54") == 262.54

    def test_vs_dot(self):
        assert _extract_stock_ref("vs. 250") == 250.0

    def test_tt_no_space(self):
        assert _extract_stock_ref("tt69.86") == 69.86

    def test_tt_space(self):
        assert _extract_stock_ref("tt 171.10") == 171.10

    def test_t_space(self):
        assert _extract_stock_ref("AAPL t 250.00") == 250.00

    def test_none(self):
        assert _extract_stock_ref("AAPL Jun26 300 calls") is None


class TestExtractDelta:
    def test_simple(self):
        assert _extract_delta("30d") == 30.0

    def test_single_digit(self):
        assert _extract_delta("3d") == 3.0

    def test_on_a(self):
        assert _extract_delta("on a 11d") == 11.0

    def test_in_context(self):
        assert _extract_delta("UBER Jun26 45P tt69.86 3d 0.41 bid") == 3.0


class TestExtractQuantity:
    def test_simple(self):
        assert _extract_quantity("1058x") == 1058

    def test_in_context(self):
        assert _extract_quantity("AAPL Jun26 300 calls 500x") == 500

    def test_with_ratio(self):
        # Should not match the "1" in "1X2", should match "500x"
        assert _extract_quantity("PS 1X2 500x") == 500

    def test_k_format_simple(self):
        assert _extract_quantity("1k") == 1000

    def test_k_format_larger(self):
        assert _extract_quantity("2k") == 2000

    def test_k_format_in_context(self):
        assert _extract_quantity("goog jun 100 90 ps vs 200.00 10d 1 bid 1k") == 1000


class TestExtractPriceAndSide:
    def test_bid_word(self):
        price, side = _extract_price_and_side("20.50 bid")
        assert price == 20.50
        assert side == QuoteSide.BID

    def test_bid_suffix(self):
        price, side = _extract_price_and_side("2.4b")
        assert price == 2.4
        assert side == QuoteSide.BID

    def test_at_symbol(self):
        price, side = _extract_price_and_side("@ 1.60")
        assert price == 1.60
        assert side == QuoteSide.OFFER

    def test_at_with_qty(self):
        price, side = _extract_price_and_side("500 @ 2.55")
        assert price == 2.55
        assert side == QuoteSide.OFFER

    def test_offer_word(self):
        price, side = _extract_price_and_side("5.00 offer")
        assert price == 5.00
        assert side == QuoteSide.OFFER


class TestExtractRatio:
    def test_1x2(self):
        assert _extract_ratio("PS 1X2 500x") == (1, 2)

    def test_1x3(self):
        assert _extract_ratio("1x3") == (1, 3)

    def test_no_ratio(self):
        assert _extract_ratio("500x @ 3.50") is None


class TestExtractModifier:
    def test_putover(self):
        assert _extract_modifier("putover") == "putover"

    def test_put_over(self):
        assert _extract_modifier("put over") == "putover"

    def test_callover(self):
        assert _extract_modifier("callover") == "callover"

    def test_nx_over(self):
        assert _extract_modifier("1X over") == "1x_over"


class TestExtractStructureType:
    def test_ps(self):
        assert _extract_structure_type("AAPL Jun26 240/220 PS") == "put_spread"

    def test_cs(self):
        assert _extract_structure_type("AAPL Jun26 240/280 CS") == "call_spread"

    def test_risky(self):
        assert _extract_structure_type("IWM feb 257 apr 280 Risky") == "risk_reversal"

    def test_straddle(self):
        assert _extract_structure_type("AAPL Jun26 250 straddle") == "straddle"

    def test_fly(self):
        assert _extract_structure_type("AAPL fly 240/250/260") == "butterfly"


class TestParseOrder:
    def test_single_call(self):
        order = parse_order("AAPL jun26 300 calls vs250.32 30d 20.50 bid 1058x")
        assert order.underlying == "AAPL"
        assert order.stock_ref == 250.32
        assert order.delta == 30.0
        assert order.price == 20.50
        assert order.quote_side == QuoteSide.BID
        assert order.quantity == 1058
        assert len(order.structure.legs) == 1
        leg = order.structure.legs[0]
        assert leg.strike == 300.0
        assert leg.option_type == OptionType.CALL
        assert leg.expiry == date(2026, 6, 16)

    def test_single_put_with_tt(self):
        order = parse_order("UBER Jun26 45P tt69.86 3d 0.41 bid 1058x")
        assert order.underlying == "UBER"
        assert order.stock_ref == 69.86
        assert order.delta == -3.0
        assert order.price == 0.41
        assert order.quote_side == QuoteSide.BID
        assert len(order.structure.legs) == 1
        leg = order.structure.legs[0]
        assert leg.strike == 45.0
        assert leg.option_type == OptionType.PUT

    def test_put_strike_before_expiry(self):
        order = parse_order("QCOM 85P Jan27 tt141.17 7d 2.4b 600x")
        assert order.underlying == "QCOM"
        assert order.stock_ref == 141.17
        assert order.delta == -7.0
        assert order.price == 2.4
        assert order.quote_side == QuoteSide.BID
        assert order.quantity == 600
        leg = order.structure.legs[0]
        assert leg.strike == 85.0
        assert leg.option_type == OptionType.PUT
        assert leg.expiry == date(2027, 1, 16)

    def test_at_price_convention(self):
        order = parse_order("VST Apr 130p 500 @ 2.55 tt 171.10 on a 11d")
        assert order.underlying == "VST"
        assert order.stock_ref == 171.10
        assert order.delta == -11.0
        assert order.price == 2.55
        assert order.quote_side == QuoteSide.OFFER
        leg = order.structure.legs[0]
        assert leg.strike == 130.0
        assert leg.option_type == OptionType.PUT

    def test_calendar_risk_reversal(self):
        order = parse_order(
            "IWM feb 257 apr 280 Risky vs 262.54 52d 2500x @ 1.60"
        )
        assert order.underlying == "IWM"
        assert order.stock_ref == 262.54
        assert order.delta == 52.0
        assert order.price == 1.60
        assert order.quantity == 2500
        assert len(order.structure.legs) == 2
        # Lower strike should be the put, higher the call
        put_leg = [l for l in order.structure.legs
                   if l.option_type == OptionType.PUT][0]
        call_leg = [l for l in order.structure.legs
                    if l.option_type == OptionType.CALL][0]
        assert put_leg.strike == 257.0
        assert call_leg.strike == 280.0

    def test_put_spread_ratio(self):
        order = parse_order(
            "AAPL Jun26 240/220 PS 1X2 vs250 15d 500x @ 3.50 1X over"
        )
        assert order.underlying == "AAPL"
        assert order.stock_ref == 250.0
        assert order.delta == -15.0
        assert order.price == 3.50
        assert len(order.structure.legs) == 2
        # Buy higher strike (240P), sell lower strike (220P) at 2x
        buy_leg = [l for l in order.structure.legs if l.side == Side.BUY][0]
        sell_leg = [l for l in order.structure.legs if l.side == Side.SELL][0]
        assert buy_leg.strike == 240.0
        assert buy_leg.option_type == OptionType.PUT
        assert buy_leg.quantity == 500  # 500 * r1(1)
        assert sell_leg.strike == 220.0
        assert sell_leg.option_type == OptionType.PUT
        assert sell_leg.quantity == 1000  # 500 * r2(2)

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            parse_order("")

    def test_ticker_uppercased(self):
        order = parse_order("aapl Jun26 300 calls vs250 30d 5.00 bid 100x")
        assert order.underlying == "AAPL"


class TestExtractRatioThreePart:
    def test_three_part_integer(self):
        assert _extract_ratio("fly 1x2x1") == (1.0, 2.0, 1.0)

    def test_three_part_decimal(self):
        assert _extract_ratio("fly 1x1.5x1") == (1.0, 1.5, 1.0)

    def test_two_part_still_works(self):
        assert _extract_ratio("PS 1X2 500x") == (1, 2)


class TestExtractDeltaDirection:
    def test_dp_suffix(self):
        assert _extract_delta("30dp") == 30.0

    def test_dc_suffix(self):
        assert _extract_delta("20dc") == 20.0

    def test_direction_dp(self):
        assert _extract_delta_direction("30dp") == "put"

    def test_direction_dc(self):
        assert _extract_delta_direction("20dc") == "call"


class TestExtractStructureTypeNew:
    def test_iron_butterfly_if(self):
        assert _extract_structure_type("SPX Jun26 4000/4050/4100 IF") == "iron_butterfly"

    def test_iron_butterfly_ibf(self):
        assert _extract_structure_type("SPX Jun26 4000/4050/4100 IBF") == "iron_butterfly"

    def test_put_fly_pf(self):
        assert _extract_structure_type("AAPL Jun26 220/230/240 PF") == "put_fly"

    def test_call_fly_cf(self):
        assert _extract_structure_type("AAPL Jun26 280/290/300 CF") == "call_fly"


class TestParseOrderNewStructures:
    def test_put_fly(self):
        order = parse_order("AAPL Jun26 220/230/240 PF vs250 30dp 500x")
        assert order.underlying == "AAPL"
        assert order.stock_ref == 250.0
        assert order.delta == -30.0
        assert order.quantity == 500
        assert len(order.structure.legs) == 3
        assert order.structure.name == "put fly"
        for leg in order.structure.legs:
            assert leg.option_type == OptionType.PUT
        sorted_legs = sorted(order.structure.legs, key=lambda l: l.strike)
        assert sorted_legs[0].strike == 220.0
        assert sorted_legs[0].side == Side.BUY
        assert sorted_legs[1].strike == 230.0
        assert sorted_legs[1].side == Side.SELL
        assert sorted_legs[2].strike == 240.0
        assert sorted_legs[2].side == Side.BUY

    def test_call_fly(self):
        order = parse_order("AAPL Jun26 280/290/300 CF vs250 20dc 500x")
        assert order.underlying == "AAPL"
        assert order.delta == 20.0
        assert len(order.structure.legs) == 3
        assert order.structure.name == "call fly"
        for leg in order.structure.legs:
            assert leg.option_type == OptionType.CALL
        sorted_legs = sorted(order.structure.legs, key=lambda l: l.strike)
        assert sorted_legs[0].strike == 280.0
        assert sorted_legs[0].side == Side.BUY
        assert sorted_legs[1].strike == 290.0
        assert sorted_legs[1].side == Side.SELL
        assert sorted_legs[2].strike == 300.0
        assert sorted_legs[2].side == Side.BUY

    def test_iron_butterfly(self):
        order = parse_order("SPX Jun26 4000/4050/4100 IF vs4050 5d 100x")
        assert order.underlying == "SPX"
        assert order.delta == 5.0
        assert order.quantity == 100
        assert len(order.structure.legs) == 4
        assert order.structure.name == "iron butterfly"
        sorted_legs = sorted(order.structure.legs, key=lambda l: (l.strike, l.option_type.value))
        # Low put (buy), mid put (sell), mid call (sell), high call (buy)
        assert sorted_legs[0].strike == 4000.0
        assert sorted_legs[0].option_type == OptionType.PUT
        assert sorted_legs[0].side == Side.BUY
        assert sorted_legs[1].strike == 4050.0
        assert sorted_legs[1].option_type == OptionType.CALL
        assert sorted_legs[1].side == Side.SELL
        assert sorted_legs[2].strike == 4050.0
        assert sorted_legs[2].option_type == OptionType.PUT
        assert sorted_legs[2].side == Side.SELL
        assert sorted_legs[3].strike == 4100.0
        assert sorted_legs[3].option_type == OptionType.CALL
        assert sorted_legs[3].side == Side.BUY

    def test_butterfly_custom_ratio(self):
        order = parse_order("AAPL Jun26 220/230/240 fly 1x1.5x1 vs250 10d 500x")
        assert order.underlying == "AAPL"
        assert order.delta == 10.0
        assert len(order.structure.legs) == 3
        sorted_legs = sorted(order.structure.legs, key=lambda l: l.strike)
        assert sorted_legs[0].quantity == 500   # 500 * 1
        assert sorted_legs[1].quantity == 750   # 500 * 1.5
        assert sorted_legs[2].quantity == 500   # 500 * 1

    def test_single_call_displays_as_call(self):
        order = parse_order("AAPL Jun26 300 calls vs250 30d")
        assert order.structure.name == "call"
        assert order.delta == 30.0

    def test_single_put_displays_as_put(self):
        order = parse_order("UBER Jun26 45P tt69.86 3dp")
        assert order.structure.name == "put"
        assert order.delta == -3.0


class TestDeltaSignInference:
    def test_risk_reversal_putover_delta_sign(self):
        order = parse_order("AAPL jun 240 260 1x2 RR vs248 90d 6 bid 400x put over")
        assert order.underlying == "AAPL"
        assert order.stock_ref == 248.0
        assert order.delta == -90.0  # put over → negative delta
        assert order.price == 6.0
        assert order.quote_side == QuoteSide.BID
        assert order.quantity == 400
        assert len(order.structure.legs) == 2
        assert order.structure.name == "risk reversal"


class TestExtractStructureTypeCondors:
    def test_iron_condor_ic(self):
        assert _extract_structure_type("SPX Jun26 3900/3950/4100/4150 IC") == "iron_condor"

    def test_put_condor_pc(self):
        assert _extract_structure_type("AAPL Jun26 200/210/220/230 PC") == "put_condor"

    def test_call_condor_cc(self):
        assert _extract_structure_type("AAPL Jun26 280/290/300/310 CC") == "call_condor"

    def test_call_spread_collar_csc(self):
        assert _extract_structure_type("AAPL Jun26 220/250/260 CSC") == "call_spread_collar"

    def test_put_spread_collar_psc(self):
        assert _extract_structure_type("AAPL Jun26 200/220/260 PSC") == "put_spread_collar"


class TestParseOrderCondorsCollars:
    def test_iron_condor(self):
        order = parse_order("SPX Jun26 3900/3950/4100/4150 IC vs4050 5d 100x")
        assert order.underlying == "SPX"
        assert order.delta == 5.0
        assert order.quantity == 100
        assert len(order.structure.legs) == 4
        assert order.structure.name == "iron condor"
        sorted_legs = sorted(order.structure.legs, key=lambda l: (l.strike, l.option_type.value))
        assert sorted_legs[0].strike == 3900.0
        assert sorted_legs[0].option_type == OptionType.PUT
        assert sorted_legs[0].side == Side.BUY
        assert sorted_legs[1].strike == 3950.0
        assert sorted_legs[1].option_type == OptionType.PUT
        assert sorted_legs[1].side == Side.SELL
        assert sorted_legs[2].strike == 4100.0
        assert sorted_legs[2].option_type == OptionType.CALL
        assert sorted_legs[2].side == Side.SELL
        assert sorted_legs[3].strike == 4150.0
        assert sorted_legs[3].option_type == OptionType.CALL
        assert sorted_legs[3].side == Side.BUY

    def test_put_condor(self):
        order = parse_order("AAPL Jun26 200/210/220/230 PC vs250 10dp 500x")
        assert order.underlying == "AAPL"
        assert order.delta == -10.0
        assert len(order.structure.legs) == 4
        assert order.structure.name == "put condor"
        for leg in order.structure.legs:
            assert leg.option_type == OptionType.PUT
        sorted_legs = sorted(order.structure.legs, key=lambda l: l.strike)
        assert sorted_legs[0].side == Side.BUY
        assert sorted_legs[1].side == Side.SELL
        assert sorted_legs[2].side == Side.SELL
        assert sorted_legs[3].side == Side.BUY

    def test_call_condor(self):
        order = parse_order("AAPL Jun26 280/290/300/310 CC vs250 15dc 500x")
        assert order.underlying == "AAPL"
        assert order.delta == 15.0
        assert len(order.structure.legs) == 4
        assert order.structure.name == "call condor"
        for leg in order.structure.legs:
            assert leg.option_type == OptionType.CALL
        sorted_legs = sorted(order.structure.legs, key=lambda l: l.strike)
        assert sorted_legs[0].side == Side.BUY
        assert sorted_legs[1].side == Side.SELL
        assert sorted_legs[2].side == Side.SELL
        assert sorted_legs[3].side == Side.BUY

    def test_call_spread_collar(self):
        order = parse_order("AAPL Jun26 220/250/260 CSC vs250 20d 500x")
        assert order.underlying == "AAPL"
        assert order.delta == 20.0
        assert len(order.structure.legs) == 3
        assert order.structure.name == "call spread collar"
        sorted_legs = sorted(order.structure.legs, key=lambda l: l.strike)
        # Buy put at lowest, sell call at mid, buy call at highest
        assert sorted_legs[0].strike == 220.0
        assert sorted_legs[0].option_type == OptionType.PUT
        assert sorted_legs[0].side == Side.BUY
        assert sorted_legs[1].strike == 250.0
        assert sorted_legs[1].option_type == OptionType.CALL
        assert sorted_legs[1].side == Side.SELL
        assert sorted_legs[2].strike == 260.0
        assert sorted_legs[2].option_type == OptionType.CALL
        assert sorted_legs[2].side == Side.BUY

    def test_put_spread_collar(self):
        order = parse_order("AAPL Jun26 200/220/260 PSC vs250 15d 500x")
        assert order.underlying == "AAPL"
        assert order.delta == 15.0
        assert len(order.structure.legs) == 3
        assert order.structure.name == "put spread collar"
        sorted_legs = sorted(order.structure.legs, key=lambda l: l.strike)
        # Sell put at lowest, buy put at mid, sell call at highest
        assert sorted_legs[0].strike == 200.0
        assert sorted_legs[0].option_type == OptionType.PUT
        assert sorted_legs[0].side == Side.SELL
        assert sorted_legs[1].strike == 220.0
        assert sorted_legs[1].option_type == OptionType.PUT
        assert sorted_legs[1].side == Side.BUY
        assert sorted_legs[2].strike == 260.0
        assert sorted_legs[2].option_type == OptionType.CALL
        assert sorted_legs[2].side == Side.SELL


class TestParseOrderStupid:
    def test_put_stupid(self):
        order = parse_order("AAPL Jun26 250 240 put stupid live 500x")
        assert order.underlying == "AAPL"
        assert order.quantity == 500
        assert len(order.structure.legs) == 2
        assert order.structure.name == "put stupid"
        sorted_legs = sorted(order.structure.legs, key=lambda l: l.strike)
        assert sorted_legs[0].strike == 240.0
        assert sorted_legs[0].option_type == OptionType.PUT
        assert sorted_legs[0].side == Side.BUY
        assert sorted_legs[1].strike == 250.0
        assert sorted_legs[1].option_type == OptionType.PUT
        assert sorted_legs[1].side == Side.BUY

    def test_call_stupid(self):
        order = parse_order("AAPL Jun26 260 270 call stupid live 300x")
        assert order.underlying == "AAPL"
        assert order.quantity == 300
        assert len(order.structure.legs) == 2
        assert order.structure.name == "call stupid"
        sorted_legs = sorted(order.structure.legs, key=lambda l: l.strike)
        assert sorted_legs[0].strike == 260.0
        assert sorted_legs[0].option_type == OptionType.CALL
        assert sorted_legs[0].side == Side.BUY
        assert sorted_legs[1].strike == 270.0
        assert sorted_legs[1].option_type == OptionType.CALL
        assert sorted_legs[1].side == Side.BUY

    def test_put_stupid_delta_sign(self):
        order = parse_order("AAPL Jun26 250 240 put stupid vs248 30d 500x")
        assert order.delta == -30.0  # put stupid → negative delta

    def test_call_stupid_delta_sign(self):
        order = parse_order("AAPL Jun26 260 270 call stupid vs265 25d 300x")
        assert order.delta == 25.0  # call stupid → positive delta


class TestLiveTieConflict:
    def test_live_with_tie_raises(self):
        """'live' + stock tie is contradictory — should raise."""
        with pytest.raises(ValueError, match="live.*tied"):
            parse_order("MU may 420 Call live vs420 40d 500x at 50.00")

    def test_live_without_tie_ok(self):
        """'live' without a tie is fine — delta and stock_ref zeroed."""
        order = parse_order("MU may 420 Call live 500x at 50.00")
        assert order.stock_ref == 0.0
        assert order.delta == 0.0
        assert order.quantity == 500
