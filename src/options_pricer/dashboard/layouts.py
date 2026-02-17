"""Dashboard layout components for IDB options pricer."""

from dash import dcc, html, dash_table

from ..order_store import get_orders_mtime, load_orders, orders_to_display

# ==========================================================================
# THEME SYSTEM — All visual constants in one place
# ==========================================================================

# --- Color Palette ---
# Background layers (dark grey, NOT pure black)
BG_ROOT = "#1a1a24"        # Darkest: root page background
BG_SURFACE = "#22222e"     # Primary surface (panels, toolbars, card backgrounds)
BG_ELEVATED = "#2a2a38"    # Elevated surface (table cells, input fields)
BG_EDITABLE = "#2f3044"    # Editable cells (slightly lighter to signal interactivity)
BG_HOVER = "#353548"       # Hover/active states
BG_STRUCTURE = "#1e2e4a"   # Structure summary row (subtle blue tint)

# Text hierarchy
TEXT_PRIMARY = "#e8e8ec"    # Primary text (high contrast on dark)
TEXT_SECONDARY = "#9898a6"  # Secondary labels, column headers
TEXT_TERTIARY = "#5c5c6e"   # Disabled, hints, placeholder
TEXT_STALE = "#4a4a5c"      # Stale/unavailable data

# Directional colors (colorblind-friendly — differ in luminance for CVD)
GREEN_PRIMARY = "#2ecc71"   # Buy/bid/positive edge
GREEN_MUTED = "#1fa558"     # Subtle positive indicators
RED_PRIMARY = "#e74c3c"     # Sell/offer/negative edge
RED_MUTED = "#c0392b"       # Subtle negative indicators
RED_DESTRUCTIVE = "#a62020" # Destructive actions (clear button)

# Accent
ACCENT = "#4aa3df"          # Interactive elements, links, structure highlights
ACCENT_BRIGHT = "#5bb8f5"   # Hover state for accent
ACCENT_DIM = "#2d7ab8"      # Subtle accent (borders, rules)

# Borders
BORDER_SUBTLE = "#2a2a3a"   # Table cell borders, dividers
BORDER_DEFAULT = "#3a3a4c"  # Input borders, card outlines
BORDER_FOCUS = "#4aa3df"    # Focus rings, active cell

# Status badges
STATUS_LIVE = "#27ae60"     # Bloomberg connected
STATUS_MOCK = "#3498db"     # Mock data
STATUS_ERROR = "#c0392b"    # Connection failed
STATUS_ALERT_BG = "#c0392b"

# --- Typography ---
FONT_BODY = "'Inter', 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif"
FONT_MONO = ("'JetBrains Mono', 'Cascadia Code', 'Fira Code', 'SF Mono', "
             "'Consolas', monospace")

# Size scale (px)
FONT_SIZE_XS = "10px"      # Timestamps, tertiary labels
FONT_SIZE_SM = "11px"      # Status text, hints
FONT_SIZE_BASE = "12px"    # Standard labels, column headers
FONT_SIZE_DATA = "13px"    # Table data cells (monospace)
FONT_SIZE_MD = "14px"      # Toolbar inputs
FONT_SIZE_LG = "16px"      # Broker quote values, key metrics
FONT_SIZE_XL = "18px"      # Structure name in header
FONT_SIZE_H3 = "16px"      # Section headers
FONT_SIZE_H1 = "22px"      # App title

# Font weights
WEIGHT_NORMAL = "400"
WEIGHT_MEDIUM = "500"
WEIGHT_SEMIBOLD = "600"
WEIGHT_BOLD = "700"

# --- Spacing ---
SPACE_XS = "2px"
SPACE_SM = "4px"
SPACE_MD = "8px"
SPACE_LG = "12px"
SPACE_XL = "16px"
SPACE_XXL = "20px"

# Table cell padding (tighter for density)
CELL_PADDING = "5px 8px"          # Standard data cell
CELL_PADDING_HEADER = "6px 8px"   # Column headers
CELL_PADDING_BLOTTER = "6px 10px" # Blotter (slightly wider)

# Border radius
RADIUS_SM = "3px"
RADIUS_MD = "4px"
RADIUS_LG = "6px"

# ==========================================================================
# Derived style dicts
# ==========================================================================

_INPUT_STYLE = {
    "padding": SPACE_MD,
    "backgroundColor": BG_ELEVATED,
    "color": TEXT_PRIMARY,
    "border": f"1px solid {BORDER_DEFAULT}",
    "borderRadius": RADIUS_MD,
    "fontFamily": FONT_MONO,
    "fontSize": FONT_SIZE_MD,
    "outline": "none",
}

_DROPDOWN_STYLE = {
    "width": "110px",
    "backgroundColor": BG_ELEVATED,
    "color": "#000",
    "fontSize": FONT_SIZE_DATA,
}

_LABEL_STYLE = {
    "color": TEXT_SECONDARY,
    "fontSize": FONT_SIZE_BASE,
    "marginBottom": SPACE_SM,
    "fontWeight": WEIGHT_MEDIUM,
    "letterSpacing": "0.3px",
    "textTransform": "uppercase",
}

# Shared button styles
_ACTION_BTN = {
    "padding": f"{SPACE_SM} 12px",
    "fontSize": FONT_SIZE_BASE,
    "backgroundColor": BG_ELEVATED,
    "color": TEXT_SECONDARY,
    "border": f"1px solid {BORDER_DEFAULT}",
    "borderRadius": RADIUS_MD,
    "cursor": "pointer",
    "fontFamily": FONT_MONO,
}

_CLEAR_BTN = {
    **_ACTION_BTN,
    "backgroundColor": RED_DESTRUCTIVE,
    "color": TEXT_PRIMARY,
    "border": f"1px solid {RED_MUTED}",
    "marginLeft": SPACE_LG,
}

# Data source badge styles (shared with app.py toggle callback)
BADGE_STYLE_BASE = {
    "padding": "3px 10px",
    "borderRadius": "10px",
    "fontSize": FONT_SIZE_SM,
    "fontFamily": FONT_MONO,
    "fontWeight": WEIGHT_SEMIBOLD,
    "color": "white",
    "letterSpacing": "0.5px",
}
BADGE_GREEN = {**BADGE_STYLE_BASE, "backgroundColor": STATUS_LIVE}
BADGE_BLUE = {**BADGE_STYLE_BASE, "backgroundColor": STATUS_MOCK}
BADGE_RED = {**BADGE_STYLE_BASE, "backgroundColor": STATUS_ERROR}

ALERT_BANNER_STYLE = {
    "display": "block",
    "backgroundColor": STATUS_ALERT_BG,
    "color": "white",
    "padding": f"{SPACE_MD} {SPACE_XL}",
    "borderRadius": RADIUS_MD,
    "fontSize": FONT_SIZE_DATA,
    "fontFamily": FONT_MONO,
    "marginTop": SPACE_LG,
    "textAlign": "center",
    "fontWeight": WEIGHT_MEDIUM,
}

STRUCTURE_TYPE_OPTIONS = [
    {"label": "Call", "value": "call"},
    {"label": "Put", "value": "put"},
    {"label": "Put Spread", "value": "put_spread"},
    {"label": "Call Spread", "value": "call_spread"},
    {"label": "Risk Reversal", "value": "risk_reversal"},
    {"label": "Straddle", "value": "straddle"},
    {"label": "Strangle", "value": "strangle"},
    {"label": "Butterfly", "value": "butterfly"},
    {"label": "Put Fly", "value": "put_fly"},
    {"label": "Call Fly", "value": "call_fly"},
    {"label": "Iron Butterfly", "value": "iron_butterfly"},
    {"label": "Iron Condor", "value": "iron_condor"},
    {"label": "Put Condor", "value": "put_condor"},
    {"label": "Call Condor", "value": "call_condor"},
    {"label": "Collar", "value": "collar"},
    {"label": "Call Spread Collar", "value": "call_spread_collar"},
    {"label": "Put Spread Collar", "value": "put_spread_collar"},
    {"label": "Put Stupid", "value": "put_stupid"},
    {"label": "Call Stupid", "value": "call_stupid"},
]

# Empty leg row template
_EMPTY_ROW = {
    "leg": "", "expiry": "", "strike": "", "type": "",
    "ratio": 1, "bid_size": "", "bid": "", "mid": "", "offer": "", "offer_size": "",
}


def _make_empty_rows(n: int = 2) -> list[dict]:
    """Create n empty leg rows with Leg labels."""
    return [{**_EMPTY_ROW, "leg": f"Leg {i + 1}"} for i in range(n)]


# ---------------------------------------------------------------------------
# Order Blotter column definitions
# ---------------------------------------------------------------------------

_BLOTTER_COLUMNS = [
    {"name": "ID", "id": "id", "editable": False},
    {"name": "Time", "id": "added_time", "editable": False},
    {"name": "Underlying", "id": "underlying", "editable": False},
    {"name": "Structure", "id": "structure", "editable": False},
    {"name": "Bid", "id": "bid", "editable": False},
    {"name": "Mid", "id": "mid", "editable": False},
    {"name": "Offer", "id": "offer", "editable": False},
    {"name": "Bid Size", "id": "bid_size", "editable": False},
    {"name": "Offer Size", "id": "offer_size", "editable": False},
    {"name": "Bid/Offered", "id": "side", "editable": True, "presentation": "dropdown"},
    {"name": "Size", "id": "size", "editable": True},
    {"name": "Traded", "id": "traded", "editable": True, "presentation": "dropdown"},
    {"name": "Bought/Sold", "id": "bought_sold", "editable": True, "presentation": "dropdown"},
    {"name": "Traded Px", "id": "traded_price", "editable": True},
    {"name": "Initiator", "id": "initiator", "editable": True},
    {"name": "PnL", "id": "pnl", "editable": False},
]

_DEFAULT_VISIBLE = [
    "id", "added_time", "underlying", "structure", "bid", "mid", "offer",
    "side", "size", "traded", "traded_price", "initiator", "pnl",
]

_DEFAULT_HIDDEN = ["bid_size", "offer_size", "bought_sold"]


# ---------------------------------------------------------------------------
# Layout components
# ---------------------------------------------------------------------------

def create_header(initial_source="Mock Data"):
    is_bloomberg = initial_source == "Bloomberg API"
    badge_style = BADGE_GREEN if is_bloomberg else BADGE_BLUE

    return html.Div(
        className="header",
        style={
            "display": "flex",
            "justifyContent": "space-between",
            "alignItems": "center",
        },
        children=[
            html.Div([
                html.H1("IDB Options Pricer",
                         style={"fontSize": FONT_SIZE_H1, "fontWeight": WEIGHT_SEMIBOLD,
                                "margin": "0"}),
                html.P("Equity Derivatives Structure Pricing Tool",
                         style={"color": TEXT_SECONDARY, "fontSize": FONT_SIZE_BASE,
                                "margin": f"{SPACE_SM} 0 0 0"}),
            ]),
            html.Div(
                style={"display": "flex", "alignItems": "center", "gap": "10px"},
                children=[
                    html.Span(
                        initial_source,
                        id="data-source-badge",
                        style=badge_style,
                    ),
                    html.Button(
                        "Switch to Bloomberg" if not is_bloomberg else "Switch to Mock",
                        id="toggle-data-source-btn",
                        n_clicks=0,
                        style={
                            **_ACTION_BTN,
                            "fontSize": FONT_SIZE_SM,
                        },
                    ),
                    html.Div(
                        id="data-source-error",
                        style={
                            "color": RED_PRIMARY,
                            "fontSize": FONT_SIZE_BASE,
                            "fontFamily": FONT_MONO,
                        },
                    ),
                ],
            ),
        ],
    )


def create_order_input():
    return html.Div(
        className="order-input",
        style={"marginBottom": SPACE_XXL},
        children=[
            html.H3("Paste Order",
                     style={"fontSize": FONT_SIZE_H3, "fontWeight": WEIGHT_SEMIBOLD,
                            "margin": f"0 0 {SPACE_MD} 0"}),
            dcc.Textarea(
                id="order-text",
                placeholder='e.g. AAPL Jun26 240/220 PS 1X2 vs250 15d 500x @ 3.50 1X over',
                style={
                    "width": "100%",
                    "boxSizing": "border-box",
                    "padding": "14px",
                    "fontSize": FONT_SIZE_LG,
                    "fontFamily": FONT_MONO,
                    "backgroundColor": BG_ELEVATED,
                    "color": ACCENT,
                    "border": f"1px solid {BORDER_DEFAULT}",
                    "borderRadius": RADIUS_MD,
                    "minHeight": "80px",
                    "resize": "vertical",
                    "lineHeight": "1.5",
                },
            ),
            # Hidden helper to relay Enter keypress from textarea
            dcc.Store(id="textarea-enter", data=0),
            html.Button(
                "Parse & Price",
                id="price-btn",
                n_clicks=0,
                style={
                    "marginTop": "10px",
                    "padding": "10px 30px",
                    "fontSize": FONT_SIZE_LG,
                    "backgroundColor": ACCENT,
                    "color": "white",
                    "border": "none",
                    "borderRadius": RADIUS_MD,
                    "cursor": "pointer",
                    "fontWeight": WEIGHT_SEMIBOLD,
                    "fontFamily": FONT_BODY,
                    "letterSpacing": "0.3px",
                },
            ),
            html.Div(id="parse-error",
                     style={"color": RED_PRIMARY, "marginTop": SPACE_MD,
                            "fontFamily": FONT_MONO, "fontSize": FONT_SIZE_DATA}),
        ],
    )


def create_pricer_toolbar():
    """Compact toolbar row with underlying, structure type, order metadata, and Add Order."""
    toolbar_row = html.Div(
        style={
            "display": "flex",
            "gap": SPACE_LG,
            "alignItems": "flex-end",
            "flexWrap": "wrap",
        },
        children=[
            html.Div([
                html.Div("Underlying", style=_LABEL_STYLE),
                dcc.Input(
                    id="manual-underlying", type="text",
                    placeholder="e.g. AAPL", debounce=True,
                    style={**_INPUT_STYLE, "width": "100px", "textTransform": "uppercase"},
                ),
            ]),
            html.Div([
                html.Div("Structure", style=_LABEL_STYLE),
                dcc.Dropdown(
                    id="manual-structure-type",
                    options=STRUCTURE_TYPE_OPTIONS,
                    placeholder="Select...",
                    style={**_DROPDOWN_STYLE, "width": "160px"},
                ),
            ]),
            html.Div([
                html.Div("Tie", style=_LABEL_STYLE),
                dcc.Input(
                    id="manual-stock-ref", type="number",
                    placeholder="0.00", debounce=True,
                    style={**_INPUT_STYLE, "width": "90px"},
                ),
            ]),
            html.Div([
                html.Div("Delta", style=_LABEL_STYLE),
                dcc.Input(
                    id="manual-delta", type="number",
                    placeholder="0", debounce=True,
                    style={**_INPUT_STYLE, "width": "70px"},
                ),
            ]),
            html.Div([
                html.Div("Order Price", style=_LABEL_STYLE),
                dcc.Input(
                    id="manual-broker-price", type="number",
                    placeholder="0.00", debounce=True,
                    style={**_INPUT_STYLE, "width": "90px"},
                ),
            ]),
            html.Div([
                html.Div("Side", style=_LABEL_STYLE),
                dcc.Dropdown(
                    id="manual-quote-side",
                    options=[
                        {"label": "Bid", "value": "bid"},
                        {"label": "Offer", "value": "offer"},
                    ],
                    value=None,
                    placeholder="Side",
                    style={**_DROPDOWN_STYLE, "width": "90px"},
                ),
            ]),
            html.Div([
                html.Div("Size", style=_LABEL_STYLE),
                dcc.Input(
                    id="manual-quantity", type="number",
                    placeholder="Size", value=None, debounce=True,
                    style={**_INPUT_STYLE, "width": "80px"},
                ),
            ]),
            html.Div([
                html.Div("\u00a0", style=_LABEL_STYLE),
                html.Button(
                    "Add Order",
                    id="add-order-btn",
                    n_clicks=0,
                    style={
                        "padding": f"{SPACE_MD} {SPACE_XXL}",
                        "backgroundColor": STATUS_LIVE,
                        "color": "white",
                        "border": "none",
                        "borderRadius": RADIUS_MD,
                        "cursor": "pointer",
                        "fontSize": FONT_SIZE_DATA,
                        "fontFamily": FONT_MONO,
                        "fontWeight": WEIGHT_SEMIBOLD,
                    },
                ),
            ]),
        ],
    )
    return html.Div(
        style={
            "backgroundColor": BG_SURFACE,
            "padding": f"{SPACE_LG} {SPACE_XXL}",
            "borderRadius": f"{RADIUS_LG} {RADIUS_LG} 0 0",
        },
        children=[
            toolbar_row,
            html.Div(
                id="order-error",
                style={
                    "color": RED_PRIMARY,
                    "fontFamily": FONT_MONO,
                    "fontSize": FONT_SIZE_DATA,
                    "marginTop": SPACE_SM,
                },
            ),
        ],
    )


def create_pricing_table():
    """Unified editable pricing table — input columns + output columns."""
    return html.Div(
        className="pricing-table",
        children=[
            dash_table.DataTable(
                id="pricing-display",
                columns=[
                    {"name": "Leg", "id": "leg", "editable": False},
                    {"name": "Expiry", "id": "expiry", "editable": True},
                    {"name": "Strike", "id": "strike", "editable": True, "type": "numeric"},
                    {"name": "Type", "id": "type", "editable": True, "presentation": "dropdown"},
                    {"name": "Ratio", "id": "ratio", "editable": True, "type": "numeric"},
                    {"name": "Bid Size", "id": "bid_size", "editable": False},
                    {"name": "Bid", "id": "bid", "editable": False},
                    {"name": "Mid", "id": "mid", "editable": False},
                    {"name": "Offer", "id": "offer", "editable": False},
                    {"name": "Offer Size", "id": "offer_size", "editable": False},
                ],
                data=_make_empty_rows(2),
                dropdown={
                    "type": {
                        "options": [
                            {"label": "Call", "value": "C"},
                            {"label": "Put", "value": "P"},
                        ],
                    },
                },
                style_table={"overflowX": "auto"},
                style_cell={
                    "textAlign": "right",
                    "padding": CELL_PADDING,
                    "fontFamily": FONT_MONO,
                    "fontSize": FONT_SIZE_DATA,
                    "fontFeatureSettings": "'tnum' 1, 'lnum' 1",
                    "border": "none",
                },
                style_header={
                    "backgroundColor": BG_SURFACE,
                    "color": TEXT_SECONDARY,
                    "fontWeight": WEIGHT_SEMIBOLD,
                    "fontFamily": FONT_BODY,
                    "fontSize": FONT_SIZE_BASE,
                    "textTransform": "uppercase",
                    "letterSpacing": "0.5px",
                    "borderBottom": f"1px solid {BORDER_DEFAULT}",
                    "padding": CELL_PADDING_HEADER,
                    "textAlign": "right",
                },
                style_data={
                    "backgroundColor": BG_ELEVATED,
                    "color": TEXT_PRIMARY,
                    "borderBottom": f"1px solid {BORDER_SUBTLE}",
                },
                style_cell_conditional=[
                    # Input columns get a slightly lighter background
                    {
                        "if": {"column_id": ["expiry", "strike", "type", "ratio"]},
                        "backgroundColor": BG_EDITABLE,
                    },
                    # Leg column: left-align, fixed width
                    {"if": {"column_id": "leg"}, "width": "65px", "textAlign": "left"},
                    {"if": {"column_id": "expiry"}, "width": "75px", "textAlign": "center"},
                    {"if": {"column_id": "type"}, "width": "55px", "textAlign": "center"},
                    {"if": {"column_id": "ratio"}, "width": "55px", "textAlign": "center"},
                    {"if": {"column_id": "strike"}, "width": "80px"},
                    # Mid column emphasized (slightly larger, bolder)
                    {
                        "if": {"column_id": "mid"},
                        "fontWeight": WEIGHT_BOLD,
                        "fontSize": FONT_SIZE_MD,
                    },
                ],
                style_data_conditional=[
                    # Color-coded pricing columns
                    {"if": {"column_id": "bid"}, "color": GREEN_PRIMARY},
                    {"if": {"column_id": "offer"}, "color": RED_PRIMARY},
                    # Signed ratio: positive (buy) green, negative (sell) red
                    {
                        "if": {
                            "filter_query": "{ratio} > 0",
                            "column_id": "ratio",
                        },
                        "color": GREEN_PRIMARY,
                        "fontWeight": WEIGHT_BOLD,
                    },
                    {
                        "if": {
                            "filter_query": "{ratio} < 0",
                            "column_id": "ratio",
                        },
                        "color": RED_PRIMARY,
                        "fontWeight": WEIGHT_BOLD,
                    },
                    # Structure summary row — HIGHEST VISUAL PRIORITY
                    {
                        "if": {"filter_query": '{leg} = "Structure"'},
                        "backgroundColor": BG_STRUCTURE,
                        "fontWeight": WEIGHT_BOLD,
                        "borderTop": f"2px solid {ACCENT_DIM}",
                        "color": ACCENT,
                        "fontSize": "15px",
                    },
                    # Failed quote indicator (stale/unavailable data)
                    {"if": {"filter_query": '{bid} = "--"', "column_id": "bid"}, "color": TEXT_STALE, "fontStyle": "italic"},
                    {"if": {"filter_query": '{mid} = "--"', "column_id": "mid"}, "color": TEXT_STALE, "fontStyle": "italic"},
                    {"if": {"filter_query": '{offer} = "--"', "column_id": "offer"}, "color": TEXT_STALE, "fontStyle": "italic"},
                    {"if": {"filter_query": '{bid_size} = "--"', "column_id": "bid_size"}, "color": TEXT_STALE, "fontStyle": "italic"},
                    {"if": {"filter_query": '{offer_size} = "--"', "column_id": "offer_size"}, "color": TEXT_STALE, "fontStyle": "italic"},
                ],
            ),
            # Action row below table
            html.Div(
                style={
                    "display": "flex",
                    "gap": "10px",
                    "alignItems": "center",
                    "marginTop": SPACE_MD,
                    "flexWrap": "wrap",
                },
                children=[
                    html.Button("+ Row", id="add-row-btn", n_clicks=0, style=_ACTION_BTN),
                    html.Button("- Row", id="remove-row-btn", n_clicks=0, style=_ACTION_BTN),
                    html.Button(
                        "Flip", id="flip-btn", n_clicks=0,
                        title="Invert all ratios and flip delta",
                        style=_ACTION_BTN,
                    ),
                    html.Button("Clear", id="clear-btn", n_clicks=0, style=_CLEAR_BTN),
                    html.Div(
                        id="table-error",
                        style={"color": RED_PRIMARY, "fontFamily": FONT_MONO, "fontSize": FONT_SIZE_DATA},
                    ),
                ],
            ),
        ],
    )


def create_order_header():
    """Header bar showing parsed order info: ticker, structure, tie, stock, delta."""
    return html.Div(
        id="order-header",
        style={
            "backgroundColor": BG_SURFACE,
            "padding": f"{SPACE_LG} {SPACE_XXL}",
            "borderRadius": RADIUS_LG,
            "marginBottom": "15px",
            "display": "none",
            "borderLeft": f"3px solid {ACCENT}",
        },
        children=[
            html.Div(
                id="order-header-content",
                style={
                    "display": "flex",
                    "gap": "30px",
                    "fontSize": "15px",
                    "fontFamily": FONT_MONO,
                    "flexWrap": "wrap",
                    "alignItems": "baseline",
                },
            ),
        ],
    )


def create_broker_quote():
    """Display broker's quoted price vs screen market."""
    return html.Div(
        id="broker-quote-section",
        style={
            "backgroundColor": BG_SURFACE,
            "padding": f"15px {SPACE_XXL}",
            "borderRadius": RADIUS_LG,
            "marginTop": "15px",
            "display": "none",
        },
        children=[
            html.Div(id="broker-quote-content", style={"fontFamily": FONT_MONO}),
        ],
    )


def create_order_input_section():
    """Hidden stub — preserves IDs that callbacks still output to."""
    return html.Div(
        id="order-input-section",
        style={"display": "none"},
        children=[
            dcc.Dropdown(id="order-side", style={"display": "none"}),
            dcc.Input(id="order-size", type="number", style={"display": "none"}),
        ],
    )


def create_order_blotter(initial_data=None, show_recall_hint=True, resizable=False, selectable=False):
    """Order blotter table — library of all priced structures."""
    visible_cols = [c for c in _BLOTTER_COLUMNS if c["id"] in _DEFAULT_VISIBLE]

    table = dash_table.DataTable(
        id="blotter-table",
        columns=visible_cols,
        data=initial_data or [],
        row_selectable="multi" if selectable else False,
        selected_rows=[],
        dropdown={
            "side": {
                "options": [
                    {"label": "Bid", "value": "Bid"},
                    {"label": "Offered", "value": "Offered"},
                ],
            },
            "traded": {
                "options": [
                    {"label": "Yes", "value": "Yes"},
                    {"label": "No", "value": "No"},
                ],
            },
            "bought_sold": {
                "options": [
                    {"label": "Bought", "value": "Bought"},
                    {"label": "Sold", "value": "Sold"},
                    {"label": "-", "value": ""},
                ],
            },
        },
        sort_action="native",
        sort_by=[{"column_id": "added_time", "direction": "desc"}],
        style_table={"overflowX": "auto", "overflowY": "auto"},
        fixed_rows={"headers": True},
        style_cell={
            "textAlign": "center",
            "padding": CELL_PADDING_BLOTTER,
            "fontFamily": FONT_MONO,
            "fontSize": FONT_SIZE_DATA,
            "fontFeatureSettings": "'tnum' 1, 'lnum' 1",
            "cursor": "pointer",
            "border": "none",
        },
        style_header={
            "backgroundColor": BG_SURFACE,
            "color": TEXT_SECONDARY,
            "fontWeight": WEIGHT_SEMIBOLD,
            "fontFamily": FONT_BODY,
            "fontSize": FONT_SIZE_BASE,
            "textTransform": "uppercase",
            "letterSpacing": "0.5px",
            "borderBottom": f"1px solid {BORDER_DEFAULT}",
            "cursor": "default",
            "padding": CELL_PADDING_HEADER,
        },
        style_data={
            "backgroundColor": BG_ELEVATED,
            "color": TEXT_PRIMARY,
            "borderBottom": f"1px solid {BORDER_SUBTLE}",
        },
        style_cell_conditional=[
            # Editable columns get lighter background
            {
                "if": {"column_id": [
                    "side", "size", "traded", "bought_sold",
                    "traded_price", "initiator",
                ]},
                "backgroundColor": BG_EDITABLE,
            },
            # Right-align numeric columns
            {
                "if": {"column_id": [
                    "bid", "mid", "offer", "bid_size", "offer_size",
                    "traded_price", "pnl", "size",
                ]},
                "textAlign": "right",
            },
            # Mid column emphasized
            {
                "if": {"column_id": "mid"},
                "fontWeight": WEIGHT_BOLD,
            },
            # ID column: compact, left-aligned, smaller font
            {
                "if": {"column_id": "id"},
                "width": "80px",
                "textAlign": "left",
                "fontSize": "11px",
            },
        ],
        style_data_conditional=[
            # Bid/Offered coloring
            {
                "if": {
                    "filter_query": '{side} = "Bid"',
                    "column_id": "side",
                },
                "color": GREEN_PRIMARY,
                "fontWeight": WEIGHT_BOLD,
            },
            {
                "if": {
                    "filter_query": '{side} = "Offered"',
                    "column_id": "side",
                },
                "color": RED_PRIMARY,
                "fontWeight": WEIGHT_BOLD,
            },
            # Bought/Sold coloring
            {
                "if": {
                    "filter_query": '{bought_sold} = "Bought"',
                    "column_id": "bought_sold",
                },
                "color": GREEN_PRIMARY,
                "fontWeight": WEIGHT_BOLD,
            },
            {
                "if": {
                    "filter_query": '{bought_sold} = "Sold"',
                    "column_id": "bought_sold",
                },
                "color": RED_PRIMARY,
                "fontWeight": WEIGHT_BOLD,
            },
            # PnL coloring
            {
                "if": {
                    "filter_query": "{pnl} contains '-'",
                    "column_id": "pnl",
                },
                "color": RED_PRIMARY,
                "fontWeight": WEIGHT_BOLD,
            },
            {
                "if": {
                    "filter_query": "{pnl} contains '+'",
                    "column_id": "pnl",
                },
                "color": GREEN_PRIMARY,
                "fontWeight": WEIGHT_BOLD,
            },
            # Active row highlight
            {
                "if": {"state": "active"},
                "backgroundColor": BG_HOVER,
                "border": f"1px solid {BORDER_FOCUS}",
            },
            # Failed quote indicator (stale/unavailable data)
            {"if": {"filter_query": '{bid} = "--"', "column_id": "bid"}, "color": TEXT_STALE, "fontStyle": "italic"},
            {"if": {"filter_query": '{mid} = "--"', "column_id": "mid"}, "color": TEXT_STALE, "fontStyle": "italic"},
            {"if": {"filter_query": '{offer} = "--"', "column_id": "offer"}, "color": TEXT_STALE, "fontStyle": "italic"},
        ],
    )

    # Wrap table in a resizable container for the Admin Dashboard
    if resizable:
        table_section = html.Div(
            style={
                "resize": "vertical",
                "overflow": "auto",
                "height": "280px",
                "minHeight": "120px",
                "maxHeight": "80vh",
                "border": f"1px solid {BORDER_DEFAULT}",
                "borderRadius": RADIUS_MD,
            },
            children=[table],
        )
    else:
        table_section = table

    # Select all / deselect all control (Admin Dashboard only)
    if selectable:
        select_all_control = dcc.Checklist(
            id="blotter-select-all",
            options=[{"label": " Select all", "value": "all"}],
            value=[],
            style={
                "marginTop": SPACE_MD,
                "fontFamily": FONT_MONO,
                "fontSize": FONT_SIZE_BASE,
                "color": TEXT_SECONDARY,
            },
            inputStyle={"marginRight": "6px"},
        )
    else:
        select_all_control = None

    children = [
        # Title row with column toggle
        html.Div(
            style={
                "display": "flex",
                "alignItems": "center",
                "gap": "10px",
                "marginBottom": "6px",
            },
            children=[
                html.H3("Order Blotter",
                         style={"margin": "0", "fontSize": FONT_SIZE_H3,
                                "fontWeight": WEIGHT_SEMIBOLD}),
                html.Button(
                    "Columns",
                    id="column-toggle-btn",
                    n_clicks=0,
                    title="Show/hide blotter columns",
                    style={**_ACTION_BTN, "fontSize": FONT_SIZE_SM},
                ),
            ],
        ),
        html.P(
            "Click a row to recall into pricer. Edit cells directly to update order status."
            if show_recall_hint
            else "Edit cells directly to update order status. Changes sync across dashboards.",
            style={"color": TEXT_TERTIARY, "fontSize": FONT_SIZE_SM, "margin": "0 0 6px 0"},
        ),
        # Column toggle panel (hidden by default)
        html.Div(
            id="column-toggle-panel",
            style={"display": "none"},
            children=[
                dcc.Checklist(
                    id="column-checklist",
                    options=[
                        {"label": c["name"], "value": c["id"]}
                        for c in _BLOTTER_COLUMNS
                    ],
                    value=_DEFAULT_VISIBLE,
                    style={
                        "display": "flex",
                        "flexWrap": "wrap",
                        "gap": SPACE_MD,
                        "padding": "10px",
                        "backgroundColor": BG_SURFACE,
                        "borderRadius": RADIUS_MD,
                        "fontFamily": FONT_MONO,
                        "fontSize": FONT_SIZE_BASE,
                        "color": TEXT_SECONDARY,
                        "marginBottom": SPACE_MD,
                    },
                    inputStyle={"marginRight": "4px"},
                ),
            ],
        ),
        # Store for visible column IDs
        dcc.Store(id="visible-columns", data=_DEFAULT_VISIBLE),
        # The blotter DataTable
        table_section,
    ]

    if select_all_control is not None:
        children.append(select_all_control)

    return html.Div(
        className="order-blotter",
        style={"marginTop": SPACE_XXL},
        children=children,
    )


def create_layout(data_source="Mock Data"):
    """Build the full dashboard layout.

    Called by Dash on each page load (app.layout = create_layout) so that
    persisted orders are loaded from JSON on refresh.
    """
    # Load persisted orders from JSON
    orders = load_orders()
    current_mtime = get_orders_mtime()
    blotter_data = orders_to_display(orders)

    return html.Div(
        style={
            "fontFamily": FONT_BODY,
            "backgroundColor": BG_ROOT,
            "color": TEXT_PRIMARY,
            "minHeight": "100vh",
            "padding": f"{SPACE_XXL} {SPACE_XXL} 80px {SPACE_XXL}",
            "maxWidth": "1400px",
            "margin": "0 auto",
            "boxSizing": "border-box",
            "lineHeight": "1.4",
        },
        children=[
            # Session data stores
            dcc.Store(id="current-structure", data=None),
            dcc.Store(id="order-store", data=orders),
            dcc.Store(id="suppress-template", data=False),
            dcc.Store(id="auto-price-suppress", data=False),
            dcc.Store(id="blotter-edit-suppress", data=False),
            # Polling infrastructure for cross-dashboard sync
            dcc.Interval(id="poll-interval", interval=2000, n_intervals=0),
            dcc.Store(id="file-mtime", data=current_mtime),
            dcc.Store(id="last-write-time", data=current_mtime),
            # Live price refresh (1-second cadence)
            dcc.Interval(id="live-refresh-interval", interval=1000, n_intervals=0),
            # Data source tracking
            dcc.Store(id="data-source", data=data_source),
            dcc.Store(id="bloomberg-health", data="ok"),
            create_header(initial_source=data_source),
            html.Div(id="bloomberg-health-alert", style={"display": "none"}),
            html.Hr(style={"borderColor": BORDER_DEFAULT}),
            create_order_input(),
            # Toolbar + table grouped as one card
            html.Div(
                style={
                    "backgroundColor": BG_ELEVATED,
                    "borderRadius": RADIUS_LG,
                    "border": f"1px solid {BORDER_DEFAULT}",
                    "overflow": "visible",
                },
                children=[
                    create_pricer_toolbar(),
                    create_pricing_table(),
                ],
            ),
            create_order_header(),
            create_broker_quote(),
            create_order_input_section(),
            html.Hr(style={"borderColor": BORDER_DEFAULT, "marginTop": SPACE_XXL}),
            create_order_blotter(initial_data=blotter_data),
        ],
    )


def create_blotter_layout():
    """Build a blotter-only layout for the standalone blotter dashboard.

    Shows only the order blotter with editable cells, column toggle,
    and polling infrastructure for cross-dashboard sync. No pricer,
    no parser, no recall.
    """
    orders = load_orders()
    current_mtime = get_orders_mtime()
    blotter_data = orders_to_display(orders)

    return html.Div(
        style={
            "fontFamily": FONT_BODY,
            "backgroundColor": BG_ROOT,
            "color": TEXT_PRIMARY,
            "minHeight": "100vh",
            "padding": f"{SPACE_XXL} {SPACE_XXL} 80px {SPACE_XXL}",
            "maxWidth": "1400px",
            "margin": "0 auto",
            "boxSizing": "border-box",
            "lineHeight": "1.4",
        },
        children=[
            # Session data stores
            dcc.Store(id="order-store", data=orders),
            dcc.Store(id="blotter-edit-suppress", data=False),
            # Polling infrastructure for cross-dashboard sync
            dcc.Interval(id="poll-interval", interval=2000, n_intervals=0),
            dcc.Store(id="file-mtime", data=current_mtime),
            dcc.Store(id="last-write-time", data=current_mtime),
            # Header
            html.Div(children=[
                html.H1("Admin Dashboard",
                         style={"margin": "0", "fontSize": FONT_SIZE_H1,
                                "fontWeight": WEIGHT_SEMIBOLD}),
                html.P(
                    "Order blotter \u2014 edits sync with the pricer dashboard",
                    style={"color": TEXT_TERTIARY, "fontSize": FONT_SIZE_BASE,
                           "margin": f"{SPACE_SM} 0 0 0"},
                ),
            ]),
            html.Hr(style={"borderColor": BORDER_DEFAULT}),
            # Blotter
            create_order_blotter(initial_data=blotter_data, show_recall_hint=False, resizable=True, selectable=True),
        ],
    )
