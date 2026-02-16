# Options Pricer — Project Context

## What This Is
An options pricing tool for an IDB (inter-dealer broker) equity derivatives broker. Parses real broker shorthand orders, fetches screen market data (Bloomberg or mock), and displays structure-level implied bid/offer/mid on a web dashboard.

The core use case: broker sends an order like `AAPL Jun26 240/220 PS 1X2 vs250 15d 500x @ 3.50 1X over`, user pastes it into the dashboard, and instantly sees screen-implied pricing for the structure to compare against the broker's quote.

## Tech Stack
- **Python 3.12** (venv at `.venv/`, activate with `source .venv/Scripts/activate` on Windows)
- **Dash (Plotly)** — web dashboard
- **NumPy / SciPy** — numerical pricing
- **blpapi 3.25.12** — Bloomberg Terminal API (installed; falls back to mock when Terminal not running)
- **pytest** — 80 tests, all passing

## Project Structure
```
src/options_pricer/
├── models.py            # OptionLeg, OptionStructure, ParsedOrder, LegMarketData, StructureMarketData
├── parser.py            # Flexible IDB broker shorthand parser (regex-based, order-independent tokens)
├── pricer.py            # Black-Scholes pricing engine + Greeks (delta, gamma, theta, vega, rho)
├── structure_pricer.py  # Calculates structure bid/offer/mid from individual leg screen prices
├── bloomberg.py         # BloombergClient (live) + MockBloombergClient (BS-based realistic quotes)
└── dashboard/
    ├── app.py           # Dash web app entry point + callbacks
    └── layouts.py       # UI layout: order input, header bar, pricing table, payoff chart
tests/
├── test_models.py       # 17 tests — payoffs, structures
├── test_parser.py       # 40 tests — extraction helpers + full order parsing for all IDB formats
└── test_pricer.py       # 23 tests — BS pricing, put-call parity, Greeks, structure pricing
```

## Broker Shorthand Format
The parser handles flexible, messy real-world broker shorthand with tokens in any order:

**Stock reference:** `vs250.32`, `vs 250`, `vs. 250`, `tt69.86`, `tt 171.10`, `t 250`
**Delta:** `30d`, `3d`, `on a 11d`
**Quote side:** `20.50 bid`, `2.4b`, `@ 1.60`, `500 @ 2.55`, `5.00 offer`, `3.5o`
**Quantity:** `1058x`, `600x`, `2500x`
**Strike+type:** `45P`, `300C`, `130p`, `240/220`
**Expiry:** `Jun26`, `Jan27`, `Apr` (no year = nearest upcoming)
**Structure types:** `PS` (put spread), `CS` (call spread), `Risky` (risk reversal), `straddle`, `strangle`, `fly` (butterfly), `collar`
**Ratios:** `1X2`, `1x3`
**Modifiers:** `putover`, `put over`, `callover`, `call over`, `1X over`

### Example Orders
```
AAPL jun26 300 calls vs250.32 30d 20.50 bid 1058x
UBER Jun26 45P tt69.86 3d 0.41 bid 1058x
QCOM 85P Jan27 tt141.17 7d 2.4b 600x
VST Apr 130p 500 @ 2.55 tt 171.10 on a 11d
IWM feb 257 apr 280 Risky vs 262.54 52d 2500x @ 1.60
AAPL Jun26 240/220 PS 1X2 vs250 15d 500x @ 3.50 1X over
```

## Dashboard Display
- **Header bar:** Ticker, structure type, tie price, current stock price, delta (+/-)
- **Pricing table:** Leg | Ratio | Bid Size | Bid | Mid | Offer | Offer Size
  - Ratio column: sell = positive (+1), buy = negative (-2)
  - Structure row at bottom with implied bid/offer/mid and sizes
- **Broker quote section:** Shows broker price vs screen mid and edge
- **Payoff diagram:** At-expiry payoff chart

## Key Concepts
- **Tied to (tt/vs):** The stock price at which the option package is quoted. Delta-hedged trades sell/buy stock at this price.
- **Delta-neutral packages:** Quantity × 100 × delta = stock hedge shares
- **Ratio spreads (1X2):** Unequal legs, e.g., sell 1x 240P, buy 2x 220P. "1X over" = 1 extra ratio on the buy side.
- **Putover/callover:** Which leg of a risk reversal is worth more (determines buy/sell direction)
- **Structure bid/offer:** Calculated from screen prices — bid uses worst fills (buy at offer, sell at bid), offer uses best fills

## Key Commands
```bash
source .venv/Scripts/activate          # Windows (Git Bash)
pytest tests/ -v                       # Run all 80 tests
python -m options_pricer.dashboard.app # Launch dashboard at http://127.0.0.1:8050
```

## Current Status & Next Steps
- Parser handles all example formats provided so far — feed more real orders to refine
- Bloomberg API integrated but needs Terminal running for live data; mock works for dev
- Next: delta adjustment for stock tie vs current price in structure pricing
- Next: more structure types as needed (iron condors, diagonals, etc.)
- Next: SPX/index options with combo pricing

## GitHub
- Repo: https://github.com/hermanrockefeller-glitch/mycodebase.git
- Single branch: `main`
- Auth: HTTPS via `gh` credential helper
