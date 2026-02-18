"""CRUD endpoints for the order blotter."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from options_pricer.order_store import (
    load_orders,
    orders_to_display,
    save_orders_locked,
    update_order,
)

from ..dependencies import manager
from ..schemas import OrderDeleteRequest, OrderUpdateRequest, OrdersResponse

logger = logging.getLogger(__name__)
router = APIRouter()

_MANUAL_FIELDS = ("side", "size", "traded", "bought_sold", "traded_price", "initiator")


def _recalc_pnl(order: dict) -> None:
    """Update order['pnl'] in-place (mirrors callbacks.recalc_pnl)."""
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


@router.get("/orders", response_model=OrdersResponse)
def get_orders():
    """Return all orders (including private recall fields for the frontend)."""
    orders = load_orders()
    return OrdersResponse(orders=orders)


@router.post("/orders", response_model=OrdersResponse)
async def add_order(body: dict):
    """Add a new order to the blotter and broadcast to all WS clients."""
    orders = load_orders()
    orders.append(body)
    save_orders_locked(orders)

    await manager.broadcast({
        "channel": "order_sync",
        "action": "add",
        "data": {"orders": orders},
    })

    return OrdersResponse(orders=orders)


@router.put("/orders/{order_id}")
async def update_order_fields(order_id: str, req: OrderUpdateRequest):
    """Update manual fields on an existing order."""
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    # Validate field names
    for field in updates:
        if field not in _MANUAL_FIELDS:
            raise HTTPException(
                status_code=400,
                detail=f"Field '{field}' is not editable",
            )

    orders = update_order(order_id, updates)

    # Recalc PnL if trade fields changed
    for order in orders:
        if order.get("id") == order_id:
            _recalc_pnl(order)
            break
    save_orders_locked(orders)

    # Broadcast
    await manager.broadcast({
        "channel": "order_sync",
        "action": "update",
        "data": {"orders": orders},
    })

    target = next((o for o in orders if o.get("id") == order_id), None)
    if target is None:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
    return {"order": target}


@router.delete("/orders", response_model=OrdersResponse)
async def delete_orders(req: OrderDeleteRequest):
    """Delete orders by ID list."""
    if not req.ids:
        raise HTTPException(status_code=400, detail="No IDs provided")

    orders = load_orders()
    id_set = set(req.ids)
    remaining = [o for o in orders if o.get("id") not in id_set]

    if len(remaining) == len(orders):
        raise HTTPException(status_code=404, detail="No matching orders found")

    save_orders_locked(remaining)

    await manager.broadcast({
        "channel": "order_sync",
        "action": "delete",
        "data": {"orders": remaining},
    })

    return OrdersResponse(orders=remaining)
