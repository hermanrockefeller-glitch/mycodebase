"""Dashboard layout components."""

from dash import dcc, html, dash_table


def create_header():
    return html.Div(
        className="header",
        children=[
            html.H1("Options Pricer"),
            html.P("IDB Equity Derivatives Pricing Tool"),
        ],
    )


def create_order_input():
    return html.Div(
        className="order-input",
        children=[
            html.H3("Order Input"),
            dcc.Input(
                id="order-text",
                type="text",
                placeholder='e.g. "BUY 100 AAPL Jan25 150/160 call spread"',
                style={"width": "100%", "padding": "12px", "fontSize": "16px"},
                debounce=True,
            ),
            html.Button(
                "Price",
                id="price-btn",
                n_clicks=0,
                style={
                    "marginTop": "10px",
                    "padding": "10px 30px",
                    "fontSize": "16px",
                    "backgroundColor": "#0d6efd",
                    "color": "white",
                    "border": "none",
                    "borderRadius": "4px",
                    "cursor": "pointer",
                },
            ),
            html.Div(id="parse-error", style={"color": "red", "marginTop": "8px"}),
        ],
    )


def create_structure_summary():
    return html.Div(
        className="structure-summary",
        children=[
            html.H3("Structure Summary"),
            html.Div(id="structure-info"),
        ],
    )


def create_pricing_panel():
    return html.Div(
        className="pricing-panel",
        children=[
            html.H3("Pricing"),
            html.Div(
                id="price-display",
                style={"fontSize": "28px", "fontWeight": "bold", "margin": "10px 0"},
            ),
        ],
    )


def create_greeks_table():
    return html.Div(
        className="greeks-table",
        children=[
            html.H3("Greeks"),
            dash_table.DataTable(
                id="greeks-display",
                columns=[
                    {"name": "Leg", "id": "leg"},
                    {"name": "Strike", "id": "strike"},
                    {"name": "Type", "id": "type"},
                    {"name": "Side", "id": "side"},
                    {"name": "Price", "id": "price"},
                    {"name": "Delta", "id": "delta"},
                    {"name": "Gamma", "id": "gamma"},
                    {"name": "Theta", "id": "theta"},
                    {"name": "Vega", "id": "vega"},
                    {"name": "Rho", "id": "rho"},
                ],
                style_table={"overflowX": "auto"},
                style_cell={"textAlign": "center", "padding": "8px"},
                style_header={
                    "backgroundColor": "#1a1a2e",
                    "color": "white",
                    "fontWeight": "bold",
                },
                style_data={"backgroundColor": "#16213e", "color": "#e0e0e0"},
            ),
        ],
    )


def create_payoff_chart():
    return html.Div(
        className="payoff-chart",
        children=[
            html.H3("Payoff Diagram"),
            dcc.Graph(id="payoff-graph"),
        ],
    )


def create_layout():
    """Build the full dashboard layout."""
    return html.Div(
        style={
            "fontFamily": "'Segoe UI', Tahoma, sans-serif",
            "backgroundColor": "#0f0f23",
            "color": "#e0e0e0",
            "minHeight": "100vh",
            "padding": "20px",
        },
        children=[
            create_header(),
            html.Hr(style={"borderColor": "#333"}),
            html.Div(
                style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "20px"},
                children=[
                    html.Div([create_order_input(), create_structure_summary()]),
                    html.Div([create_pricing_panel(), create_greeks_table()]),
                ],
            ),
            html.Hr(style={"borderColor": "#333"}),
            create_payoff_chart(),
        ],
    )
