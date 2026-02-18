"""Dash web app entry point for the IDB options pricer dashboard."""

import logging
import re
import time
import uuid
from datetime import date, datetime

logger = logging.getLogger(__name__)

from dash import Dash, Input, Output, State, callback, ctx, html, no_update

from ..bloomberg import BloombergClient, MockBloombergClient, create_client
from ..models import (
    LegMarketData,
    OptionLeg,
    OptionStructure,
    OptionType,
    ParsedOrder,
    QuoteSide,
    Side,
)
from ..order_store import get_orders_mtime, orders_to_display, save_orders_locked
from ..parser import parse_expiry, parse_order
from ..structure_pricer import price_structure_from_market
from .callbacks import recalc_pnl, register_blotter_callbacks
from .layouts import (
    ACCENT,
    ALERT_BANNER_STYLE,
    BADGE_BLUE,
    BADGE_GREEN,
    BADGE_RED,
    BG_SURFACE,
    BORDER_DEFAULT,
    FONT_MONO,
    FONT_SIZE_LG,
    FONT_SIZE_XL,
    GREEN_PRIMARY,
    RADIUS_LG,
    RED_PRIMARY,
    SPACE_LG,
    SPACE_XXL,
    TEXT_STALE,
    WEIGHT_BOLD,
    WEIGHT_SEMIBOLD,
    _EMPTY_ROW,
    _make_empty_rows,
    create_layout,
)

app = Dash(__name__, suppress_callback_exceptions=True)
app.title = "IDB Options Pricer"
app.layout = lambda: create_layout(data_source=_client.source_name)

# Clientside callback: Enter key in textarea triggers pricing
app.clientside_callback(
    """
    function(id) {
        var textarea = document.getElementById("order-text");
        if (textarea && !textarea._enterBound) {
            textarea.addEventListener("keydown", function(e) {
                if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    var store = document.getElementById("textarea-enter");
                    var btn = document.getElementById("price-btn");
                    if (btn) btn.click();
                }
            });
            textarea._enterBound = true;
        }
        return window.dash_clientside.no_update;
    }
    """,
    Output("textarea-enter", "data"),
    Input("order-text", "value"),
)

# Try live Bloomberg first, fall back to mock
_client = create_client(use_mock=False)

# ---------------------------------------------------------------------------
# Callback: toggle data source (Bloomberg / Mock)
# ---------------------------------------------------------------------------

@callback(
    Output("data-source-badge", "children"),
    Output("data-source-badge", "style"),
    Output("toggle-data-source-btn", "children"),
    Output("data-source-error", "children"),
    Output("data-source", "data"),
    Output("bloomberg-health-alert", "style", allow_duplicate=True),
    Output("bloomberg-health-alert", "children", allow_duplicate=True),
    Output("bloomberg-health", "data", allow_duplicate=True),
    Input("toggle-data-source-btn", "n_clicks"),
    State("data-source", "data"),
    prevent_initial_call=True,
)
def toggle_data_source(n_clicks, current_source):
    global _client

    if current_source == "Mock Data":
        # Try switching to Bloomberg
        new_client = BloombergClient()
        if new_client.connect():
            _client = new_client
            return ("Bloomberg API", BADGE_GREEN, "Switch to Mock", "",
                    "Bloomberg API", _HIDDEN, "", "ok")
        else:
            return (
                "Mock Data", BADGE_BLUE, "Switch to Bloomberg",
                "Bloomberg API connection failed. Check Terminal is running.",
                "Mock Data", _HIDDEN, "", "ok",
            )
    else:
        # Switch to Mock
        _client.disconnect()
        _client = MockBloombergClient()
        return ("Mock Data", BADGE_BLUE, "Switch to Bloomberg", "",
                "Mock Data", _HIDDEN, "", "ok")


# ---------------------------------------------------------------------------
# Reusable style constants
# ---------------------------------------------------------------------------

_HIDDEN = {"display": "none"}

_HEADER_VISIBLE_STYLE = {
    "backgroundColor": BG_SURFACE,
    "padding": f"{SPACE_LG} {SPACE_XXL}",
    "borderRadius": RADIUS_LG,
    "marginBottom": "15px",
    "display": "block",
    "borderLeft": f"3px solid {ACCENT}",
}

_BROKER_VISIBLE_STYLE = {
    "backgroundColor": BG_SURFACE,
    "padding": f"15px {SPACE_XXL}",
    "borderRadius": RADIUS_LG,
    "marginTop": "15px",
    "display": "flex",
    "gap": SPACE_XXL,
    "alignItems": "center",
}

_ORDER_INPUT_VISIBLE_STYLE = {
    "backgroundColor": BG_SURFACE,
    "padding": f"15px {SPACE_XXL}",
    "borderRadius": RADIUS_LG,
    "marginTop": "15px",
    "display": "block",
}

# Structure templates for pre-populating table rows.
STRUCTURE_TEMPLATES = {
    "call": [{"type": "C", "ratio": 1}],
    "put": [{"type": "P", "ratio": 1}],
    "put_spread": [
        {"type": "P", "ratio": 1},
        {"type": "P", "ratio": -1},
    ],
    "call_spread": [
        {"type": "C", "ratio": 1},
        {"type": "C", "ratio": -1},
    ],
    "risk_reversal": [
        {"type": "P", "ratio": -1},
        {"type": "C", "ratio": 1},
    ],
    "straddle": [
        {"type": "C", "ratio": 1},
        {"type": "P", "ratio": 1},
    ],
    "strangle": [
        {"type": "P", "ratio": 1},
        {"type": "C", "ratio": 1},
    ],
    "butterfly": [
        {"type": "C", "ratio": 1},
        {"type": "C", "ratio": -2},
        {"type": "C", "ratio": 1},
    ],
    "put_fly": [
        {"type": "P", "ratio": 1},
        {"type": "P", "ratio": -2},
        {"type": "P", "ratio": 1},
    ],
    "call_fly": [
        {"type": "C", "ratio": 1},
        {"type": "C", "ratio": -2},
        {"type": "C", "ratio": 1},
    ],
    "iron_butterfly": [
        {"type": "P", "ratio": 1},
        {"type": "P", "ratio": -1},
        {"type": "C", "ratio": -1},
        {"type": "C", "ratio": 1},
    ],
    "iron_condor": [
        {"type": "P", "ratio": 1},
        {"type": "P", "ratio": -1},
        {"type": "C", "ratio": -1},
        {"type": "C", "ratio": 1},
    ],
    "put_condor": [
        {"type": "P", "ratio": 1},
        {"type": "P", "ratio": -1},
        {"type": "P", "ratio": -1},
        {"type": "P", "ratio": 1},
    ],
    "call_condor": [
        {"type": "C", "ratio": 1},
        {"type": "C", "ratio": -1},
        {"type": "C", "ratio": -1},
        {"type": "C", "ratio": 1},
    ],
    "collar": [
        {"type": "P", "ratio": 1},
        {"type": "C", "ratio": -1},
    ],
    "call_spread_collar": [
        {"type": "P", "ratio": 1},
        {"type": "C", "ratio": -1},
        {"type": "C", "ratio": 1},
    ],
    "put_spread_collar": [
        {"type": "P", "ratio": -1},
        {"type": "P", "ratio": 1},
        {"type": "C", "ratio": -1},
    ],
    "put_stupid": [
        {"type": "P", "ratio": 1},
        {"type": "P", "ratio": 1},
    ],
    "call_stupid": [
        {"type": "C", "ratio": 1},
        {"type": "C", "ratio": 1},
    ],
}

# Map short codes to model enums
_TYPE_MAP = {"C": OptionType.CALL, "P": OptionType.PUT}

# Blotter fields that accept manual user input (never overwritten by auto-refresh)
_MANUAL_FIELDS = ("side", "size", "traded", "bought_sold", "traded_price", "initiator")

# Error tail for price_order (outputs 3-17 when pricing fails)
_PRICE_ORDER_ERR_TAIL = (
    _HIDDEN, [],           # order-header style, content
    _HIDDEN, [],           # broker-quote style, content
    None,                  # current-structure
    _HIDDEN,               # order-input-section
    no_update, no_update,  # underlying, structure-type
    no_update, no_update,  # stock-ref, delta
    no_update, no_update,  # broker-price, quote-side
    no_update,             # quantity
    False,                 # suppress-template
    True,                  # auto-price-suppress
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _fetch_and_price(order):
    """Fetch market data for each leg, price the structure, return outputs."""
    spot = _client.get_spot(order.underlying)
    if spot is None or spot == 0:
        spot = order.stock_ref if order.stock_ref > 0 else 100.0

    leg_market: list[LegMarketData] = []
    for leg in order.structure.legs:
        quote = _client.get_option_quote(
            leg.underlying, leg.expiry, leg.strike, leg.option_type.value,
        )
        leg_market.append(LegMarketData(
            bid=quote.bid,
            bid_size=quote.bid_size,
            offer=quote.offer,
            offer_size=quote.offer_size,
        ))

    struct_data = price_structure_from_market(order, leg_market, spot)
    multiplier = _client.get_contract_multiplier(order.underlying)
    return spot, leg_market, struct_data, multiplier


def _build_table_data(order, leg_market, struct_data):
    """Build the unified table data (input + output columns) from priced order."""
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

        rows.append({
            "leg": f"Leg {i + 1}",
            "expiry": exp_str,
            "strike": leg.strike,
            "type": type_code,
            "ratio": signed_ratio,
            "bid_size": "--" if both_failed else str(mkt.bid_size),
            "bid": bid_str,
            "mid": mid_str,
            "offer": offer_str,
            "offer_size": "--" if both_failed else str(mkt.offer_size),
        })

    # Check if any leg has a completely failed quote
    any_leg_failed = any(
        m.bid == 0 and m.offer == 0 for m in leg_market
    )

    if any_leg_failed:
        # Structure price from partial data is unreliable
        rows.append({
            "leg": "Structure",
            "expiry": "", "strike": "", "type": "", "ratio": "",
            "bid_size": "--", "bid": "--", "mid": "--", "offer": "--", "offer_size": "--",
        })
    else:
        # Structure summary row — struct_bid <= struct_offer by construction
        disp_bid = struct_data.structure_bid
        disp_offer = struct_data.structure_offer
        disp_mid = struct_data.structure_mid

        rows.append({
            "leg": "Structure",
            "expiry": "", "strike": "", "type": "", "ratio": "",
            "bid_size": str(struct_data.structure_bid_size),
            "bid": f"{disp_bid:.2f}",
            "mid": f"{disp_mid:.2f}",
            "offer": f"{disp_offer:.2f}",
            "offer_size": str(struct_data.structure_offer_size),
        })

    return rows


def _build_header_and_extras(order, spot, struct_data, multiplier, leg_market=None):
    """Build order header, broker quote, current-structure store, order input style."""
    header_items = []
    structure_name = order.structure.name.upper()
    header_items.append(
        html.Span(
            f"{order.underlying} {structure_name}",
            style={"color": ACCENT, "fontWeight": WEIGHT_BOLD, "fontSize": FONT_SIZE_XL},
        )
    )
    if order.stock_ref > 0:
        header_items.append(html.Span(f"Tie: ${order.stock_ref:.2f}"))
    header_items.append(html.Span(f"Stock: ${spot:.2f}"))
    if order.delta > 0:
        header_items.append(html.Span(f"Delta: +{order.delta:.0f}"))
    elif order.delta < 0:
        header_items.append(html.Span(f"Delta: {order.delta:.0f}"))

    # Check if any leg has a completely failed quote
    any_leg_failed = (
        leg_market is not None
        and any(m.bid == 0 and m.offer == 0 for m in leg_market)
    )

    if any_leg_failed:
        disp_bid = None
        disp_mid = None
        disp_offer = None
    else:
        # struct_bid <= struct_offer by construction
        disp_bid = struct_data.structure_bid
        disp_offer = struct_data.structure_offer
        disp_mid = struct_data.structure_mid

    broker_style = _HIDDEN
    broker_content = []
    if order.price > 0 and disp_mid is not None:
        side_label = order.quote_side.value.upper()
        broker_content = [
            html.Span(
                f"Broker: {order.price:.2f} {side_label}",
                style={"fontSize": FONT_SIZE_LG, "marginRight": "30px", "fontFamily": FONT_MONO},
            ),
            html.Span(
                f"Screen Mid: {disp_mid:.2f}",
                style={"fontSize": FONT_SIZE_LG, "marginRight": "30px", "fontFamily": FONT_MONO},
            ),
        ]
        edge = order.price - disp_mid
        edge_color = GREEN_PRIMARY if edge > 0 else RED_PRIMARY
        broker_content.append(
            html.Span(
                f"Edge: {edge:+.2f}",
                style={"fontSize": FONT_SIZE_LG, "color": edge_color, "fontWeight": WEIGHT_BOLD, "fontFamily": FONT_MONO},
            )
        )
        broker_style = _BROKER_VISIBLE_STYLE
    elif order.price > 0 and disp_mid is None:
        side_label = order.quote_side.value.upper()
        broker_content = [
            html.Span(
                f"Broker: {order.price:.2f} {side_label}",
                style={"fontSize": FONT_SIZE_LG, "marginRight": "30px", "fontFamily": FONT_MONO},
            ),
            html.Span(
                "Screen Mid: --",
                style={"fontSize": FONT_SIZE_LG, "marginRight": "30px", "color": TEXT_STALE, "fontStyle": "italic", "fontFamily": FONT_MONO},
            ),
        ]
        broker_style = _BROKER_VISIBLE_STYLE

    leg_details = []
    for leg in order.structure.legs:
        type_str = leg.option_type.value[0].upper()
        exp_str = leg.expiry.strftime("%b%y") if leg.expiry else ""
        leg_details.append(f"{leg.strike:.0f}{type_str} {exp_str}")
    structure_detail = " / ".join(leg_details)

    current_data = {
        "underlying": order.underlying,
        "structure_name": structure_name,
        "structure_detail": structure_detail,
        "bid": disp_bid,
        "mid": disp_mid,
        "offer": disp_offer,
        "bid_size": struct_data.structure_bid_size if not any_leg_failed else None,
        "offer_size": struct_data.structure_offer_size if not any_leg_failed else None,
        "multiplier": multiplier,
    }

    return (
        _HEADER_VISIBLE_STYLE, header_items,
        broker_style, broker_content,
        current_data, _ORDER_INPUT_VISIBLE_STYLE,
    )


def _parse_expiry_str(expiry_str: str) -> date:
    """Parse an expiry string like 'Jun26' or 'Mar27' into a date."""
    s = expiry_str.strip()
    m = re.match(r'^([A-Za-z]{3})(\d{2})?$', s)
    if not m:
        raise ValueError(f"Invalid expiry format: '{expiry_str}'. Use e.g. Jun26, Mar27")
    month_str = m.group(1)
    year_str = m.group(2)
    return parse_expiry(month_str, year_str)


def _build_legs_from_table(table_data, underlying, order_qty):
    """Parse table rows into OptionLeg list. Returns (legs, error_msg) tuple."""
    leg_rows = [r for r in (table_data or []) if r.get("leg", "").startswith("Leg")]

    legs: list[OptionLeg] = []
    for i, row in enumerate(leg_rows):
        expiry_str = str(row.get("expiry", "")).strip()
        strike_val = row.get("strike")
        type_val = str(row.get("type", "")).strip()
        ratio_val = row.get("ratio")

        row_has_data = bool(expiry_str or strike_val or type_val or ratio_val)
        if not row_has_data:
            continue

        ratio = int(ratio_val) if ratio_val else 0
        if not expiry_str or not strike_val or type_val not in ("C", "P") or ratio == 0:
            return None, None  # Incomplete row — caller decides how to handle

        try:
            expiry = _parse_expiry_str(expiry_str)
        except ValueError as e:
            return None, f"Leg {i + 1}: {e}"

        side = Side.BUY if ratio > 0 else Side.SELL
        qty = abs(ratio)
        legs.append(OptionLeg(
            underlying=underlying,
            expiry=expiry,
            strike=float(strike_val),
            option_type=_TYPE_MAP[type_val],
            side=side,
            quantity=qty * order_qty,
            ratio=qty,
        ))

    return legs, None


# ---------------------------------------------------------------------------
# Callback: paste-to-parse pricing
# ---------------------------------------------------------------------------

@callback(
    Output("parse-error", "children"),
    Output("pricing-display", "data"),
    Output("order-header", "style"),
    Output("order-header-content", "children"),
    Output("broker-quote-section", "style"),
    Output("broker-quote-content", "children"),
    Output("current-structure", "data"),
    Output("order-input-section", "style"),
    Output("manual-underlying", "value"),
    Output("manual-structure-type", "value"),
    Output("manual-stock-ref", "value"),
    Output("manual-delta", "value"),
    Output("manual-broker-price", "value"),
    Output("manual-quote-side", "value"),
    Output("manual-quantity", "value"),
    Output("suppress-template", "data"),
    Output("auto-price-suppress", "data"),
    Input("price-btn", "n_clicks"),
    State("order-text", "value"),
    prevent_initial_call=True,
)
def price_order(n_clicks, order_text):
    if not order_text:
        return ("Please enter an order.", [], *_PRICE_ORDER_ERR_TAIL)

    try:
        order = parse_order(order_text)
    except ValueError as e:
        return (str(e), [], *_PRICE_ORDER_ERR_TAIL)

    spot, leg_market, struct_data, multiplier = _fetch_and_price(order)
    table_data = _build_table_data(order, leg_market, struct_data)
    header_style, header_items, broker_style, broker_content, current_data, order_input_style = (
        _build_header_and_extras(order, spot, struct_data, multiplier, leg_market)
    )

    struct_name = order.structure.name.lower().replace(" ", "_")
    struct_dropdown = struct_name if struct_name in STRUCTURE_TEMPLATES else None

    return (
        "",                         # parse-error
        table_data,                 # pricing-display data
        header_style,               # order-header style
        header_items,               # order-header-content
        broker_style,               # broker-quote-section style
        broker_content,             # broker-quote-content
        current_data,               # current-structure
        order_input_style,          # order-input-section style
        order.underlying,           # manual-underlying
        struct_dropdown,            # manual-structure-type
        order.stock_ref if order.stock_ref > 0 else None,
        order.delta if order.delta != 0 else None,
        order.price if order.price > 0 else None,
        order.quote_side.value,     # manual-quote-side
        order.quantity if order.quantity > 0 else None,
        True,                       # suppress-template
        True,                       # auto-price-suppress
    )


# ---------------------------------------------------------------------------
# Callback: structure template pre-population
# ---------------------------------------------------------------------------

@callback(
    Output("pricing-display", "data", allow_duplicate=True),
    Output("suppress-template", "data", allow_duplicate=True),
    Output("auto-price-suppress", "data", allow_duplicate=True),
    Input("manual-structure-type", "value"),
    State("suppress-template", "data"),
    prevent_initial_call=True,
)
def populate_table_template(structure_type, suppress):
    if suppress:
        return no_update, False, no_update

    template = STRUCTURE_TEMPLATES.get(structure_type, [])
    if not template:
        return no_update, False, no_update

    rows = []
    for i, t in enumerate(template):
        rows.append({
            **_EMPTY_ROW,
            "leg": f"Leg {i + 1}",
            "type": t["type"],
            "ratio": t.get("ratio", 1),
        })
    return rows, False, True


# ---------------------------------------------------------------------------
# Callback: add/remove table rows
# ---------------------------------------------------------------------------

@callback(
    Output("pricing-display", "data", allow_duplicate=True),
    Output("auto-price-suppress", "data", allow_duplicate=True),
    Input("add-row-btn", "n_clicks"),
    Input("remove-row-btn", "n_clicks"),
    State("pricing-display", "data"),
    prevent_initial_call=True,
)
def toggle_table_rows(add_clicks, remove_clicks, current_data):
    triggered = ctx.triggered_id
    rows = [r for r in (current_data or []) if r.get("leg") != "Structure"]

    if triggered == "add-row-btn":
        n = len(rows) + 1
        rows.append({**_EMPTY_ROW, "leg": f"Leg {n}"})
    elif triggered == "remove-row-btn" and len(rows) > 1:
        rows.pop()

    return rows, True


# ---------------------------------------------------------------------------
# Callback: flip structure (invert ratios + delta)
# ---------------------------------------------------------------------------

@callback(
    Output("pricing-display", "data", allow_duplicate=True),
    Output("manual-delta", "value", allow_duplicate=True),
    Output("auto-price-suppress", "data", allow_duplicate=True),
    Input("flip-btn", "n_clicks"),
    State("pricing-display", "data"),
    State("manual-delta", "value"),
    prevent_initial_call=True,
)
def flip_structure(n_clicks, table_data, current_delta):
    """Invert all signed ratios and flip the delta sign."""
    new_rows = []
    for row in (table_data or []):
        if row.get("leg", "").startswith("Leg"):
            ratio = row.get("ratio")
            if ratio is not None and ratio != "" and ratio != 0:
                row = {**row, "ratio": -int(ratio)}
        new_rows.append(row)

    new_delta = -current_delta if current_delta else None
    return new_rows, new_delta, False


# ---------------------------------------------------------------------------
# Callback: auto-price from table
# ---------------------------------------------------------------------------

@callback(
    Output("table-error", "children"),
    Output("pricing-display", "data", allow_duplicate=True),
    Output("order-header", "style", allow_duplicate=True),
    Output("order-header-content", "children", allow_duplicate=True),
    Output("broker-quote-section", "style", allow_duplicate=True),
    Output("broker-quote-content", "children", allow_duplicate=True),
    Output("current-structure", "data", allow_duplicate=True),
    Output("order-input-section", "style", allow_duplicate=True),
    Output("auto-price-suppress", "data", allow_duplicate=True),
    Input("pricing-display", "data_timestamp"),
    Input("manual-underlying", "value"),
    Input("manual-stock-ref", "value"),
    Input("manual-delta", "value"),
    Input("manual-broker-price", "value"),
    Input("manual-quote-side", "value"),
    Input("manual-quantity", "value"),
    State("auto-price-suppress", "data"),
    State("pricing-display", "data"),
    State("manual-structure-type", "value"),
    prevent_initial_call=True,
)
def auto_price_from_table(data_ts, underlying, stock_ref, delta,
                          broker_price, quote_side_val, order_qty,
                          suppress, table_data, struct_type):
    noop = ("",) + (no_update,) * 7 + (False,)

    # Suppress prevents self-loop: callback outputs table → data_timestamp
    # fires → callback runs again → suppress=True → returns noop
    if suppress:
        return noop

    if not underlying or not underlying.strip():
        return noop

    underlying = underlying.strip().upper()
    order_qty_val = int(order_qty) if order_qty else 1

    legs, err_msg = _build_legs_from_table(table_data, underlying, order_qty_val)

    if err_msg:
        return (err_msg,) + (no_update,) * 7 + (False,)

    if legs is None or len(legs) == 0:
        return noop

    struct_name = struct_type.replace("_", " ") if struct_type else "custom"
    order = ParsedOrder(
        underlying=underlying,
        structure=OptionStructure(name=struct_name, legs=legs, description="Table entry"),
        stock_ref=float(stock_ref) if stock_ref else 0.0,
        delta=float(delta) if delta else 0.0,
        price=float(broker_price) if broker_price else 0.0,
        quote_side=QuoteSide(quote_side_val) if quote_side_val else QuoteSide.BID,
        quantity=order_qty_val,
        raw_text="Table entry",
    )

    try:
        spot, leg_market, struct_data, multiplier = _fetch_and_price(order)
    except Exception as e:
        return (f"Pricing error: {e}",) + (no_update,) * 7 + (False,)

    new_table = _build_table_data(order, leg_market, struct_data)

    header_style, header_items, broker_style, broker_content, current_data, order_input_style = (
        _build_header_and_extras(order, spot, struct_data, multiplier, leg_market)
    )

    return (
        "",                 # table-error
        new_table,          # pricing-display data
        header_style,       # order-header style
        header_items,       # order-header-content
        broker_style,       # broker-quote-section style
        broker_content,     # broker-quote-content
        current_data,       # current-structure
        order_input_style,  # order-input-section style
        True,               # auto-price-suppress (prevent self-loop)
    )


# ---------------------------------------------------------------------------
# Callback: live-refresh header + broker quote (interval-driven, NO table update)
# ---------------------------------------------------------------------------

@callback(
    Output("order-header-content", "children", allow_duplicate=True),
    Output("broker-quote-content", "children", allow_duplicate=True),
    Output("bloomberg-health-alert", "style", allow_duplicate=True),
    Output("bloomberg-health-alert", "children", allow_duplicate=True),
    Output("data-source-badge", "style", allow_duplicate=True),
    Output("data-source-badge", "children", allow_duplicate=True),
    Output("bloomberg-health", "data", allow_duplicate=True),
    Input("live-refresh-interval", "n_intervals"),
    State("current-structure", "data"),
    State("manual-underlying", "value"),
    State("manual-stock-ref", "value"),
    State("manual-delta", "value"),
    State("manual-broker-price", "value"),
    State("manual-quote-side", "value"),
    State("data-source", "data"),
    prevent_initial_call=True,
)
def refresh_live_display(n_intervals, current_data, underlying,
                         stock_ref, delta, broker_price, quote_side_val,
                         data_source):
    """Update header bar (live stock price), broker edge, and Bloomberg health every tick.

    Never touches pricing-display.data or any editable field — only
    updates display-only HTML components that have no editing state.
    """
    is_bloomberg = (data_source == "Bloomberg API")

    # Default health outputs: no alert, keep current badge
    alert_style = _HIDDEN
    alert_text = ""
    badge_style = no_update
    badge_text = no_update
    health = "ok"

    if not current_data or not underlying or not underlying.strip():
        # Even without a structure, check Bloomberg health if we have an underlying
        if is_bloomberg and underlying and underlying.strip():
            raw_spot = _client.get_spot(underlying.strip().upper())
            if raw_spot is None:
                alert_style = ALERT_BANNER_STYLE
                alert_text = "Bloomberg API is not responding. Market data may be unavailable."
                badge_style = BADGE_RED
                badge_text = "Bloomberg API"
                health = "failing"
            else:
                badge_style = BADGE_GREEN
                badge_text = "Bloomberg API"
        return (no_update, no_update,
                alert_style, alert_text, badge_style, badge_text, health)

    underlying = underlying.strip().upper()
    raw_spot = _client.get_spot(underlying)
    spot = raw_spot or 0.0

    # Bloomberg health detection
    if is_bloomberg and raw_spot is None:
        alert_style = ALERT_BANNER_STYLE
        alert_text = "Bloomberg API is not responding. Market data may be unavailable."
        badge_style = BADGE_RED
        badge_text = "Bloomberg API"
        health = "failing"
    elif is_bloomberg:
        badge_style = BADGE_GREEN
        badge_text = "Bloomberg API"

    # --- Rebuild header with live spot price ---
    structure_name = current_data.get("structure_name", "")
    header_items = [
        html.Span(
            f"{underlying} {structure_name}",
            style={"color": ACCENT, "fontWeight": WEIGHT_BOLD, "fontSize": FONT_SIZE_XL},
        ),
    ]
    if stock_ref:
        header_items.append(html.Span(f"Tie: ${float(stock_ref):.2f}"))
    header_items.append(html.Span(f"Stock: ${spot:.2f}"))
    if delta:
        d = float(delta)
        if d > 0:
            header_items.append(html.Span(f"Delta: +{d:.0f}"))
        elif d < 0:
            header_items.append(html.Span(f"Delta: {d:.0f}"))

    # --- Rebuild broker edge using stored mid from last price calculation ---
    broker_content = no_update
    mid = current_data.get("mid")
    if broker_price and mid is not None:
        try:
            bp = float(broker_price)
            mid_f = float(mid)
            if bp > 0 and mid_f > 0:
                side_label = quote_side_val.upper() if quote_side_val else "BID"
                edge = bp - mid_f
                edge_color = GREEN_PRIMARY if edge > 0 else RED_PRIMARY
                broker_content = [
                    html.Span(
                        f"Broker: {bp:.2f} {side_label}",
                        style={"fontSize": FONT_SIZE_LG, "marginRight": "30px", "fontFamily": FONT_MONO},
                    ),
                    html.Span(
                        f"Screen Mid: {mid_f:.2f}",
                        style={"fontSize": FONT_SIZE_LG, "marginRight": "30px", "fontFamily": FONT_MONO},
                    ),
                    html.Span(
                        f"Edge: {edge:+.2f}",
                        style={
                            "fontSize": FONT_SIZE_LG,
                            "color": edge_color,
                            "fontWeight": WEIGHT_BOLD,
                            "fontFamily": FONT_MONO,
                        },
                    ),
                ]
        except (ValueError, TypeError):
            logger.exception("Failed to build broker quote display")

    return (header_items, broker_content,
            alert_style, alert_text, badge_style, badge_text, health)


# ---------------------------------------------------------------------------
# Callback: clear / reset (does NOT clear the order blotter)
# ---------------------------------------------------------------------------

@callback(
    Output("pricing-display", "data", allow_duplicate=True),
    Output("order-text", "value"),
    Output("manual-underlying", "value", allow_duplicate=True),
    Output("manual-structure-type", "value", allow_duplicate=True),
    Output("manual-stock-ref", "value", allow_duplicate=True),
    Output("manual-delta", "value", allow_duplicate=True),
    Output("manual-broker-price", "value", allow_duplicate=True),
    Output("manual-quote-side", "value", allow_duplicate=True),
    Output("manual-quantity", "value", allow_duplicate=True),
    Output("order-header", "style", allow_duplicate=True),
    Output("order-header-content", "children", allow_duplicate=True),
    Output("broker-quote-section", "style", allow_duplicate=True),
    Output("broker-quote-content", "children", allow_duplicate=True),
    Output("current-structure", "data", allow_duplicate=True),
    Output("order-input-section", "style", allow_duplicate=True),
    Output("parse-error", "children", allow_duplicate=True),
    Output("table-error", "children", allow_duplicate=True),
    Output("auto-price-suppress", "data", allow_duplicate=True),
    Input("clear-btn", "n_clicks"),
    prevent_initial_call=True,
)
def clear_all(n_clicks):
    return (
        _make_empty_rows(2),  # pricing-display
        "",                   # order-text
        None,                 # manual-underlying
        None,                 # manual-structure-type
        None,                 # manual-stock-ref
        None,                 # manual-delta
        None,                 # manual-broker-price
        None,                 # manual-quote-side (neutral)
        None,                 # manual-quantity (empty)
        _HIDDEN,              # order-header style
        [],                   # order-header-content
        _HIDDEN,              # broker-quote-section style
        [],                   # broker-quote-content
        None,                 # current-structure
        _HIDDEN,              # order-input-section style
        "",                   # parse-error
        "",                   # table-error
        True,                 # auto-price-suppress
    )


# ---------------------------------------------------------------------------
# Callback: add order to blotter
# ---------------------------------------------------------------------------

@callback(
    Output("blotter-table", "data"),
    Output("order-store", "data"),
    Output("order-error", "children"),
    Output("order-side", "value"),
    Output("order-size", "value"),
    Output("blotter-edit-suppress", "data"),
    Output("last-write-time", "data"),
    Input("add-order-btn", "n_clicks"),
    State("current-structure", "data"),
    State("order-store", "data"),
    # Capture pricer state for recall
    State("pricing-display", "data"),
    State("manual-underlying", "value"),
    State("manual-structure-type", "value"),
    State("manual-stock-ref", "value"),
    State("manual-delta", "value"),
    State("manual-broker-price", "value"),
    State("manual-quote-side", "value"),
    State("manual-quantity", "value"),
    prevent_initial_call=True,
)
def add_order(n_clicks, current_data, existing_orders,
              table_data, toolbar_underlying, toolbar_struct, toolbar_ref,
              toolbar_delta, toolbar_broker_px, toolbar_quote_side, toolbar_qty):
    if not current_data:
        return no_update, no_update, "Price a structure first.", no_update, no_update, no_update, no_update

    # Map toolbar side to blotter side
    side_map = {"bid": "Bid", "offer": "Offered"}
    blotter_side = side_map.get(toolbar_quote_side, "")
    size_str = str(int(toolbar_qty)) if toolbar_qty else ""

    # Handle failed quotes (None values in current_data)
    bid_val = current_data.get("bid")
    mid_val = current_data.get("mid")
    offer_val = current_data.get("offer")
    bid_size_val = current_data.get("bid_size")
    offer_size_val = current_data.get("offer_size")

    order_record = {
        "id": str(uuid.uuid4()),
        "added_time": datetime.now().strftime("%H:%M"),
        "underlying": current_data["underlying"],
        "structure": f"{current_data['structure_name']} {current_data['structure_detail']}",
        "bid_size": "--" if bid_size_val is None else str(bid_size_val),
        "bid": "--" if bid_val is None else f"{bid_val:.2f}",
        "mid": "--" if mid_val is None else f"{mid_val:.2f}",
        "offer": "--" if offer_val is None else f"{offer_val:.2f}",
        "offer_size": "--" if offer_size_val is None else str(offer_size_val),
        "side": blotter_side,
        "size": size_str,
        "traded": "No",
        "bought_sold": "",
        "traded_price": "",
        "initiator": "",
        "pnl": "",
        "multiplier": current_data.get("multiplier", 100),
        # Recall data
        "_table_data": table_data,
        "_underlying": toolbar_underlying,
        "_structure_type": toolbar_struct,
        "_stock_ref": toolbar_ref,
        "_delta": toolbar_delta,
        "_broker_price": toolbar_broker_px,
        "_quote_side": toolbar_quote_side,
        "_quantity": toolbar_qty,
        "_current_structure": current_data,
    }

    orders = existing_orders or []
    orders.append(order_record)

    # Persist to JSON (with cross-process lock)
    save_orders_locked(orders)
    new_mtime = get_orders_mtime()

    # Build display rows (strip underscore fields)
    blotter_rows = orders_to_display(orders)

    return blotter_rows, orders, "", None, None, True, new_mtime


# ---------------------------------------------------------------------------
# Shared blotter callbacks (poll, sync edits, column toggle, column visibility)
# ---------------------------------------------------------------------------
register_blotter_callbacks()


# ---------------------------------------------------------------------------
# Callback: live-refresh blotter order prices
# ---------------------------------------------------------------------------

@callback(
    Output("order-store", "data", allow_duplicate=True),
    Output("last-write-time", "data", allow_duplicate=True),
    Input("live-refresh-interval", "n_intervals"),
    State("order-store", "data"),
    State("blotter-table", "data"),
    State("blotter-table", "data_timestamp"),
    prevent_initial_call=True,
)
def refresh_blotter_prices(n_intervals, orders, blotter_data, data_ts):
    """Re-price every blotter order from live market data each tick.

    Updates the client-side order store and persists to JSON so the Admin
    Dashboard can pick up fresh prices via file polling.  Stamps
    last-write-time so the pricer's own poll callback skips reloading.
    """
    if not orders:
        return no_update, no_update

    # Only merge manual fields from the pricer's blotter table if a cell
    # was edited recently on the pricer.  This protects uncommitted pricer
    # edits without overwriting admin dashboard edits that arrived via
    # JSON polling into order-store.  The pricer's blotter-table is stale
    # for admin-originated edits (no push_store_to_blotter on the pricer),
    # so an unconditional merge would revert admin changes.
    now_ms = time.time() * 1000
    if data_ts and (now_ms - data_ts) < 5000:
        blotter_by_id = {r["id"]: r for r in (blotter_data or []) if "id" in r}
        for order in orders:
            row = blotter_by_id.get(order.get("id"))
            if row:
                for f in _MANUAL_FIELDS:
                    if f in row:
                        order[f] = row[f]

    # Phase 1: scan orders, build legs, collect unique tickers for batch fetch
    order_legs = {}  # id → (legs, ParsedOrder)
    unique_underlyings = set()
    unique_options = set()  # (underlying, expiry, strike, opt_type_str)

    for order in orders:
        table_data = order.get("_table_data")
        underlying = order.get("_underlying")
        if not table_data or not underlying:
            continue

        legs, err = _build_legs_from_table(table_data, underlying.strip().upper(), 1)
        if not legs:
            continue

        struct_name = (order.get("_structure_type") or "custom").replace("_", " ")
        try:
            parsed = ParsedOrder(
                underlying=underlying.strip().upper(),
                structure=OptionStructure(name=struct_name, legs=legs),
                stock_ref=float(order.get("_stock_ref") or 0),
                delta=float(order.get("_delta") or 0),
                price=float(order.get("_broker_price") or 0),
                quote_side=QuoteSide(order.get("_quote_side", "bid")),
                quantity=1,
                raw_text="",
            )
        except (ValueError, TypeError):
            logger.exception("Blotter reprice: failed to build ParsedOrder for order %s", order.get("id"))
            continue

        order_legs[order["id"]] = (legs, parsed)
        unique_underlyings.add(parsed.underlying)
        for leg in legs:
            unique_options.add(
                (leg.underlying, leg.expiry, leg.strike, leg.option_type.value)
            )

    if not order_legs:
        return no_update, no_update

    # Batch fetch: each unique spot / quote / multiplier fetched once
    spot_cache = {}
    multiplier_cache = {}
    quote_cache = {}

    try:
        for ul in unique_underlyings:
            spot_cache[ul] = _client.get_spot(ul) or 0.0
            multiplier_cache[ul] = _client.get_contract_multiplier(ul)

        for key in unique_options:
            q = _client.get_option_quote(*key)
            quote_cache[key] = LegMarketData(
                bid=q.bid, bid_size=q.bid_size, offer=q.offer, offer_size=q.offer_size,
            )
    except Exception:
        logger.exception("Blotter batch fetch failed")
        return no_update, no_update

    # Phase 2: price each order from cache (no additional API calls)
    changed = False
    for order in orders:
        if order["id"] not in order_legs:
            continue

        legs, parsed = order_legs[order["id"]]
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
            multiplier = multiplier_cache.get(parsed.underlying, 100)
            new_table = _build_table_data(parsed, leg_market, struct_data)

            any_leg_failed = any(m.bid == 0 and m.offer == 0 for m in leg_market)

            if any_leg_failed:
                order["bid"] = "--"
                order["mid"] = "--"
                order["offer"] = "--"
                order["bid_size"] = "--"
                order["offer_size"] = "--"
                disp_bid = None
                disp_mid = None
                disp_offer = None
            else:
                disp_bid = struct_data.structure_bid
                disp_offer = struct_data.structure_offer
                disp_mid = struct_data.structure_mid

                # Update display fields (pricing only — manual fields untouched)
                order["bid"] = f"{disp_bid:.2f}"
                order["mid"] = f"{disp_mid:.2f}"
                order["offer"] = f"{disp_offer:.2f}"
                order["bid_size"] = str(struct_data.structure_bid_size)
                order["offer_size"] = str(struct_data.structure_offer_size)

            # Update recall data
            order["_table_data"] = new_table
            struct_type = order.get("_structure_type", "custom")
            leg_details = []
            for leg in legs:
                t = "C" if leg.option_type == OptionType.CALL else "P"
                exp_str = leg.expiry.strftime("%b%y") if leg.expiry else ""
                leg_details.append(f"{leg.strike:.0f}{t} {exp_str}")
            order["_current_structure"] = {
                "underlying": parsed.underlying,
                "structure_name": struct_type.upper().replace("_", " "),
                "structure_detail": " / ".join(leg_details),
                "bid": disp_bid,
                "mid": disp_mid,
                "offer": disp_offer,
                "bid_size": struct_data.structure_bid_size if not any_leg_failed else None,
                "offer_size": struct_data.structure_offer_size if not any_leg_failed else None,
                "multiplier": multiplier,
            }
        except Exception:
            logger.exception("Blotter reprice failed for order %s", order.get("id"))
            continue

        recalc_pnl(order)
        changed = True

    if not changed:
        return no_update, no_update

    # Persist to JSON so the Admin Dashboard picks up fresh prices via polling.
    save_orders_locked(orders)
    new_mtime = get_orders_mtime()
    return orders, new_mtime


# ---------------------------------------------------------------------------
# Callback: recall order from blotter into pricer
# ---------------------------------------------------------------------------

@callback(
    Output("pricing-display", "data", allow_duplicate=True),
    Output("manual-underlying", "value", allow_duplicate=True),
    Output("manual-structure-type", "value", allow_duplicate=True),
    Output("manual-stock-ref", "value", allow_duplicate=True),
    Output("manual-delta", "value", allow_duplicate=True),
    Output("manual-broker-price", "value", allow_duplicate=True),
    Output("manual-quote-side", "value", allow_duplicate=True),
    Output("manual-quantity", "value", allow_duplicate=True),
    Output("order-header", "style", allow_duplicate=True),
    Output("order-header-content", "children", allow_duplicate=True),
    Output("broker-quote-section", "style", allow_duplicate=True),
    Output("broker-quote-content", "children", allow_duplicate=True),
    Output("current-structure", "data", allow_duplicate=True),
    Output("order-input-section", "style", allow_duplicate=True),
    Output("suppress-template", "data", allow_duplicate=True),
    Output("auto-price-suppress", "data", allow_duplicate=True),
    Input("blotter-table", "active_cell"),
    State("blotter-table", "derived_virtual_data"),
    State("order-store", "data"),
    prevent_initial_call=True,
)
def recall_order(active_cell, virtual_data, orders):
    if not active_cell or not orders:
        return (no_update,) * 16

    # derived_virtual_data reflects the current sorted/filtered display order,
    # so active_cell["row"] indexes correctly into it
    blotter_view = virtual_data or []
    row_idx = active_cell["row"]
    if row_idx >= len(blotter_view):
        return (no_update,) * 16

    # Get the order id from the displayed row (handles sorted tables)
    clicked_id = blotter_view[row_idx].get("id")
    if not clicked_id:
        return (no_update,) * 16

    # Find the full order in the store by id
    order = next((o for o in orders if o.get("id") == clicked_id), None)

    # Verify the recalled order matches the clicked row's displayed data
    if order and blotter_view[row_idx].get("underlying") != order.get("underlying"):
        return (no_update,) * 16
    if not order:
        return (no_update,) * 16

    table_data = order.get("_table_data")
    if not table_data:
        return (no_update,) * 16

    current_data = order.get("_current_structure")

    header_style = _HIDDEN
    header_items = []
    broker_style = _HIDDEN
    broker_content = []
    order_input_style = _HIDDEN

    if current_data:
        header_items = [
            html.Span(
                f"{current_data['underlying']} {current_data['structure_name']}",
                style={"color": ACCENT, "fontWeight": WEIGHT_BOLD, "fontSize": FONT_SIZE_XL},
            ),
        ]
        header_style = _HEADER_VISIBLE_STYLE
        order_input_style = _ORDER_INPUT_VISIBLE_STYLE

        broker_px = order.get("_broker_price")
        if broker_px and float(broker_px) > 0:
            quote_side = (order.get("_quote_side") or "bid").upper()
            mid = current_data["mid"]
            edge = float(broker_px) - mid
            edge_color = GREEN_PRIMARY if edge > 0 else RED_PRIMARY
            broker_content = [
                html.Span(
                    f"Broker: {float(broker_px):.2f} {quote_side}",
                    style={"fontSize": FONT_SIZE_LG, "marginRight": "30px", "fontFamily": FONT_MONO},
                ),
                html.Span(
                    f"Screen Mid: {mid:.2f}",
                    style={"fontSize": FONT_SIZE_LG, "marginRight": "30px", "fontFamily": FONT_MONO},
                ),
                html.Span(
                    f"Edge: {edge:+.2f}",
                    style={"fontSize": FONT_SIZE_LG, "color": edge_color, "fontWeight": WEIGHT_BOLD, "fontFamily": FONT_MONO},
                ),
            ]
            broker_style = _BROKER_VISIBLE_STYLE

    return (
        table_data,
        order.get("_underlying"),
        order.get("_structure_type"),
        order.get("_stock_ref"),
        order.get("_delta"),
        order.get("_broker_price"),
        order.get("_quote_side"),
        order.get("_quantity"),
        header_style,
        header_items,
        broker_style,
        broker_content,
        current_data,
        order_input_style,
        True,   # suppress-template
        True,   # auto-price-suppress
    )


def main():
    """Run the dashboard."""
    app.run(host="127.0.0.1", port=8050, debug=True)


if __name__ == "__main__":
    main()
