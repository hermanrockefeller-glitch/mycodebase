# Options Pricer — Project Context

## What This Is
An options pricing tool for an IDB (inter-dealer broker) equity derivatives broker. Parses real broker shorthand orders, fetches screen market data (Bloomberg or mock), and displays structure-level implied bid/offer/mid on a web dashboard.

The core use case: broker sends an order like `AAPL Jun26 240/220 PS 1X2 vs250 15d 500x @ 3.50 1X over`, user pastes it into the dashboard, and instantly sees screen-implied pricing for the structure to compare against the broker's quote.

## Tech Stack
- **Python 3.12** (venv at `.venv/`, activate with `source .venv/Scripts/activate` on Windows)
- **FastAPI + Uvicorn** — API backend (replaces Dash)
- **React 18 + TypeScript + Vite** — frontend SPA
- **AG Grid Community** — data grid (column resize, cell flash, streaming updates)
- **Zustand** — React state management
- **NumPy / SciPy** — numerical pricing
- **blpapi 3.25.12** — Bloomberg Terminal API (installed; falls back to mock when Terminal not running)
- **pytest** — 144 tests, all passing

## Project Structure
```
src/
  options_pricer/           # Python business logic (UNCHANGED)
    models.py               # OptionLeg, OptionStructure, ParsedOrder, LegMarketData, StructureMarketData
    parser.py               # Flexible IDB broker shorthand parser (regex-based, order-independent tokens)
    pricer.py               # Black-Scholes pricing engine + Greeks (delta, gamma, theta, vega, rho)
    structure_pricer.py     # Calculates structure bid/offer/mid from individual leg screen prices
    bloomberg.py            # BloombergClient (live) + MockBloombergClient (BS-based realistic quotes)
    order_store.py          # Per-day JSON persistence (~/.options_pricer/orders/YYYY-MM-DD.json) + cross-process file locking
  api/                      # FastAPI backend
    main.py                 # FastAPI app, CORS, lifespan, background price broadcaster
    schemas.py              # Pydantic request/response models
    dependencies.py         # Bloomberg client singleton, WebSocket ConnectionManager
    ws.py                   # WebSocket endpoint + background price broadcast loop
    routes/
      parse.py              # POST /api/parse
      price.py              # POST /api/price
      orders.py             # GET/POST/PUT/DELETE /api/orders
      source.py             # POST /api/toggle-source, GET /api/health
frontend/                   # React + Vite + TypeScript
  src/
    main.tsx, App.tsx
    api/
      client.ts             # REST fetch wrappers
      ws.ts                 # WebSocket client (auto-reconnect, channel multiplexing)
    stores/
      pricerStore.ts        # Zustand: parsed order, table data, header, broker quote
      blotterStore.ts       # Zustand: orders, column visibility, selection (persisted)
      connectionStore.ts    # Zustand: WS status, bloomberg health, data source
    components/
      Layout/               # AppShell, Header
      Pricer/               # OrderInput, PricerToolbar, PricingGrid, StructureBuilder,
                            # OrderHeader, BrokerQuote, AddOrderButton
      Blotter/              # BlotterGrid, ColumnToggle
      Shared/               # HealthBadge, AlertBanner
    hooks/
      useWebSocket.ts       # Routes WS messages to stores
    types/index.ts          # TS interfaces matching API schemas
    theme/
      tokens.ts             # Colors, fonts, spacing from design system
      aggrid.ts             # AG Grid dark theme CSS overrides
tests/
  test_models.py            # 17 tests — payoffs, structures
  test_parser.py            # 68 tests — extraction helpers + full order parsing for all IDB formats
  test_order_store.py       # 26 tests — JSON persistence, file locking, per-day storage, migration, mtime helpers
  test_pricer.py            # 25 tests — BS pricing, put-call parity, Greeks, structure pricing
```

## Broker Shorthand Format
The parser handles flexible, messy real-world broker shorthand with tokens in any order:

**Stock reference:** `vs250.32`, `vs 250`, `vs. 250`, `tt69.86`, `tt 171.10`, `t 250`
**Delta:** `30d`, `3d`, `on a 11d`
**Quote side:** `20.50 bid`, `2.4b`, `@ 1.60`, `500 @ 2.55`, `5.00 offer`, `3.5o`
**Quantity:** `1058x`, `600x`, `2500x`, `1k` (= 1000), `2k` (= 2000)
**Strike+type:** `45P`, `300C`, `130p`, `240/220`
**Expiry:** `Jun26`, `Jan27`, `Apr` (no year = nearest upcoming)
**Delta direction:** `30dp` (put delta = -30), `20dc` (call delta = +20)
**Structure types:** `PS` (put spread), `CS` (call spread), `Risky` (risk reversal), `straddle`, `strangle`, `fly` (butterfly), `PF` (put fly), `CF` (call fly), `IF`/`IBF` (iron butterfly), `IC` (iron condor), `PC` (put condor), `CC` (call condor), `collar`, `CSC` (call spread collar), `PSC` (put spread collar)
**Ratios:** `1X2`, `1x3`, `1x1.5x1`, `1x2x1` (3-part for butterfly-type structures)
**Modifiers:** `putover`, `put over`, `callover`, `call over`, `1X over`

### Example Orders
```
AAPL jun26 300 calls vs250.32 30d 20.50 bid 1058x
UBER Jun26 45P tt69.86 3d 0.41 bid 1058x
QCOM 85P Jan27 tt141.17 7d 2.4b 600x
VST Apr 130p 500 @ 2.55 tt 171.10 on a 11d
IWM feb 257 apr 280 Risky vs 262.54 52d 2500x @ 1.60
AAPL Jun26 240/220 PS 1X2 vs250 15d 500x @ 3.50 1X over
AAPL Jun26 220/230/240 PF vs250 30dp 500x
AAPL Jun26 280/290/300 CF vs250 20dc 500x
SPX Jun26 4000/4050/4100 IF vs4050 5d 100x
AAPL Jun26 220/230/240 fly 1x1.5x1 vs250 10d 500x
SPX Jun26 3900/3950/4100/4150 IC vs4050 5d 100x
AAPL Jun26 200/210/220/230 PC vs250 10dp 500x
AAPL Jun26 220/250/260 CSC vs250 20d 500x
```

## Dashboard Display
- **Paste Order:** Textarea for broker shorthand input. Enter key triggers parse & price.
- **Pricer Toolbar:** Underlying | Structure | Tie | Delta | Order Price | Side | Qty — shown after first price. Changes trigger auto-reprice.
- **Header bar:** Ticker, structure type, tie price, current stock price, delta (+/-)
- **Pricing table:** AG Grid — Leg | Expiry | Strike | Type | Ratio | Bid Size | Bid | Mid | Offer | Offer Size. Editable cells (expiry, strike, type, ratio) trigger auto-reprice via `onCellValueChanged`. Structure summary as pinned bottom row (blue-tinted).
- **Structure Builder:** +Row, -Row, Flip, Clear buttons above the pricing grid (always visible).
- **Broker quote section:** Shows broker price vs screen mid and edge (color-coded green/red).
- **Add Order:** Creates a blotter order from the current priced structure.
- **Order Blotter:** AG Grid with 16 columns (6 editable with dropdowns: side, size, traded, bought/sold, traded price, initiator). Column toggle via "Columns" button. Sortable. Click row to recall into pricer. PnL auto-calcs for traded orders. Cell flash on price updates. Per-day persistence to `~/.options_pricer/orders/YYYY-MM-DD.json`. Timestamps are local ISO 8601 (`YYYY-MM-DDTHH:MM:SS`), displayed as `HH:MM:SS` in the Time column.
- **Health indicator:** Green/red badge for Bloomberg status, WS connection dot (green=live, gray=reconnecting).
- **Blotter-only view:** `http://localhost:5173/blotter` — standalone blotter without the pricer (replaces old `blotter_app.py` on port 8051). Same WebSocket sync, same editable cells. Header links between the two views.

## Real-Time Architecture
- **Single FastAPI server** handles REST API + WebSocket on port 8000
- **Background asyncio task** reprices all blotter orders every 1s, broadcasts via WebSocket
- **WebSocket channels:** `blotter_prices` (1s price updates), `health` (Bloomberg status), `order_sync` (cross-tab sync), `stock_price` (live ticker)
- **Cross-tab sync:** Order mutations broadcast via WS to all connected clients (replaces file polling)
- **AG Grid `onCellValueChanged`** fires only on user edits — no suppress flags needed (unlike Dash DataTable)
- **AG Grid `applyTransactionAsync`** for streaming price updates without disrupting edit state
- Per-day `orders/YYYY-MM-DD.json` files are the source of truth for persistence (one-time migration from legacy `orders.json`)

## Key Concepts
- **Tied to (tt/vs):** The stock price at which the option package is quoted. Delta-hedged trades sell/buy stock at this price.
- **Delta-neutral packages:** Quantity × 100 × delta = stock hedge shares
- **Ratio spreads (1X2):** Unequal legs, e.g., sell 1x 240P, buy 2x 220P. "1X over" = 1 extra ratio on the buy side.
- **Putover/callover:** Which leg of a risk reversal is worth more (determines buy/sell direction)
- **Iron butterfly:** Sell ATM straddle + buy OTM wings (3 strikes → 4 legs). Aliases: `IF`, `IBF`, `iron fly`
- **Put fly / Call fly:** 3-leg butterfly using all puts or all calls. Aliases: `PF`, `CF`, `putfly`, `callfly`
- **3-part ratios (1x1.5x1):** Custom ratios for butterfly-type structures. Middle leg ratio doesn't have to be 2x
- **Condors (IC/PC/CC):** 4-leg, 4-strike structures. Iron condor mixes puts+calls; put/call condor uses single type
- **Spread collars (CSC/PSC):** 3-leg collar variants. CSC = buy put + sell call spread. PSC = buy put spread + sell call
- **Structure bid/offer:** Calculated from screen prices — bid uses worst fills (buy at offer, sell at bid), offer uses best fills
- **Structure bid <= offer guaranteed:** `structure_pricer.py` guarantees `struct_bid <= struct_offer` by construction (BUY legs widen toward offer, SELL legs widen toward bid). **Never use `abs()` or `min/max` to normalize structure prices** — it destroys sign information (negative = debit/crossed market) and can swap bid/offer when both values are negative.

## Key Commands
```bash
source .venv/Scripts/activate                      # Windows (Git Bash)
pytest tests/ -v                                   # Run all 135 tests
uvicorn api.main:app --reload --port 8000          # FastAPI backend
cd frontend && npm run dev                         # React dev server at http://localhost:5173
cd frontend && npm run build                       # Production build
```

## UI Rules
- **Theme tokens:** All colors, fonts, spacing in `frontend/src/theme/tokens.ts`. AG Grid overrides in `frontend/src/theme/aggrid.ts`.
- **No content cutoff:** Never use `overflow: hidden` on containers with interactive content.
- **AG Grid autoHeight:** PricingGrid uses `domLayout="autoHeight"` — never set an explicit `height` on its container div (conflicts with autoHeight and breaks sibling layout).
- **Button visibility:** Grid action buttons (+Row, -Row, Flip, Clear, Add Order) must be rendered ABOVE the grid, not below. Components that appear conditionally after pricing (OrderHeader, BrokerQuote, PricerToolbar) push content down — buttons below the grid can be pushed off-screen.
- **Max width:** Main layout uses `maxWidth: 1600px`.
- **Consistent sizing:** Monospace font at 13px for data cells, 16px for inputs.
- **AG Grid column resize:** Built-in via `resizable: true` in defaultColDef.
- **Test visually:** After any layout change, confirm in the browser at `http://localhost:5173`.

## Auto-Recalculation Rules
- AG Grid's `onCellValueChanged` fires only on user edits (not programmatic updates) — no suppress flags needed.
- Streaming price updates via WebSocket use Zustand store updates — AG Grid re-renders only affected cells.
- **Blotter editable fields** (side, size, traded, bought_sold, traded_price, initiator) must never be overwritten by price updates.
- Any change to a pricing input triggers automatic recalculation: table edits (expiry, strike, type, ratio) and toolbar fields (underlying, tie, delta, broker price, side, quantity).

## Bloomberg Failure Visibility (MUST follow for all pricing displays)
Bloomberg failures must ALWAYS be surfaced visibly to the user. Never silently show zero prices or fallback values.

- **Connection-level**: When Bloomberg is selected but `get_spot()` returns `None`, show RED badge + alert banner at top of dashboard. Badge auto-reverts to green when Bloomberg recovers.
- **Cell-level**: When a quote returns `bid=0 AND offer=0`, display `--` not `0.00`. Zero is never a valid displayed price — a real zero-bid option still has an offer.
- **Structure-level**: If ANY leg has a failed quote, the structure summary row must also show `--`. Don't compute a structure price from partially invalid data.
- **Blotter propagation**: Same `--` formatting applies to blotter pricing columns. PnL shows empty when mid is `--`.
- **Never show "0.00" as a price** in any table cell. Any code path that formats prices for display must check for zeros and use `--`.

## Engineering Conventions
- **Python dependencies:** `pyproject.toml` is the single source of truth. Min version pinning (`>=X.Y.Z`). Dev deps in `[project.optional-dependencies] dev`, Bloomberg in `bloomberg`.
- **Frontend dependencies:** `frontend/package.json`. React 18, AG Grid Community 32, Zustand 5, Vite 6.
- **Cross-platform:** Code runs on Windows (Bloomberg Terminal) and macOS/Linux (dev). `sys.platform == "win32"` guards for Windows modules. File locking: `msvcrt` (Windows), `fcntl` (Unix).
- **API design:** All REST endpoints under `/api/` prefix. WebSocket at `/api/ws/prices`. Vite proxy forwards `/api` to FastAPI.
- **State management:** Zustand stores are the single source of truth for UI state. Blotter column visibility persisted to localStorage via `zustand/persist`.
- **Technical debt:** Track deferred items in `DEBT.md` with rationale for deferral.

## Current Status & Next Steps
- Full React + FastAPI migration complete (replaced Dash)
- Parser handles all IDB broker shorthand formats (19 structure types)
- Bloomberg API integrated; falls back to mock when Terminal not running
- Order Blotter: AG Grid with live price updates via WebSocket, editable cells, column toggle, PnL auto-calc, cross-tab sync
- Per-day order storage (`orders/YYYY-MM-DD.json`) with one-time migration from legacy `orders.json`
- ISO 8601 timestamps (`YYYY-MM-DDTHH:MM:SS`) for correct cross-day sorting
- 144 Python tests all passing (business logic unchanged)
- Next: date picker UI for browsing historical order dates
- Next: delta adjustment for stock tie vs current price in structure pricing
- Next: more structure types as needed (diagonals, etc.)
- Next: SPX/index options with combo pricing

## GitHub
- Repo: https://github.com/hermanrockefeller-glitch/mycodebase.git
- Single branch: `main`
- Auth: HTTPS via `gh` credential helper
