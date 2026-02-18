"""Pydantic request/response models for the Options Pricer API."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class ParseRequest(BaseModel):
    text: str


class LegSpec(BaseModel):
    underlying: str | None = None
    expiry: date
    strike: float
    option_type: str  # "call" or "put"
    side: str  # "buy" or "sell"
    quantity: int = 1
    ratio: int = 1


class PriceRequest(BaseModel):
    underlying: str
    structure_name: str
    legs: list[LegSpec]
    stock_ref: float = 0.0
    delta: float = 0.0
    price: float = 0.0
    quote_side: str = "bid"
    quantity: int = 1


class OrderCreateRequest(BaseModel):
    """Full order record to add to the blotter."""

    id: str
    added_time: str
    underlying: str
    structure: str
    bid: str = "--"
    mid: str = "--"
    offer: str = "--"
    bid_size: str = "--"
    offer_size: str = "--"
    side: str = ""
    size: str = ""
    traded: str = "No"
    bought_sold: str = ""
    traded_price: str = ""
    initiator: str = ""
    pnl: str = ""
    multiplier: int = 100

    # Recall data (underscore-prefixed, stored but not displayed)
    _table_data: list[dict] | None = None
    _underlying: str | None = None
    _structure_type: str | None = None
    _stock_ref: float | None = None
    _delta: float | None = None
    _broker_price: float | None = None
    _quote_side: str | None = None
    _quantity: int | None = None
    _current_structure: dict | None = None

    class Config:
        # Allow underscore-prefixed fields to be set from dict
        populate_by_name = True


class OrderUpdateRequest(BaseModel):
    """Partial update for an existing order (manual fields only)."""

    side: str | None = None
    size: str | None = None
    traded: str | None = None
    bought_sold: str | None = None
    traded_price: str | None = None
    initiator: str | None = None


class OrderDeleteRequest(BaseModel):
    ids: list[str]


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class LegResponse(BaseModel):
    underlying: str
    expiry: date
    strike: float
    option_type: str
    side: str
    quantity: int
    ratio: int


class ParseResponse(BaseModel):
    underlying: str
    structure_name: str
    legs: list[LegResponse]
    stock_ref: float
    delta: float
    price: float
    quote_side: str
    quantity: int
    raw_text: str = ""


class LegRow(BaseModel):
    leg: str
    expiry: str
    strike: float | str
    type: str
    ratio: int | str
    bid_size: str
    bid: str
    mid: str
    offer: str
    offer_size: str


class OrderHeader(BaseModel):
    underlying: str
    structure_name: str
    stock_ref: float
    stock_price: float
    delta: float


class BrokerQuote(BaseModel):
    broker_price: float
    quote_side: str
    screen_mid: float | None = None
    edge: float | None = None


class CurrentStructure(BaseModel):
    underlying: str
    structure_name: str
    structure_detail: str
    bid: float | None = None
    mid: float | None = None
    offer: float | None = None
    bid_size: int | None = None
    offer_size: int | None = None
    multiplier: int = 100


class PriceResponse(BaseModel):
    table_data: list[LegRow]
    header: OrderHeader
    broker_quote: BrokerQuote | None = None
    current_structure: CurrentStructure


class OrdersResponse(BaseModel):
    orders: list[dict]


class OrderResponse(BaseModel):
    order: dict


class SourceResponse(BaseModel):
    source: str
    connected: bool
    error: str | None = None


class HealthResponse(BaseModel):
    source: str
    status: str
