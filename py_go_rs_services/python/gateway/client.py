import httpx

from gateway.config import HTTP_TIMEOUT
from gateway.models import DownstreamOrderPayload, OrderResponse


class OrderServiceClient:
    """Async HTTP client for the Go order service.

    A single ``httpx.AsyncClient`` is shared for the process lifetime so
    connections are pooled and reused across requests.
    """

    def __init__(self, base_url: str) -> None:
        self._client = httpx.AsyncClient(base_url=base_url, timeout=HTTP_TIMEOUT)

    async def create_order(self, payload: DownstreamOrderPayload) -> OrderResponse:
        resp = await self._client.post("/order", json=payload.model_dump())
        resp.raise_for_status()
        return OrderResponse.model_validate(resp.json())

    async def get_order(self, order_id: int) -> OrderResponse | None:
        """Return the order, or ``None`` when the service reports 404."""
        resp = await self._client.get(f"/order/{order_id}")
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return OrderResponse.model_validate(resp.json())

    async def aclose(self) -> None:
        await self._client.aclose()
