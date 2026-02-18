"""POST /api/parse — parse IDB broker shorthand into a structured order."""

from fastapi import APIRouter, HTTPException

from options_pricer.parser import parse_order

from ..schemas import LegResponse, ParseRequest, ParseResponse

router = APIRouter()


@router.post("/parse", response_model=ParseResponse)
def parse_order_text(req: ParseRequest):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Order text is empty")

    try:
        order = parse_order(req.text)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    legs = [
        LegResponse(
            underlying=leg.underlying,
            expiry=leg.expiry,
            strike=leg.strike,
            option_type=leg.option_type.value,
            side=leg.side.value,
            quantity=leg.quantity,
            ratio=leg.ratio,
        )
        for leg in order.structure.legs
    ]

    return ParseResponse(
        underlying=order.underlying,
        structure_name=order.structure.name,
        legs=legs,
        stock_ref=order.stock_ref,
        delta=order.delta,
        price=order.price,
        quote_side=order.quote_side.value,
        quantity=order.quantity,
        raw_text=order.raw_text,
    )
