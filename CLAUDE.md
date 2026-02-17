# Options Pricer — Project Context

## What This Is
An options pricing tool for an IDB (inter-dealer broker) equity derivatives broker. Parses real broker shorthand orders, fetches screen market data (Bloomberg or mock), and displays structure-level implied bid/offer/mid on a web dashboard.

The core use case: broker sends an order like `AAPL Jun26 240/220 PS 1X2 vs250 15d 500x @ 3.50 1X over`, user pastes it into the dashboard, and instantly sees screen-implied pricing for the structure to compare against the broker's quote.

## Tech Stack
- **Python 3.12** (venv at `.venv/`, activate with `source .venv/Scripts/activate` on Windows)
- **Dash (Plotly)** — web dashboard
- **NumPy / SciPy** — numerical pricing
- **blpapi 3.25.12** — Bloomberg Terminal API (installed; falls back to mock when Terminal not running)
- **pytest** — 133 tests, all passing

## Project Structure
```
src/options_pricer/
├── models.py            # OptionLeg, OptionStructure, ParsedOrder, LegMarketData, StructureMarketData
├── parser.py            # Flexible IDB broker shorthand parser (regex-based, order-independent tokens)
├── pricer.py            # Black-Scholes pricing engine + Greeks (delta, gamma, theta, vega, rho)
├── structure_pricer.py  # Calculates structure bid/offer/mid from individual leg screen prices
├── bloomberg.py         # BloombergClient (live) + MockBloombergClient (BS-based realistic quotes)
├── order_store.py       # JSON persistence + cross-process file locking (~/.options_pricer/orders.json)
└── dashboard/
    ├── app.py           # Dash web app entry point + pricer-specific callbacks
    ├── blotter_app.py   # Standalone blotter dashboard (port 8051) — shares orders.json
    ├── callbacks.py     # Shared blotter callbacks (poll, sync edits, column toggle/visibility)
    └── layouts.py       # UI layouts: pricer dashboard, blotter-only dashboard, shared components
tests/
├── test_models.py       # 17 tests — payoffs, structures
├── test_parser.py       # 68 tests — extraction helpers + full order parsing for all IDB formats
├── test_order_store.py  # 17 tests — JSON persistence, file locking, mtime helpers
└── test_pricer.py       # 25 tests — BS pricing, put-call parity, Greeks, structure pricing
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
- **Paste Order:** `dcc.Textarea` for broker shorthand input. Enter key triggers parse & price via clientside callback.
- **Pricer Toolbar:** Underlying | Structure | Tie | Delta | Order Price | Side | Qty | [Add Order] — dual-purpose: configures pricing AND submits to order blotter. Side/Qty/Price are all optional.
- **Header bar:** Ticker, structure type, tie price, current stock price, delta (+/-)
- **Pricing table:** Editable DataTable — Leg | Expiry | Strike | Type | Side | Qty | Bid Size | Bid | Mid | Offer | Offer Size. Editing triggers auto-reprice.
  - Structure row at bottom with implied bid/offer/mid and sizes
- **Broker quote section:** Shows broker price vs screen mid and edge
- **Order Blotter:** Persistent library of all priced structures. 15 columns (6 editable: side, size, traded, bought/sold, traded price, initiator). Column toggle via "Columns" button. Native sort (default: time desc). Click row to recall into pricer. PnL auto-calcs for traded orders. Data persists to `~/.options_pricer/orders.json`. **Syncs across dashboards** via 2-second file polling.
- **Standalone Blotter (port 8051):** Blotter-only dashboard — shows the same order data, editable cells, column toggle. No pricer or parser. Edits sync bidirectionally with the pricer dashboard.
- **Architecture:** Toolbar is always visible; "Add Order" validates a structure is priced. Hidden ID stubs (`order-input-section`, `order-side`, `order-size`) exist for Dash callback compatibility after the standalone order input section was removed.

## Cross-Dashboard Sync Architecture
- Both dashboards read/write `~/.options_pricer/orders.json` with atomic writes + cross-process file locking (`msvcrt` on Windows)
- A `dcc.Interval` (2-second timer) checks `os.path.getmtime()` on the JSON file
- Write suppression: after writing, the dashboard stamps `last-write-time = file_mtime` so it skips reloading its own changes
- `blotter-edit-suppress` prevents feedback loops when `sync_blotter_edits` programmatically updates the blotter table
- **Both dashboards use the same blotter protocol:** table only updates on user actions (`sync_blotter_edits`, `add_order`), never from store changes. Polling updates the `order-store` (fresh prices), which are picked up on the next user edit. This prevents React re-renders from disrupting editing UI (dropdowns, keystrokes, cell selection).

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
pytest tests/ -v                                   # Run all 133 tests
python -m options_pricer.dashboard.app             # Launch pricer dashboard at http://127.0.0.1:8050
python -m options_pricer.dashboard.blotter_app     # Launch blotter dashboard at http://127.0.0.1:8051
```

## UI Rules (MUST follow when editing layouts.py or any dashboard styling)
- **No content cutoff:** Never use `overflow: hidden` on containers that hold interactive content (toolbars, tables, inputs, dropdowns). Use `overflow: visible` or `overflow: auto` instead.
- **Box sizing:** All elements with `width: 100%` must also set `boxSizing: border-box` so padding/border don't cause overflow.
- **Max width:** The main layout container uses `maxWidth: 1400px`. Do not shrink this without good reason.
- **Text inputs that may contain long strings:** Use `dcc.Textarea` (not `dcc.Input`) so text wraps visibly. Set `minHeight: 80px`, `resize: vertical`, `lineHeight: 1.5`, and `boxSizing: border-box`. `dcc.Input` is single-line and clips long text — never use it for order/paste fields.
- **Enter key on Textarea:** `dcc.Textarea` does not support `n_submit`. Use a clientside callback that binds a `keydown` listener and calls `btn.click()` on Enter (see `app.py` for the pattern). Shift+Enter should still allow newlines.
- **Dropdowns in tables:** Dash DataTable dropdown columns can clip inside tight containers — ensure parent has `overflow: visible`.
- **Test visually:** After any layout change, confirm in the browser that all text, inputs, buttons, and table columns are fully visible and not clipped. Scroll horizontally if the table is wide (`overflowX: auto` on DataTable).
- **Consistent sizing:** Use monospace font at 13px for data cells, 16px for the order input. Keep padding consistent (8-14px for inputs, 10-14px for table cells).
- **Resizable table containers:** Wrap DataTables in a container with CSS `resize: vertical` (or `resize: both`) so users can drag to adjust the table area. Dash DataTable does NOT support a column-level `resizable` prop — never add invalid keys to column definitions (valid keys: `id`, `name`, `type`, `presentation`, `editable`, `selectable`, `clearable`, `deletable`, `hideable`, `renamable`, `filter_options`, `format`, `on_change`, `sort_as_null`, `validation`).

## Auto-Refresh Rules (MUST follow across ALL dashboard components)
Auto-refresh updates ONLY calculations and live-feed data from the API. It must NEVER touch any field the user can manually edit.

- **Principle: auto-refresh = calculations + live feed ONLY.** Any column or cell that accepts manual user input is off-limits to auto-refresh. Only overwrite values that come from the API (prices, sizes) or are computed from them (mid, PnL). This applies to every table, every callback, every dashboard — not just the blotter.
- **CRITICAL: Never let a timer/interval callback write to a DataTable's `data` property.** Any assignment to `data` — even `Patch()`, even identical values — triggers a React re-render that resets all editing UI state (closes open dropdowns, clears in-progress keystrokes, deselects cells). This is a Dash/React limitation with no workaround.
- **Architecture: separate timer callbacks from table callbacks.** Timer-driven callbacks (`dcc.Interval`) must only output to display-only HTML components (`html.Div`, `html.Span`) and `dcc.Store` components. Table updates (`pricing-display.data`, `blotter-table.data`) must only happen in response to user actions (cell edit via `data_timestamp`, button click, parse order, etc.).
- **Current implementation:**
  - `auto_price_from_table` — triggered by `data_timestamp` + `manual-underlying` only (NO interval). Updates pricer table + header + broker quote.
  - `refresh_live_display` — triggered by `live-refresh-interval` only. Updates header (live stock price) + broker quote (edge). Never touches any DataTable.
  - `refresh_blotter_prices` — triggered by `live-refresh-interval`. Updates `order-store` (client-side store) AND persists to `orders.json` so Admin Dashboard picks up fresh prices via file polling. Stamps `last-write-time` so the pricer's own poll skips reloading.
  - `push_store_to_blotter` — triggered by `order-store.data` changes (NOT a timer). Pushes display rows to `blotter-table.data` only when user is not actively editing. Sets `blotter-edit-suppress` so `sync_blotter_edits` skips the programmatic `data_timestamp` change.
- **Blotter table:** 6 editable fields (`side`, `size`, `traded`, `bought_sold`, `traded_price`, `initiator`) must never be overwritten. Only update pricing columns and computed `pnl`.
- **Wrap API calls in try/except.** Bloomberg fetch errors must not crash the refresh callback — a single bad ticker should not break repricing for all orders.
- **CRITICAL: Any callback that programmatically writes to `blotter-table.data` MUST also output `blotter-edit-suppress = True`.** Writing to `data` triggers `data_timestamp`, which fires `sync_blotter_edits`. Without the suppress flag, `sync_blotter_edits` runs, potentially writes back to `order-store.data`, which re-triggers the original callback — creating an infinite loop. This applies to `push_store_to_blotter`, `sync_blotter_edits` itself, and `add_order`.
- **CRITICAL: Every return path in a callback must return the correct number of values matching its Output count.** A callback with N Outputs must return N values on every path (including early returns). Returning fewer values causes Dash errors. Use `return no_update, no_update, ...` (one per Output) for skip paths.

## Pricer Auto-Recalculation Principle
Any change to a pricing input must trigger automatic recalculation of structure bid/mid/offer. Pricing inputs include:
- **Table edits:** expiry, strike, type, ratio (via `data_timestamp`)
- **Toolbar fields:** underlying, tie, delta, broker price, side, quantity (all `Input`, not `State`)
- The `auto-price-suppress` flag prevents self-loops (callback outputs table → timestamp fires → suppress blocks → resets to False)
- Toolbar `dcc.Input` fields must have `debounce=True` to avoid per-keystroke repricing

## Bloomberg Failure Visibility (MUST follow for all pricing displays)
Bloomberg failures must ALWAYS be surfaced visibly to the user. Never silently show zero prices or fallback values.

- **Connection-level**: When Bloomberg is selected but `get_spot()` returns `None`, show RED badge + alert banner at top of dashboard. Badge auto-reverts to green when Bloomberg recovers.
- **Cell-level**: When a quote returns `bid=0 AND offer=0`, display `--` not `0.00`. Zero is never a valid displayed price — a real zero-bid option still has an offer.
- **Structure-level**: If ANY leg has a failed quote, the structure summary row must also show `--`. Don't compute a structure price from partially invalid data.
- **Blotter propagation**: Same `--` formatting applies to blotter pricing columns. PnL shows empty when mid is `--`.
- **Never show "0.00" as a price** in any table cell. Any code path that formats prices for display must check for zeros and use `--`.

## Current Status & Next Steps
- Parser handles all example formats provided so far (including `Nk` quantity format) — feed more real orders to refine
- Bloomberg API integrated but needs Terminal running for live data; mock works for dev
- Order Blotter with JSON persistence, editable cells, column toggle, PnL auto-calc, and recall working
- Cross-dashboard sync: pricer (8050) + standalone blotter (8051) share orders.json with polling + file locking
- Next: delta adjustment for stock tie vs current price in structure pricing
- Structure types: call, put, put spread, call spread, risk reversal, straddle, strangle, butterfly, put fly, call fly, iron butterfly, iron condor, put condor, call condor, collar, call spread collar, put spread collar
- Next: more structure types as needed (diagonals, etc.)
- Next: SPX/index options with combo pricing

## GitHub
- Repo: https://github.com/hermanrockefeller-glitch/mycodebase.git
- Single branch: `main`
- Auth: HTTPS via `gh` credential helper
