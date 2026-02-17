"""Calculate structure-level bid/offer/mid from individual leg market data."""

from .models import (
    LegMarketData,
    OptionLeg,
    ParsedOrder,
    StructureMarketData,
)


def price_structure_from_market(
    order: ParsedOrder,
    leg_market: list[LegMarketData],
    stock_price: float,
) -> StructureMarketData:
    """Calculate per-unit structure bid/offer/mid from screen market data.

    Uses signed ratios (positive = BUY, negative = SELL) normalised to the
    smallest leg so the result is a per-structure price independent of order
    size.

    For each leg with signed ratio *s*:
      s > 0 (BUY):  bid += s * leg_bid,   offer += s * leg_offer
      s < 0 (SELL):  bid += s * leg_offer, offer += s * leg_bid

    A tie adjustment is added when the order has a stock ref and delta:
      tie_adj = (delta / 100) * (spot - ref)
    """
    legs = order.structure.legs

    if len(legs) != len(leg_market):
        raise ValueError(
            f"Leg count mismatch: {len(legs)} legs but {len(leg_market)} market entries"
        )

    base_qty = min(leg.quantity for leg in legs) if legs else 1
    if base_qty <= 0:
        base_qty = 1

    struct_bid = 0.0
    struct_offer = 0.0

    for leg, mkt in zip(legs, leg_market):
        ratio = leg.quantity // base_qty
        signed = leg.direction * ratio  # +ratio for BUY, -ratio for SELL

        if signed > 0:
            struct_bid += signed * mkt.bid
            struct_offer += signed * mkt.offer
        elif signed < 0:
            struct_bid += signed * mkt.offer
            struct_offer += signed * mkt.bid

    # Tie adjustment for structures with a stock reference
    tie_adj = 0.0
    if order.stock_ref > 0 and order.delta != 0:
        tie_adj = (order.delta / 100.0) * (stock_price - order.stock_ref)
    struct_bid += tie_adj
    struct_offer += tie_adj

    # Calculate structure sizes (limited by thinnest leg adjusted for ratio)
    struct_bid_size = _calc_structure_size(legs, leg_market, for_bid=True)
    struct_offer_size = _calc_structure_size(legs, leg_market, for_bid=False)

    return StructureMarketData(
        leg_data=list(zip(legs, leg_market)),
        stock_price=stock_price,
        stock_ref=order.stock_ref,
        delta=order.delta,
        structure_bid=struct_bid,
        structure_offer=struct_offer,
        structure_bid_size=struct_bid_size,
        structure_offer_size=struct_offer_size,
    )


def _calc_structure_size(
    legs: list[OptionLeg],
    leg_market: list[LegMarketData],
    for_bid: bool,
) -> int:
    """Calculate max structure quantity based on screen liquidity.

    Each leg's available size is divided by its ratio-per-structure
    to find how many structures can be filled.
    """
    min_structures = float("inf")
    base_qty = min(leg.quantity for leg in legs) if legs else 1
    if base_qty <= 0:
        base_qty = 1

    for leg, mkt in zip(legs, leg_market):
        is_buy = leg.direction > 0
        if for_bid:
            # Structure bid: someone buys from market
            # BUY legs → need offer_size, SELL legs → need bid_size
            available = mkt.offer_size if is_buy else mkt.bid_size
        else:
            # Structure offer: someone sells to market
            # BUY legs → need bid_size, SELL legs → need offer_size
            available = mkt.bid_size if is_buy else mkt.offer_size

        ratio = leg.quantity / base_qty
        if ratio > 0:
            structures_possible = available / ratio
            min_structures = min(min_structures, structures_possible)

    return int(min_structures) if min_structures != float("inf") else 0
