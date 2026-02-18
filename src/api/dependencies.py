"""Shared state: Bloomberg client singleton and WebSocket connection manager."""

from __future__ import annotations

import json
import logging

from fastapi import WebSocket

from options_pricer.bloomberg import (
    BloombergClient,
    MockBloombergClient,
    create_client,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Bloomberg client singleton
# ---------------------------------------------------------------------------

_client: BloombergClient | MockBloombergClient | None = None


def startup_client() -> None:
    global _client
    _client = create_client(use_mock=False)


def shutdown_client() -> None:
    global _client
    if _client is not None:
        _client.disconnect()
        _client = None


def get_client() -> BloombergClient | MockBloombergClient:
    if _client is None:
        raise RuntimeError("Client not initialised — call startup_client() first")
    return _client


def set_client(client: BloombergClient | MockBloombergClient) -> None:
    global _client
    _client = client


# ---------------------------------------------------------------------------
# WebSocket connection manager
# ---------------------------------------------------------------------------


class ConnectionManager:
    """Manages active WebSocket connections for broadcasting price updates."""

    def __init__(self) -> None:
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket) -> None:
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, message: dict) -> None:
        data = json.dumps(message, default=str)
        for ws in self.active[:]:
            try:
                await ws.send_text(data)
            except Exception:
                logger.debug("Removing dead WebSocket connection")
                self.active.remove(ws)


manager = ConnectionManager()
