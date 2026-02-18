"""JSON-based persistence layer for the order blotter.

Orders are stored per-day at ~/.options_pricer/orders/YYYY-MM-DD.json with
atomic writes (write to temp file, then rename) to prevent corruption.

Cross-process file locking (msvcrt on Windows, fcntl on Unix) prevents
data loss when two dashboard processes perform concurrent read-modify-write
cycles.
"""

import json
import logging
import os
import re
import sys
import tempfile
import time
from contextlib import contextmanager
from datetime import date
from pathlib import Path

if sys.platform == "win32":
    import msvcrt
else:
    import fcntl

logger = logging.getLogger(__name__)

_BASE_DIR = Path.home() / ".options_pricer"
_ORDERS_DIR = _BASE_DIR / "orders"
_LEGACY_FILE = _BASE_DIR / "orders.json"
_LOCK_TIMEOUT = 5.0   # seconds
_LOCK_RETRY = 0.05    # retry interval

_migrated = False


def _orders_file_for_date(d: date | None = None) -> Path:
    """Return the orders file path for a given date (default today)."""
    d = d or date.today()
    return _ORDERS_DIR / f"{d.isoformat()}.json"


def _migrate_legacy_orders() -> None:
    """One-time migration from single orders.json to per-day directory."""
    global _migrated
    if _migrated:
        return
    _migrated = True

    if not _LEGACY_FILE.exists():
        return
    if _ORDERS_DIR.exists():
        return  # Already migrated

    try:
        with open(_LEGACY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        orders = data.get("orders", [])
        _ORDERS_DIR.mkdir(parents=True, exist_ok=True)
        if orders:
            save_orders(orders, _orders_file_for_date())
        _LEGACY_FILE.rename(_LEGACY_FILE.with_suffix(".json.bak"))
        logger.info(
            "Migrated %d orders from orders.json to orders/%s.json",
            len(orders),
            date.today().isoformat(),
        )
    except Exception:
        logger.exception("Legacy order migration failed")


@contextmanager
def _file_lock(filepath: Path | None = None):
    """Acquire an exclusive cross-process lock on the orders file.

    Uses a sidecar .lock file with msvcrt.locking() on Windows or
    fcntl.flock() on Unix.  Lock path is derived from filepath's parent
    so tests with tmp_path get isolated lock files.
    """
    if filepath:
        lock_path = filepath.parent / "orders.lock"
    else:
        lock_path = _ORDERS_DIR / "orders.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR)
    acquired = False
    try:
        if sys.platform == "win32":
            deadline = time.monotonic() + _LOCK_TIMEOUT
            while time.monotonic() < deadline:
                try:
                    msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                    acquired = True
                    break
                except OSError:
                    time.sleep(_LOCK_RETRY)
            if not acquired:
                raise TimeoutError("Could not acquire order file lock within timeout")
        else:
            deadline = time.monotonic() + _LOCK_TIMEOUT
            while time.monotonic() < deadline:
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    acquired = True
                    break
                except OSError:
                    time.sleep(_LOCK_RETRY)
            if not acquired:
                raise TimeoutError("Could not acquire order file lock within timeout")
        yield
    finally:
        if acquired:
            try:
                if sys.platform == "win32":
                    msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(fd, fcntl.LOCK_UN)
            except OSError:
                pass
        os.close(fd)


def load_orders(filepath: Path | None = None) -> list[dict]:
    """Load all orders from the JSON file. Returns [] if missing or corrupt.

    When no filepath is given, loads today's per-day file after running
    one-time migration from the legacy single-file format.
    """
    if filepath is None:
        _migrate_legacy_orders()
        fp = _orders_file_for_date()
    else:
        fp = filepath
    if not fp.exists():
        return []
    try:
        with open(fp, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("orders", [])
    except (json.JSONDecodeError, KeyError, IOError):
        return []


def save_orders(orders: list[dict], filepath: Path | None = None) -> None:
    """Atomically write orders to the JSON file (write to temp, then rename)."""
    fp = filepath or _orders_file_for_date()
    fp.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(
        dir=str(fp.parent), suffix=".tmp", prefix=".orders_"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({"orders": orders}, f, indent=2, default=str)
        os.replace(tmp_path, str(fp))
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def add_order(order: dict, filepath: Path | None = None) -> list[dict]:
    """Add a new order and persist. Returns updated orders list."""
    fp = filepath or _orders_file_for_date()
    with _file_lock(filepath):
        orders = load_orders(fp)
        orders.append(order)
        save_orders(orders, fp)
    return orders


def update_order(order_id: str, updates: dict, filepath: Path | None = None) -> list[dict]:
    """Update an existing order by ID and persist. Returns updated orders list."""
    fp = filepath or _orders_file_for_date()
    with _file_lock(filepath):
        orders = load_orders(fp)
        for order in orders:
            if order.get("id") == order_id:
                order.update(updates)
                break
        save_orders(orders, fp)
    return orders


def save_orders_locked(orders: list[dict], filepath: Path | None = None) -> None:
    """Atomically write orders under file lock.

    Use this when the caller does its own load-modify-save cycle
    (e.g. sync_blotter_edits in the dashboard callbacks).
    """
    with _file_lock(filepath):
        save_orders(orders, filepath)


def orders_to_display(orders: list[dict]) -> list[dict]:
    """Strip private underscore-prefixed keys for blotter display."""
    return [
        {k: v for k, v in o.items() if not k.startswith("_")}
        for o in orders
    ]


def get_orders_mtime(filepath: Path | None = None) -> float:
    """Return the mtime of the orders JSON file, or 0.0 if missing."""
    fp = filepath or _orders_file_for_date()
    try:
        return fp.stat().st_mtime
    except OSError:
        return 0.0


def list_order_dates(dirpath: Path | None = None) -> list[date]:
    """List available order dates, sorted most recent first.

    Scans the orders directory for YYYY-MM-DD.json files.
    """
    dp = dirpath or _ORDERS_DIR
    if not dp.is_dir():
        return []
    dates: list[date] = []
    for f in dp.iterdir():
        if f.suffix == ".json" and re.match(r"^\d{4}-\d{2}-\d{2}$", f.stem):
            try:
                dates.append(date.fromisoformat(f.stem))
            except ValueError:
                continue
    dates.sort(reverse=True)
    return dates
