"""Dash web app entry point for the options pricer dashboard."""

from datetime import date

import plotly.graph_objects as go
from dash import Dash, Input, Output, State, callback, no_update

from ..bloomberg import MockBloombergClient, create_client
from ..models import OptionStructure
from ..parser import parse_order
from ..pricer import greeks, price_structure
from .layouts import create_layout

app = Dash(__name__)
app.title = "Options Pricer"
app.layout = create_layout()

# Use mock client (falls back automatically if Bloomberg is unavailable)
_client = create_client(use_mock=True)


def _time_to_expiry(expiry: date) -> float:
    """Calculate time to expiry in years from today."""
    delta = expiry - date.today()
    return max(delta.days / 365.0, 0.001)


@callback(
    Output("parse-error", "children"),
    Output("structure-info", "children"),
    Output("price-display", "children"),
    Output("greeks-display", "data"),
    Output("payoff-graph", "figure"),
    Input("price-btn", "n_clicks"),
    State("order-text", "value"),
    prevent_initial_call=True,
)
def price_order(n_clicks, order_text):
    if not order_text:
        return "Please enter an order.", "", "", [], go.Figure()

    # Parse the order
    try:
        structure = parse_order(order_text)
    except ValueError as e:
        return str(e), "", "", [], go.Figure()

    underlying = next(iter(structure.underlyings))
    spot = _client.get_spot(underlying)
    rate = _client.get_risk_free_rate()

    # Get vol for each leg
    expiry = structure.legs[0].expiry
    T = _time_to_expiry(expiry)
    vol_map = {}
    for leg in structure.legs:
        vol = _client.get_implied_vol(underlying, leg.expiry, leg.strike)
        vol_map[leg.strike] = vol

    # Price the structure
    result = price_structure(structure, spot, rate, vol_map, T)

    # Structure info
    info = [
        f"Structure: {structure.name.upper()}",
        f" | Underlying: {underlying} @ ${spot:.2f}",
        f" | Expiry: {expiry} ({T:.2f}y)",
        f" | Legs: {len(structure.legs)}",
    ]
    structure_text = "".join(info)

    # Price display
    price_text = f"Net Price: ${result.total_price:.4f}"

    # Greeks table data
    table_data = []
    for i, (leg, lp) in enumerate(zip(structure.legs, result.leg_prices)):
        table_data.append({
            "leg": f"Leg {i + 1}",
            "strike": f"${leg.strike:.0f}",
            "type": leg.option_type.value.upper(),
            "side": leg.side.value.upper(),
            "price": f"${lp.price:.4f}",
            "delta": f"{lp.delta:.4f}",
            "gamma": f"{lp.gamma:.4f}",
            "theta": f"{lp.theta:.4f}",
            "vega": f"{lp.vega:.4f}",
            "rho": f"{lp.rho:.4f}",
        })
    # Totals row
    table_data.append({
        "leg": "TOTAL",
        "strike": "",
        "type": "",
        "side": "",
        "price": f"${result.total_price:.4f}",
        "delta": f"{result.total_delta:.4f}",
        "gamma": f"{result.total_gamma:.4f}",
        "theta": f"{result.total_theta:.4f}",
        "vega": f"{result.total_vega:.4f}",
        "rho": f"{result.total_rho:.4f}",
    })

    # Payoff diagram
    strikes = [leg.strike for leg in structure.legs]
    center = sum(strikes) / len(strikes)
    spread = max(strikes) - min(strikes) if len(strikes) > 1 else center * 0.1
    margin = max(spread * 2, center * 0.15)
    low = center - margin
    high = center + margin

    payoff_points = structure.payoff_range(low, high, steps=300)
    spots = [p[0] for p in payoff_points]
    payoffs = [p[1] for p in payoff_points]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=spots, y=payoffs,
        mode="lines",
        name="Payoff at Expiry",
        line=dict(color="#00d4ff", width=2),
    ))
    fig.add_hline(y=0, line_dash="dash", line_color="gray")
    fig.add_vline(x=spot, line_dash="dot", line_color="yellow",
                  annotation_text=f"Spot: ${spot:.2f}")
    for s in strikes:
        fig.add_vline(x=s, line_dash="dot", line_color="rgba(255,255,255,0.3)")

    fig.update_layout(
        template="plotly_dark",
        title=f"Payoff Diagram — {structure.description}",
        xaxis_title="Underlying Price",
        yaxis_title="P&L per unit",
        height=450,
        margin=dict(l=50, r=30, t=50, b=50),
    )

    return "", structure_text, price_text, table_data, fig


def main():
    """Run the dashboard."""
    app.run(host="127.0.0.1", port=8050, debug=True)


if __name__ == "__main__":
    main()
