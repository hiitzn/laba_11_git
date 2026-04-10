import httpx
from fastapi import APIRouter, Depends, HTTPException, Request

from gateway.client import OrderServiceClient
from gateway.config import get_price
from gateway.models import DownstreamOrderPayload, OrderRequest, OrderResponse

router = APIRouter()


def _get_client(request: Request) -> OrderServiceClient:
    return request.app.state.order_client


@router.post("/order", response_model=OrderResponse)
async def create_order(
    req: OrderRequest,
    client: OrderServiceClient = Depends(_get_client),
) -> OrderResponse:
    try:
        price = get_price(req.item)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    payload = DownstreamOrderPayload(
        item=req.item,
        price=price,
        loyalty_card=req.loyalty_card,
    )
    try:
        return await client.create_order(payload)
    except httpx.HTTPStatusError as exc:
        # S1: surface downstream errors as 502 Bad Gateway rather than letting
        # an unhandled exception produce a generic 500.
        raise HTTPException(
            status_code=502,
            detail=f"order service returned {exc.response.status_code}",
        ) from exc


@router.get("/order/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: int,
    client: OrderServiceClient = Depends(_get_client),
) -> OrderResponse:
    order = await client.get_order(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return order
