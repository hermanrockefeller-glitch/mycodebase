"""JSON-based persistence layer for the order blotter.

Orders are stored at ~/.options_pricer/orders.json with atomic writes
(write to temp file, then rename) to prevent corruption.
Both dashboards can read/write the same file.

Cross-process file locking (msvcrt on Windows) prevents data loss when
two dashboard processes perform concurrent read-modify-write cycles.
"""

import json
import msvcrt
import os
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path


_ORDERS_DIR = Path.home() / ".options_pricer"
_ORDERS_FILE = _ORDERS_DIR / "orders.json"
_LOCK_FILE = _ORDERS_DIR / "orders.lock"
_LOCK_TIMEOUT = 5.0   # seconds
_LOCK_RETRY = 0.05    # retry interval


@contextmanager
def _file_lock(filepath: Path | None = None):
    """Acquire an exclusive cross-process lock on the orders file.

    Uses a sidecar .lock file with msvcrt.locking() for Windows.
    Lock path is derived from filepath's parent so tests with tmp_path
    get isolated lock files.
    """
    lock_path = (filepath.parent / "orders.lock") if filepath else _LOCK_FILE
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR)
    deadline = time.monotonic() + _LOCK_TIMEOUT
    acquired = False
    try:
        while time.monotonic() < deadline:
            try:
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
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
                msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
            except OSError:
                pass
        os.close(fd)


def load_orders(filepath: Path | None = None) -> list[dict]:
    """Load all orders from the JSON file. Returns [] if missing or corrupt."""
    fp = filepath or _ORDERS_FILE
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
    fp = filepath or _ORDERS_FILE
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
    with _file_lock(filepath):
        orders = load_orders(filepath)
        orders.append(order)
        save_orders(orders, filepath)
    return orders


def update_order(order_id: str, updates: dict, filepath: Path | None = None) -> list[dict]:
    """Update an existing order by ID and persist. Returns updated orders list."""
    with _file_lock(filepath):
        orders = load_orders(filepath)
        for order in orders:
            if order.get("id") == order_id:
                order.update(updates)
                break
        save_orders(orders, filepath)
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
    fp = filepath or _ORDERS_FILE
    try:
        return fp.stat().st_mtime
    except OSError:
        return 0.0
