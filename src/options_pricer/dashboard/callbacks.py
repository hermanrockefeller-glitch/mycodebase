"""Shared Dash callbacks used by both the pricer and blotter dashboards.

Call ``register_blotter_callbacks()`` after creating a Dash app to wire up
the polling, edit-sync, column-toggle, and column-visibility callbacks.
"""

import time

from dash import Input, Output, State, callback, no_update

from ..order_store import (
    get_orders_mtime,
    load_orders,
    orders_to_display,
    save_orders_locked,
)
from .layouts import _BLOTTER_COLUMNS

_EDITABLE_FIELDS = ("side", "size", "traded", "bought_sold", "traded_price", "initiator")


def recalc_pnl(order: dict) -> bool:
    """Update order['pnl'] in-place based on current mid and trade info.

    Returns True if the pnl value changed.
    """
    old_pnl = order.get("pnl")

    if (order.get("traded") == "Yes"
            and order.get("traded_price") not in (None, "")
            and order.get("bought_sold") in ("Bought", "Sold")):
        try:
            mid = float(order.get("mid", 0))
            tp = float(order["traded_price"])
            sz = int(order.get("size", 0))
            mult = order.get("multiplier", 100)
            if order["bought_sold"] == "Bought":
                pnl = (mid - tp) * sz * mult
            else:
                pnl = (tp - mid) * sz * mult
            order["pnl"] = f"{pnl:+,.0f}"
        except (ValueError, TypeError):
            order["pnl"] = ""
    elif order.get("traded") != "Yes":
        order["pnl"] = ""

    return order.get("pnl") != old_pnl


def _sync_edits(blotter_data, orders):
    """Core logic for syncing blotter edits back to the order store.

    Returns (updated_orders, display_rows, new_mtime) if anything changed,
    or None if nothing changed.
    """
    order_map = {o["id"]: o for o in orders if "id" in o}

    changed = False

    for row in blotter_data:
        order_id = row.get("id")
        if not order_id or order_id not in order_map:
            continue

        stored = order_map[order_id]

        for field in _EDITABLE_FIELDS:
            new_val = row.get(field)
            if new_val != stored.get(field):
                stored[field] = new_val
                changed = True

        if recalc_pnl(stored):
            changed = True

    if not changed:
        return None

    updated_orders = list(order_map.values())
    save_orders_locked(updated_orders)
    new_mtime = get_orders_mtime()
    display_rows = orders_to_display(updated_orders)

    return updated_orders, display_rows, new_mtime


def register_blotter_callbacks():
    """Register the four blotter callbacks shared by both dashboards."""

    @callback(
        Output("order-store", "data", allow_duplicate=True),
        Output("file-mtime", "data"),
        Input("poll-interval", "n_intervals"),
        State("file-mtime", "data"),
        State("last-write-time", "data"),
        prevent_initial_call=True,
    )
    def poll_for_changes(n_intervals, known_mtime, last_write_time):
        """Check if orders.json was modified externally; if so, reload into store.

        Never writes to blotter-table.data — any assignment triggers a React
        re-render that resets editing state (closes dropdowns, clears keystrokes).
        """
        current_mtime = get_orders_mtime()

        if current_mtime == known_mtime:
            return no_update, no_update

        if current_mtime == last_write_time:
            return no_update, current_mtime

        orders = load_orders()
        return orders, current_mtime

    @callback(
        Output("order-store", "data", allow_duplicate=True),
        Output("blotter-table", "data", allow_duplicate=True),
        Output("blotter-edit-suppress", "data", allow_duplicate=True),
        Output("last-write-time", "data", allow_duplicate=True),
        Input("blotter-table", "data_timestamp"),
        State("blotter-table", "data"),
        State("order-store", "data"),
        State("blotter-edit-suppress", "data"),
        prevent_initial_call=True,
    )
    def sync_blotter_edits(data_ts, blotter_data, orders, suppress):
        """Sync editable cell changes back to order-store and persist to JSON."""
        if suppress:
            return no_update, no_update, False, no_update

        if not blotter_data or not orders:
            return no_update, no_update, False, no_update

        result = _sync_edits(blotter_data, orders)
        if result is None:
            return no_update, no_update, False, no_update

        updated_orders, display_rows, new_mtime = result
        return updated_orders, display_rows, True, new_mtime

    @callback(
        Output("column-toggle-panel", "style"),
        Input("column-toggle-btn", "n_clicks"),
        State("column-toggle-panel", "style"),
        prevent_initial_call=True,
    )
    def toggle_column_panel(n_clicks, current_style):
        if not current_style or current_style.get("display") == "none":
            return {"display": "block"}
        return {"display": "none"}

    @callback(
        Output("blotter-table", "columns"),
        Output("visible-columns", "data"),
        Input("column-checklist", "value"),
        prevent_initial_call=True,
    )
    def update_visible_columns(selected_columns):
        visible = [c for c in _BLOTTER_COLUMNS if c["id"] in selected_columns]
        return visible, selected_columns

    @callback(
        Output("blotter-table", "selected_rows"),
        Input("blotter-select-all", "value"),
        State("blotter-table", "derived_virtual_data"),
        prevent_initial_call=True,
    )
    def toggle_select_all(select_value, virtual_data):
        """Select or deselect all rows in the blotter (Admin Dashboard only)."""
        if "all" in select_value and virtual_data:
            return list(range(len(virtual_data)))
        return []

    @callback(
        Output("blotter-table", "data", allow_duplicate=True),
        Output("blotter-edit-suppress", "data", allow_duplicate=True),
        Input("order-store", "data"),
        State("blotter-table", "active_cell"),
        State("blotter-table", "data_timestamp"),
        prevent_initial_call=True,
    )
    def push_store_to_blotter(orders, active_cell, data_ts):
        """Push updated prices from order-store to the blotter table.

        Skips when the user is actively editing to preserve editing UI
        state (open dropdowns, in-progress keystrokes).  Manual fields
        are never overwritten — the pricer merges edits before saving.

        Sets blotter-edit-suppress so sync_blotter_edits skips the
        programmatic data_timestamp change this write causes.
        """
        # Skip if user has active cell in an editable column
        if active_cell and active_cell.get("column_id") in _EDITABLE_FIELDS:
            return no_update, no_update

        # Skip if a cell was edited in the last 3 seconds
        now_ms = time.time() * 1000
        if data_ts and (now_ms - data_ts) < 3000:
            return no_update, no_update

        if not orders:
            return no_update, no_update

        return orders_to_display(orders), True
