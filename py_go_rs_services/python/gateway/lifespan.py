from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from gateway.client import OrderServiceClient
from gateway.config import ORDER_SERVICE_URL


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Create the shared HTTP client on startup; close it on shutdown."""
    app.state.order_client = OrderServiceClient(ORDER_SERVICE_URL)
    try:
        yield
    finally:
        await app.state.order_client.aclose()