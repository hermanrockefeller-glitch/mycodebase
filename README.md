# IDB Equity Derivatives Pricing Tool

A web-based options pricing dashboard built for inter-dealer broker (IDB) workflow. Paste a broker's shorthand order, get instant screen-implied pricing to compare against the broker's quote.

## What It Does

- **Order Parser** — Handles messy real-world IDB broker shorthand (e.g. `AAPL Jun26 240/220 PS 1X2 vs250 15d 500x @ 3.50 1X over`). Extracts ticker, expiries, strikes, structure type, stock reference, delta, quantity, and quote side from tokens in any order.
- **Pricing Engine** — Black-Scholes pricing with full Greeks (delta, gamma, theta, vega, rho). Calculates structure-level implied bid/offer/mid from individual leg screen prices. Bloomberg API integration for live market data (falls back to mock BS-based quotes when Terminal isn't running).
- **Web Dashboard** — Paste order → auto-parses and prices → editable AG Grid pricing table (change strikes/expiries/legs and it auto-reprices) → header bar with ticker/structure/tie/delta → broker quote comparison showing edge.
- **Order Blotter** — Persistent library of all priced structures. 16 columns (6 editable: side, size, traded status, bought/sold, traded price, initiator). Column show/hide toggle. Click any row to recall it back into the pricer. PnL auto-calculates for traded orders. Live price updates via WebSocket. Data persists to JSON.
- **Blotter-Only View** — `http://localhost:5173/blotter` for a standalone blotter without the pricer. Same WebSocket sync, same editable cells. Header links between the two views.

## Supported Order Formats

```
AAPL jun26 300 calls vs250.32 30d 20.50 bid 1058x
UBER Jun26 45P tt69.86 3d 0.41 bid 1058x
QCOM 85P Jan27 tt141.17 7d 2.4b 600x
VST Apr 130p 500 @ 2.55 tt 171.10 on a 11d
IWM feb 257 apr 280 Risky vs 262.54 52d 2500x @ 1.60
AAPL Jun26 240/220 PS 1X2 vs250 15d 500x @ 3.50 1X over
AAPL Jun26 220/230/240 PF vs250 30dp 500x
SPX Jun26 4000/4050/4100 IF vs4050 5d 100x
SPX Jun26 3900/3950/4100/4150 IC vs4050 5d 100x
```

Structure types: put spreads, call spreads, risk reversals, straddles, strangles, butterflies (fly/PF/CF), iron butterflies (IF/IBF), iron condors (IC), put/call condors (PC/CC), collars, spread collars (CSC/PSC). Ratios (1x2, 1x3, 1x1.5x1) and modifiers (putover, callover, 1X over) supported.

## Tech Stack

- **Python 3.12** — business logic and API backend
- **FastAPI + Uvicorn** — REST API + WebSocket server
- **React 18 + TypeScript + Vite** — frontend SPA
- **AG Grid Community** — data grids (column resize, cell flash, streaming updates)
- **Zustand** — React state management
- **NumPy / SciPy** — numerical pricing
- **blpapi** — Bloomberg Terminal API (falls back to mock when Terminal not running)
- **pytest** — 135 tests

## Project Structure

```
src/
  options_pricer/             # Python business logic
    models.py                 # Data classes (legs, structures, orders)
    parser.py                 # Regex-based broker shorthand parser
    pricer.py                 # Black-Scholes engine + Greeks
    structure_pricer.py       # Structure bid/offer/mid from leg prices
    bloomberg.py              # Live Bloomberg + mock client
    order_store.py            # JSON persistence + cross-process file locking
  api/                        # FastAPI backend
    main.py                   # FastAPI app, CORS, lifespan
    schemas.py                # Pydantic request/response models
    dependencies.py           # Bloomberg client singleton, WebSocket manager
    ws.py                     # WebSocket endpoint + background price broadcaster
    routes/
      parse.py                # POST /api/parse
      price.py                # POST /api/price
      orders.py               # GET/POST/PUT/DELETE /api/orders
      source.py               # POST /api/toggle-source, GET /api/health
frontend/                     # React + Vite + TypeScript
  src/
    App.tsx                   # Main app with pricer + blotter views
    api/
      client.ts               # REST fetch wrappers
      ws.ts                   # WebSocket client (auto-reconnect, multiplexing)
    stores/
      pricerStore.ts           # Zustand: parsed order, table data, header
      blotterStore.ts          # Zustand: orders, column visibility, selection
      connectionStore.ts       # Zustand: WS status, bloomberg health
    components/
      Pricer/                  # OrderInput, PricerToolbar, PricingGrid, etc.
      Blotter/                 # BlotterGrid, ColumnToggle
      Shared/                  # HealthBadge, AlertBanner
tests/
  test_models.py              # 17 tests
  test_parser.py              # 68 tests
  test_order_store.py         # 17 tests
  test_pricer.py              # 25 tests
```

## Getting Started

```bash
git clone https://github.com/hermanrockefeller-glitch/mycodebase.git
cd mycodebase

# Python backend
python -m venv .venv
source .venv/Scripts/activate   # Windows (Git Bash)
# source .venv/bin/activate     # Mac/Linux
pip install -e .

# Frontend
cd frontend && npm install && cd ..

# Run (two terminals)
uvicorn api.main:app --reload --port 8000           # Terminal 1: API backend
cd frontend && npm run dev                           # Terminal 2: React dev server

# Open http://localhost:5173 (pricer + blotter)
# Open http://localhost:5173/blotter (blotter only)

# Tests
pytest tests/ -v                                     # 135 tests
```

## Architecture

Single FastAPI server handles REST API + WebSocket on port 8000. React SPA served by Vite dev server on port 5173 (proxies `/api` to FastAPI).

- **Background asyncio task** reprices all blotter orders every 1s, broadcasts via WebSocket
- **WebSocket channels:** `blotter_prices` (1s updates), `health` (Bloomberg status), `order_sync` (cross-tab sync), `stock_price` (live ticker)
- **Cross-tab sync:** Order mutations broadcast via WebSocket to all connected clients
- `orders.json` (~/.options_pricer/) is the persistent source of truth

## Key Concepts

- **Tied to (tt/vs):** The stock price at which the option package is quoted. Delta-hedged trades sell/buy stock at this price.
- **Delta-neutral packages:** Quantity x 100 x delta = stock hedge shares.
- **Ratio spreads (1X2):** Unequal legs, e.g., sell 1x 240P, buy 2x 220P. "1X over" = 1 extra ratio on the buy side.
- **Putover/callover:** Which leg of a risk reversal is worth more (determines buy/sell direction).
- **Structure bid/offer:** Calculated from screen prices — bid uses worst fills (buy at offer, sell at bid), offer uses best fills.
