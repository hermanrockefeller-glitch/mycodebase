"""FastAPI application entry point for the Options Pricer API.

Run with: uvicorn api.main:app --reload --port 8000
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.requests import Request

from .dependencies import shutdown_client, startup_client
from .routes import orders, parse, price, source
from .ws import price_broadcast_loop, router as ws_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    startup_client()
    # Start the background price broadcaster
    task = asyncio.create_task(price_broadcast_loop())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    shutdown_client()


app = FastAPI(
    title="Options Pricer API",
    version="0.1.0",
    lifespan=lifespan,
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Catch-all for unhandled exceptions — returns JSON so the frontend can parse it."""
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal error: {type(exc).__name__}: {exc}"},
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(parse.router, prefix="/api")
app.include_router(price.router, prefix="/api")
app.include_router(orders.router, prefix="/api")
app.include_router(source.router, prefix="/api")
app.include_router(ws_router, prefix="/api")
