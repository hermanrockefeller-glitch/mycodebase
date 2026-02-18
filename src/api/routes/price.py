"""POST /api/price — fetch market data and price a structure."""

import logging

from fastapi import APIRouter, HTTPException

from options_pricer.models import (
    LegMarketData,
    OptionLeg,
    OptionStructure,
    OptionType,
    ParsedOrder,
    QuoteSide,
    Side,
)
from options_pricer.structure_pricer import price_structure_from_market

from ..dependencies import get_client
from ..schemas import (
    BrokerQuote,
    CurrentStructure,
    LegRow,
    OrderHeader,
    PriceRequest,
    PriceResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()

_TYPE_MAP = {"call": OptionType.CALL, "put": OptionType.PUT}
_SIDE_MAP = {"buy": Side.BUY, "sell": Side.SELL}


def _build_parsed_order(req: PriceRequest) -> ParsedOrder:
    """Reconstruct a ParsedOrder from the API request."""
    legs = [
        OptionLeg(
            underlying=spec.underlying or req.underlying,
            expiry=spec.expiry,
            strike=spec.strike,
            option_type=_TYPE_MAP[spec.option_type],
            side=_SIDE_MAP[spec.side],
            quantity=spec.quantity,
            ratio=spec.ratio,
        )
        for spec in req.legs
    ]

    return ParsedOrder(
        underlying=req.underlying,
        structure=OptionStructure(
            name=req.structure_name,
            legs=legs,
            description="API request",
        ),
        stock_ref=req.stock_ref,
        delta=req.delta,
        price=req.price,
        quote_side=QuoteSide(req.quote_side),
        quantity=req.quantity,
        raw_text="",
    )


def _fetch_and_price(order: ParsedOrder):
    """Fetch market data for each leg and price the structure."""
    client = get_client()
    spot = client.get_spot(order.underlying)
    if spot is None or spot == 0:
        spot = order.stock_ref if order.stock_ref > 0 else 100.0

    leg_market: list[LegMarketData] = []
    for leg in order.structure.legs:
        quote = client.get_option_quote(
            leg.underlying, leg.expiry, leg.strike, leg.option_type.value,
        )
        leg_market.append(LegMarketData(
            bid=quote.bid,
            bid_size=quote.bid_size,
            offer=quote.offer,
            offer_size=quote.offer_size,
        ))

    struct_data = price_structure_from_market(order, leg_market, spot)
    multiplier = client.get_contract_multiplier(order.underlying)
    return spot, leg_market, struct_data, multiplier


def _build_table_rows(order: ParsedOrder, leg_market, struct_data) -> list[LegRow]:
    """Build table rows from a priced order (mirrors app.py _build_table_data)."""
    rows = []
    base_qty = (
        min(leg.quantity for leg in order.structure.legs)
        if order.structure.legs else 1
    )

    for i, (leg, mkt) in enumerate(zip(order.structure.legs, leg_market)):
        type_code = "C" if leg.option_type == OptionType.CALL else "P"
        exp_str = leg.expiry.strftime("%b%y") if leg.expiry else ""
        ratio = leg.quantity // base_qty
        signed_ratio = ratio if leg.side == Side.BUY else -ratio

        both_failed = (mkt.bid == 0 and mkt.offer == 0)
        bid_str = "--" if mkt.bid == 0 else f"{mkt.bid:.2f}"
        offer_str = "--" if mkt.offer == 0 else f"{mkt.offer:.2f}"
        if mkt.bid > 0 and mkt.offer > 0:
            mid_str = f"{(mkt.bid + mkt.offer) / 2.0:.2f}"
        elif both_failed:
            mid_str = "--"
        else:
            mid_str = bid_str if mkt.bid > 0 else offer_str

        rows.append(LegRow(
            leg=f"Leg {i + 1}",
            expiry=exp_str,
            strike=leg.strike,
            type=type_code,
            ratio=signed_ratio,
            bid_size="--" if both_failed else str(mkt.bid_size),
            bid=bid_str,
            mid=mid_str,
            offer=offer_str,
            offer_size="--" if both_failed else str(mkt.offer_size),
        ))

    any_leg_failed = any(m.bid == 0 and m.offer == 0 for m in leg_market)

    if any_leg_failed:
        rows.append(LegRow(
            leg="Structure", expiry="", strike="", type="", ratio="",
            bid_size="--", bid="--", mid="--", offer="--", offer_size="--",
        ))
    else:
        rows.append(LegRow(
            leg="Structure", expiry="", strike="", type="", ratio="",
            bid_size=str(struct_data.structure_bid_size),
            bid=f"{struct_data.structure_bid:.2f}",
            mid=f"{struct_data.structure_mid:.2f}",
            offer=f"{struct_data.structure_offer:.2f}",
            offer_size=str(struct_data.structure_offer_size),
        ))

    return rows


@router.post("/price", response_model=PriceResponse)
def price_structure(req: PriceRequest):
    order = _build_parsed_order(req)

    try:
        spot, leg_market, struct_data, multiplier = _fetch_and_price(order)
    except Exception as e:
        logger.exception("Pricing failed")
        raise HTTPException(status_code=500, detail=f"Pricing error: {e}")

    table_rows = _build_table_rows(order, leg_market, struct_data)

    any_leg_failed = any(m.bid == 0 and m.offer == 0 for m in leg_market)
    if any_leg_failed:
        disp_bid = disp_mid = disp_offer = None
        bid_size = offer_size = None
    else:
        disp_bid = struct_data.structure_bid
        disp_offer = struct_data.structure_offer
        disp_mid = struct_data.structure_mid
        bid_size = struct_data.structure_bid_size
        offer_size = struct_data.structure_offer_size

    header = OrderHeader(
        underlying=order.underlying,
        structure_name=order.structure.name.upper(),
        stock_ref=order.stock_ref,
        stock_price=spot,
        delta=order.delta,
    )

    broker_quote = None
    if order.price > 0 and disp_mid is not None:
        edge = order.price - disp_mid
        broker_quote = BrokerQuote(
            broker_price=order.price,
            quote_side=order.quote_side.value.upper(),
            screen_mid=disp_mid,
            edge=edge,
        )
    elif order.price > 0:
        broker_quote = BrokerQuote(
            broker_price=order.price,
            quote_side=order.quote_side.value.upper(),
        )

    leg_details = []
    for leg in order.structure.legs:
        t = leg.option_type.value[0].upper()
        exp_str = leg.expiry.strftime("%b%y") if leg.expiry else ""
        leg_details.append(f"{leg.strike:.0f}{t} {exp_str}")

    current_structure = CurrentStructure(
        underlying=order.underlying,
        structure_name=order.structure.name.upper(),
        structure_detail=" / ".join(leg_details),
        bid=disp_bid,
        mid=disp_mid,
        offer=disp_offer,
        bid_size=bid_size,
        offer_size=offer_size,
        multiplier=multiplier,
    )

    return PriceResponse(
        table_data=table_rows,
        header=header,
        broker_quote=broker_quote,
        current_structure=current_structure,
    )
