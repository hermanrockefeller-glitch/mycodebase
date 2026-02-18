# Technical Debt

Items identified during code review, intentionally deferred with rationale.

## Parser

- **`_parse_core()` is 232 lines** — Complex token-based state machine with 5-6 levels of nesting. Could be split into sub-parsers (expiry parser, strike parser, type resolver) but the current monolith works correctly and all 68 parser tests pass. Deferring because refactoring risks introducing regressions in a working parser, and the function is read-only (no one edits it day-to-day).

- **Fly/condor builder duplication** — `_build_put_fly()` / `_build_call_fly()` and `_build_put_condor()` / `_build_call_condor()` are near-identical pairs differing only by `OptionType`. Could be parameterized into `_build_fly(option_type)` and `_build_condor(option_type)`. Deferred because the duplication is small (~30 lines each) and the functions are stable.

- **Hardcoded expiry day 16** — `_parse_core()` uses `date(year, month, 16)` as an approximate 3rd Friday. Correct for most months but off by 1-2 days. Deferred because exact expiry date is cosmetic (Bloomberg quotes use the real expiry); only matters for time-to-expiry in mock pricing.

## API / Frontend

- **Broad `except Exception` in WebSocket broadcaster** — `price_broadcast_loop` in `ws.py` catches `Exception` broadly. Should catch specific blpapi exceptions once the live Bloomberg environment is more mature. Deferred because narrowing exception types requires testing against a live Terminal.

- **No Bloomberg client test coverage** — `bloomberg.py` has no dedicated tests. `MockBloombergClient` is tested indirectly through the pricer pipeline. The live `BloombergClient` can only be tested with a running Terminal. Deferred until CI has access to a Bloomberg test environment or a mock blpapi library is adopted.

- **No API endpoint tests** — FastAPI routes have no automated tests. Could use `httpx` with `TestClient` to test all endpoints. Deferred because the endpoints are thin wrappers around well-tested business logic (135 tests) and manual curl testing confirmed correctness.

- **No frontend tests** — React components have no unit or integration tests. Could add Vitest + React Testing Library. Deferred because the codebase is small and manual browser testing catches UI issues.

- **AG Grid bundle size** — Production bundle is ~1MB (290KB gzipped), mostly AG Grid. Could use dynamic imports to code-split AG Grid. Deferred because the app is internal-use and loads quickly on local network.

- **WebSocket reconnection backoff** — Currently uses fixed 2s reconnect delay. Should use exponential backoff with jitter. Deferred because the WS connects to localhost and reconnection storms are unlikely.

## Code Quality

- **Global mutable `_client` in `dependencies.py`** — The Bloomberg client is a module-level global modified by `toggle_source`. Not thread-safe in theory, but FastAPI runs single-process and the toggle is a user-initiated action. Acceptable for now; would need refactoring for multi-worker deployment.

- **No linter/formatter configured** — No `ruff`, `black`, or `flake8` configuration. Code style is consistent by convention but not enforced. Deferred because the codebase is small (single developer) and style is already uniform.

- **`_EMPTY_ROW` naming** — Has a leading underscore suggesting private scope, but is exported and used by `app.py`. Should be renamed to `EMPTY_ROW` for public API consistency. Deferred because renaming requires updating all import sites and is cosmetic.
