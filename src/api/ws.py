"""WebSocket endpoint and background price broadcaster.

Replaces Dash's dcc.Interval + dcc.Store pattern with a single multiplexed
WebSocket connection. Background task reprices all blotter orders every second
and broadcasts updates to all connected clients.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from datetime import date

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from options_pricer.models import (
    LegMarketData,
    OptionLeg,
    OptionStructure,
    OptionType,
    ParsedOrder,
    QuoteSide,
    Side,
)
from options_pricer.order_store import load_orders, save_orders_locked
from options_pricer.parser import parse_expiry
from options_pricer.structure_pricer import price_structure_from_market

from .dependencies import get_client, manager

logger = logging.getLogger(__name__)
router = APIRouter()

# Per-connection ticker subscriptions
_ticker_subscriptions: dict[WebSocket, str] = {}

_TYPE_MAP = {"C": OptionType.CALL, "P": OptionType.PUT}


# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------


@router.websocket("/ws/prices")
async def ws_prices(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            data = await ws.receive_text()
            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                continue

            action = msg.get("action")
            if action == "subscribe_ticker":
                underlying = msg.get("underlying", "").strip().upper()
                if underlying:
                    _ticker_subscriptions[ws] = underlying
            elif action == "unsubscribe_ticker":
                _ticker_subscriptions.pop(ws, None)
    except WebSocketDisconnect:
        manager.disconnect(ws)
        _ticker_subscriptions.pop(ws, None)


# ---------------------------------------------------------------------------
# Helpers (mirrored from app.py _build_legs_from_table / _build_table_data)
# ---------------------------------------------------------------------------


def _parse_expiry_str(expiry_str: str) -> date:
    s = expiry_str.strip()
    m = re.match(r'^([A-Za-z]{3})(\d{2})?$', s)
    if not m:
        raise ValueError(f"Invalid expiry: '{expiry_str}'")
    return parse_expiry(m.group(1), m.group(2))


def _build_legs_from_table(table_data, underlying):
    """Build OptionLeg list from table rows. Returns list or None on failure."""
    leg_rows = [r for r in (table_data or []) if str(r.get("leg", "")).startswith("Leg")]
    legs: list[OptionLeg] = []

    for row in leg_rows:
        expiry_str = str(row.get("expiry", "")).strip()
        strike_val = row.get("strike")
        type_val = str(row.get("type", "")).strip()
        ratio_val = row.get("ratio")

        if not expiry_str or not strike_val or type_val not in ("C", "P"):
            continue

        ratio = int(ratio_val) if ratio_val else 0
        if ratio == 0:
            continue

        try:
            expiry = _parse_expiry_str(expiry_str)
        except ValueError:
            continue

        side = Side.BUY if ratio > 0 else Side.SELL
        legs.append(OptionLeg(
            underlying=underlying,
            expiry=expiry,
            strike=float(strike_val),
            option_type=_TYPE_MAP[type_val],
            side=side,
            quantity=abs(ratio),
            ratio=abs(ratio),
        ))

    return legs if legs else None


def _recalc_pnl(order: dict) -> None:
    if (order.get("traded") == "Yes"
            and order.get("traded_price") not in (None, "")
            and order.get("bought_sold") in ("Bought", "Sold")):
        try:
            mid = float(order.get("mid", 0))
            tp = float(order["traded_price"])
            sz = int(order.get("size", 0))
            mult = order.get("multiplier", 100)
            if order["bought_sold"] == "Bought":
                pnl = (mid - tp) * sz * mult
            else:
                pnl = (tp - mid) * sz * mult
            order["pnl"] = f"{pnl:+,.0f}"
        except (ValueError, TypeError):
            order["pnl"] = ""
    elif order.get("traded") != "Yes":
        order["pnl"] = ""


# ---------------------------------------------------------------------------
# Background broadcaster
# ---------------------------------------------------------------------------


async def price_broadcast_loop():
    """Run every 1s: reprice all blotter orders and broadcast via WebSocket.

    Replaces Dash's refresh_blotter_prices callback (app.py lines 1010-1181).
    """
    while True:
        await asyncio.sleep(1)

        try:
            client = get_client()
        except RuntimeError:
            continue  # Client not yet initialised

        orders = load_orders()
        if not orders:
            # Still broadcast health even with no orders
            await _broadcast_health(client)
            await _broadcast_ticker_prices(client)
            continue

        # Phase 1: scan orders, build legs, collect unique tickers
        order_legs: dict[str, tuple[list[OptionLeg], ParsedOrder]] = {}
        unique_underlyings: set[str] = set()
        unique_options: set[tuple[str, date, float, str]] = set()

        for order in orders:
            table_data = order.get("_table_data")
            underlying = order.get("_underlying")
            if not table_data or not underlying:
                continue

            underlying = underlying.strip().upper()
            legs = _build_legs_from_table(table_data, underlying)
            if not legs:
                continue

            struct_name = (order.get("_structure_type") or "custom").replace("_", " ")
            try:
                parsed = ParsedOrder(
                    underlying=underlying,
                    structure=OptionStructure(name=struct_name, legs=legs),
                    stock_ref=float(order.get("_stock_ref") or 0),
                    delta=float(order.get("_delta") or 0),
                    price=float(order.get("_broker_price") or 0),
                    quote_side=QuoteSide(order.get("_quote_side", "bid")),
                    quantity=1,
                )
            except (ValueError, TypeError):
                continue

            order_legs[order["id"]] = (legs, parsed)
            unique_underlyings.add(underlying)
            for leg in legs:
                unique_options.add(
                    (leg.underlying, leg.expiry, leg.strike, leg.option_type.value)
                )

        if not order_legs:
            await _broadcast_health(client)
            await _broadcast_ticker_prices(client)
            continue

        # Batch fetch
        spot_cache: dict[str, float] = {}
        multiplier_cache: dict[str, int] = {}
        quote_cache: dict[tuple, LegMarketData] = {}

        try:
            for ul in unique_underlyings:
                spot_cache[ul] = client.get_spot(ul) or 0.0
                multiplier_cache[ul] = client.get_contract_multiplier(ul)

            for key in unique_options:
                q = client.get_option_quote(*key)
                quote_cache[key] = LegMarketData(
                    bid=q.bid, bid_size=q.bid_size,
                    offer=q.offer, offer_size=q.offer_size,
                )
        except Exception:
            logger.exception("Blotter batch fetch failed")
            await _broadcast_health(client)
            await _broadcast_ticker_prices(client)
            continue

        # Phase 2: price each order from cache
        changed = False
        price_updates: dict[str, dict] = {}

        for order in orders:
            oid = order.get("id")
            if oid not in order_legs:
                continue

            legs, parsed = order_legs[oid]
            spot = spot_cache.get(parsed.underlying, 0.0)
            leg_market = [
                quote_cache.get(
                    (leg.underlying, leg.expiry, leg.strike, leg.option_type.value),
                    LegMarketData(),
                )
                for leg in legs
            ]

            try:
                struct_data = price_structure_from_market(parsed, leg_market, spot)
                any_leg_failed = any(m.bid == 0 and m.offer == 0 for m in leg_market)

                if any_leg_failed:
                    order["bid"] = "--"
                    order["mid"] = "--"
                    order["offer"] = "--"
                    order["bid_size"] = "--"
                    order["offer_size"] = "--"
                else:
                    order["bid"] = f"{struct_data.structure_bid:.2f}"
                    order["mid"] = f"{struct_data.structure_mid:.2f}"
                    order["offer"] = f"{struct_data.structure_offer:.2f}"
                    order["bid_size"] = str(struct_data.structure_bid_size)
                    order["offer_size"] = str(struct_data.structure_offer_size)

                _recalc_pnl(order)
                changed = True

                price_updates[oid] = {
                    "bid": order["bid"],
                    "mid": order["mid"],
                    "offer": order["offer"],
                    "bid_size": order["bid_size"],
                    "offer_size": order["offer_size"],
                    "pnl": order.get("pnl", ""),
                }
            except Exception:
                logger.exception("Blotter reprice failed for order %s", oid)

        if changed:
            save_orders_locked(orders)
            await manager.broadcast({
                "channel": "blotter_prices",
                "timestamp": time.time(),
                "data": price_updates,
            })

        await _broadcast_health(client)
        await _broadcast_ticker_prices(client)


async def _broadcast_health(client) -> None:
    """Broadcast bloomberg health status."""
    spot_check = client.get_spot("SPY")
    await manager.broadcast({
        "channel": "health",
        "data": {
            "source": client.source_name,
            "status": "ok" if spot_check else "failing",
        },
    })


async def _broadcast_ticker_prices(client) -> None:
    """Broadcast live stock prices for subscribed tickers."""
    if not _ticker_subscriptions:
        return

    # Deduplicate tickers
    tickers = set(_ticker_subscriptions.values())
    prices: dict[str, float] = {}
    for ticker in tickers:
        price = client.get_spot(ticker)
        if price is not None:
            prices[ticker] = price

    for ws, ticker in list(_ticker_subscriptions.items()):
        if ticker in prices:
            try:
                await ws.send_text(json.dumps({
                    "channel": "stock_price",
                    "data": {"underlying": ticker, "price": prices[ticker]},
                }))
            except Exception:
                _ticker_subscriptions.pop(ws, None)
