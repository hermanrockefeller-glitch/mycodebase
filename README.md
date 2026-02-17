# IDB Equity Derivatives Pricing Tool

A web-based options pricing dashboard built for inter-dealer broker (IDB) workflow. Paste a broker's shorthand order, get instant screen-implied pricing to compare against the broker's quote.

## What It Does

- **Order Parser** — Handles messy real-world IDB broker shorthand (e.g. `AAPL Jun26 240/220 PS 1X2 vs250 15d 500x @ 3.50 1X over`). Extracts ticker, expiries, strikes, structure type, stock reference, delta, quantity, and quote side from tokens in any order.
- **Pricing Engine** — Black-Scholes pricing with full Greeks (delta, gamma, theta, vega, rho). Calculates structure-level implied bid/offer/mid from individual leg screen prices. Bloomberg API integration for live market data (falls back to mock BS-based quotes when Terminal isn't running).
- **Web Dashboard** — Paste order → auto-parses and prices → editable pricing table (change strikes/expiries/legs and it auto-reprices) → header bar with ticker/structure/tie/delta → broker quote comparison showing edge.
- **Order Blotter** — Persistent library of all priced structures. 15 columns (6 editable: side, size, traded status, bought/sold, traded price, initiator). Column show/hide toggle. Click any row to recall it back into the pricer. PnL auto-calculates for traded orders. Data persists to JSON for cross-dashboard sharing.
- **Pricer Toolbar** — Dual-purpose: configures pricing parameters AND submits to order blotter. Underlying, structure type, tie, delta, order price, side, qty, and "Add Order" all in one row.

## Supported Order Formats

```
AAPL jun26 300 calls vs250.32 30d 20.50 bid 1058x
UBER Jun26 45P tt69.86 3d 0.41 bid 1058x
QCOM 85P Jan27 tt141.17 7d 2.4b 600x
VST Apr 130p 500 @ 2.55 tt 171.10 on a 11d
IWM feb 257 apr 280 Risky vs 262.54 52d 2500x @ 1.60
AAPL Jun26 240/220 PS 1X2 vs250 15d 500x @ 3.50 1X over
goog jun 100 90 ps vs 200.00 10d 1 bid 1k
```

Structure types: put spreads, call spreads, risk reversals, straddles, strangles, butterflies, iron condors, collars. Ratios (1x2, 1x3) and modifiers (putover, callover, 1X over) supported.

## Tech Stack

- **Python 3.12**
- **Dash (Plotly)** — web dashboard
- **NumPy / SciPy** — numerical pricing
- **blpapi** — Bloomberg Terminal API (falls back to mock when Terminal not running)
- **pytest** — 100 tests

## Project Structure

```
src/options_pricer/
├── parser.py            # Regex-based broker shorthand parser
├── pricer.py            # Black-Scholes engine + Greeks
├── structure_pricer.py  # Structure bid/offer/mid from leg prices
├── bloomberg.py         # Live Bloomberg + mock client
├── order_store.py       # JSON persistence (atomic writes)
├── models.py            # Data classes (legs, structures, orders)
└── dashboard/
    ├── app.py           # Dash callbacks (~900 lines)
    └── layouts.py       # UI components (~700 lines)
tests/
├── test_models.py       # 17 tests — payoffs, structures
├── test_parser.py       # 43 tests — parser extraction + full orders
├── test_order_store.py  # 11 tests — JSON persistence
└── test_pricer.py       # 23 tests — BS pricing, Greeks, structures
```

## Getting Started

```bash
git clone https://github.com/hermanrockefeller-glitch/mycodebase.git
cd mycodebase
python -m venv .venv
source .venv/Scripts/activate   # Windows (Git Bash)
# source .venv/bin/activate     # Mac/Linux
pip install -e .
python -m options_pricer.dashboard.app   # http://127.0.0.1:8050
pytest tests/ -v                         # 94 tests
```

## Key Concepts

- **Tied to (tt/vs):** The stock price at which the option package is quoted. Delta-hedged trades sell/buy stock at this price.
- **Delta-neutral packages:** Quantity x 100 x delta = stock hedge shares.
- **Ratio spreads (1X2):** Unequal legs, e.g., sell 1x 240P, buy 2x 220P. "1X over" = 1 extra ratio on the buy side.
- **Putover/callover:** Which leg of a risk reversal is worth more (determines buy/sell direction).
- **Structure bid/offer:** Calculated from screen prices — bid uses worst fills (buy at offer, sell at bid), offer uses best fills.
