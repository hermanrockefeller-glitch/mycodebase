"""Tests for the order store JSON persistence layer."""

import json
from pathlib import Path

import pytest

from options_pricer.order_store import (
    _file_lock,
    add_order,
    get_orders_mtime,
    load_orders,
    orders_to_display,
    save_orders,
    save_orders_locked,
    update_order,
)


class TestLoadOrders:
    def test_missing_file(self, tmp_path):
        fp = tmp_path / "orders.json"
        assert load_orders(fp) == []

    def test_corrupt_json(self, tmp_path):
        fp = tmp_path / "orders.json"
        fp.write_text("NOT VALID JSON {{{", encoding="utf-8")
        assert load_orders(fp) == []

    def test_empty_orders_key(self, tmp_path):
        fp = tmp_path / "orders.json"
        fp.write_text('{"orders": []}', encoding="utf-8")
        assert load_orders(fp) == []

    def test_loads_existing(self, tmp_path):
        fp = tmp_path / "orders.json"
        data = {"orders": [{"id": "abc", "underlying": "AAPL"}]}
        fp.write_text(json.dumps(data), encoding="utf-8")
        result = load_orders(fp)
        assert len(result) == 1
        assert result[0]["underlying"] == "AAPL"


class TestSaveOrders:
    def test_creates_file(self, tmp_path):
        fp = tmp_path / "orders.json"
        save_orders([{"id": "1", "underlying": "AAPL"}], fp)
        assert fp.exists()
        data = json.loads(fp.read_text(encoding="utf-8"))
        assert len(data["orders"]) == 1

    def test_creates_parent_dirs(self, tmp_path):
        fp = tmp_path / "subdir" / "orders.json"
        save_orders([], fp)
        assert fp.exists()

    def test_overwrites_existing(self, tmp_path):
        fp = tmp_path / "orders.json"
        save_orders([{"id": "1"}], fp)
        save_orders([{"id": "1"}, {"id": "2"}], fp)
        data = json.loads(fp.read_text(encoding="utf-8"))
        assert len(data["orders"]) == 2


class TestAddOrder:
    def test_adds_to_empty(self, tmp_path):
        fp = tmp_path / "orders.json"
        result = add_order({"id": "abc", "underlying": "AAPL"}, fp)
        assert len(result) == 1
        assert result[0]["id"] == "abc"
        # Verify persisted
        assert len(load_orders(fp)) == 1

    def test_appends_to_existing(self, tmp_path):
        fp = tmp_path / "orders.json"
        add_order({"id": "1", "underlying": "AAPL"}, fp)
        result = add_order({"id": "2", "underlying": "MSFT"}, fp)
        assert len(result) == 2
        assert result[1]["underlying"] == "MSFT"


class TestUpdateOrder:
    def test_updates_existing(self, tmp_path):
        fp = tmp_path / "orders.json"
        add_order({"id": "abc", "traded": "No", "initiator": ""}, fp)
        result = update_order("abc", {"traded": "Yes", "initiator": "GS"}, fp)
        assert result[0]["traded"] == "Yes"
        assert result[0]["initiator"] == "GS"
        # Verify persisted
        loaded = load_orders(fp)
        assert loaded[0]["traded"] == "Yes"

    def test_update_nonexistent_id(self, tmp_path):
        fp = tmp_path / "orders.json"
        add_order({"id": "abc", "traded": "No"}, fp)
        result = update_order("nonexistent", {"traded": "Yes"}, fp)
        # Original unchanged
        assert result[0]["traded"] == "No"


class TestFileLock:
    def test_lock_acquire_release(self, tmp_path):
        """Lock can be acquired and released without error."""
        fp = tmp_path / "orders.json"
        save_orders([], fp)
        with _file_lock(fp):
            pass  # No exception = success

    def test_lock_protects_write(self, tmp_path):
        """add_order with lock persists correctly."""
        fp = tmp_path / "orders.json"
        result = add_order({"id": "1", "underlying": "AAPL"}, fp)
        assert len(result) == 1
        assert load_orders(fp)[0]["id"] == "1"

    def test_save_orders_locked(self, tmp_path):
        """save_orders_locked persists under lock."""
        fp = tmp_path / "orders.json"
        save_orders_locked([{"id": "x", "data": "test"}], fp)
        loaded = load_orders(fp)
        assert len(loaded) == 1
        assert loaded[0]["id"] == "x"


class TestRecallByIdAfterSort:
    """Verify that looking up an order by id from a sorted display list
    returns the correct full order — the core logic the recall callback
    depends on."""

    def test_sorted_display_matches_correct_order(self, tmp_path):
        fp = tmp_path / "orders.json"

        # Two orders with different structures and recall data
        order_a = {
            "id": "aaa",
            "added_time": "09:00",
            "underlying": "AAPL",
            "structure": "CALL 300C Jun26",
            "_table_data": [{"leg": "Leg 1", "strike": 300, "type": "C"}],
            "_underlying": "AAPL",
        }
        order_b = {
            "id": "bbb",
            "added_time": "10:00",
            "underlying": "SPX",
            "structure": "PUT SPREAD 4000/4050 Jun26",
            "_table_data": [
                {"leg": "Leg 1", "strike": 4050, "type": "P"},
                {"leg": "Leg 2", "strike": 4000, "type": "P"},
            ],
            "_underlying": "SPX",
        }

        orders = [order_a, order_b]
        save_orders(orders, fp)
        loaded = load_orders(fp)

        # Display rows strip underscore fields but keep id
        display = orders_to_display(loaded)
        assert display[0]["id"] == "aaa"
        assert display[1]["id"] == "bbb"
        assert "_table_data" not in display[0]
        assert "_table_data" not in display[1]

        # Simulate sorted view (time desc → B first, A second)
        sorted_view = list(reversed(display))
        assert sorted_view[0]["id"] == "bbb"  # visually row 0
        assert sorted_view[1]["id"] == "aaa"  # visually row 1

        # Clicking row 0 in sorted view should give SPX, not AAPL
        clicked_id = sorted_view[0]["id"]
        recalled = next(o for o in loaded if o["id"] == clicked_id)
        assert recalled["underlying"] == "SPX"
        assert recalled["_underlying"] == "SPX"
        assert len(recalled["_table_data"]) == 2
        assert recalled["_table_data"][0]["strike"] == 4050

        # Clicking row 1 in sorted view should give AAPL
        clicked_id = sorted_view[1]["id"]
        recalled = next(o for o in loaded if o["id"] == clicked_id)
        assert recalled["underlying"] == "AAPL"
        assert recalled["_underlying"] == "AAPL"
        assert len(recalled["_table_data"]) == 1
        assert recalled["_table_data"][0]["strike"] == 300


class TestGetOrdersMtime:
    def test_missing_file_returns_zero(self, tmp_path):
        fp = tmp_path / "orders.json"
        assert get_orders_mtime(fp) == 0.0

    def test_returns_nonzero_for_existing(self, tmp_path):
        fp = tmp_path / "orders.json"
        save_orders([], fp)
        mtime = get_orders_mtime(fp)
        assert mtime > 0.0

    def test_mtime_changes_after_write(self, tmp_path):
        import time
        fp = tmp_path / "orders.json"
        save_orders([], fp)
        mtime1 = get_orders_mtime(fp)
        time.sleep(0.05)  # Ensure filesystem mtime granularity
        save_orders([{"id": "1"}], fp)
        mtime2 = get_orders_mtime(fp)
        assert mtime2 > mtime1
