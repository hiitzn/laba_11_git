"""
Tests for the API Gateway.

The ``client`` fixture lives in conftest.py.
All HTTP calls to the Go order service are intercepted by respx.
"""

import json

import httpx
import pytest
import respx

from gateway.config import MENU, ORDER_SERVICE_URL


# ── Helpers ───────────────────────────────────────────────────────────────────


def _stub(item: str, price: float, points: int, order_id: int = 1) -> dict:
    """Build a minimal order-service response payload."""
    return {
        "id": order_id,
        "item": item,
        "price": price,
        "points": points,
        "status": "completed",
    }


# ── POST /order ───────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "item, loyalty_card, expected_points",
    [
        ("espresso", False, 10),
        ("latte", True, 15),
        ("cappuccino", False, 10),
    ],
)
@respx.mock
def test_create_order_success(client, item, loyalty_card, expected_points):
    price = MENU[item]
    respx.post(f"{ORDER_SERVICE_URL}/order").mock(
        # 201 Created — Go service returns 201 when a new order is created.
        return_value=httpx.Response(201, json=_stub(item, price, expected_points))
    )

    resp = client.post("/order", json={"item": item, "loyalty_card": loyalty_card})

    assert resp.status_code == 200
    data = resp.json()
    assert data["item"] == item
    assert data["price"] == price
    assert data["points"] == expected_points
    assert data["status"] == "completed"
    assert data["id"] == 1


@pytest.mark.parametrize("item, expected_price", list(MENU.items()))
def test_correct_price_forwarded_to_order_service(client, item, expected_price):
    """Gateway must derive price from MENU — never trust the caller."""
    with respx.mock:
        route = respx.post(f"{ORDER_SERVICE_URL}/order").mock(
            # 201 Created — Go service returns 201 when a new order is created.
            return_value=httpx.Response(201, json=_stub(item, expected_price, 10))
        )
        client.post("/order", json={"item": item})

        body = json.loads(route.calls.last.request.content)
        assert body["price"] == expected_price


def test_create_order_unknown_item_returns_400(client):
    resp = client.post("/order", json={"item": "tea"})

    assert resp.status_code == 400
    assert "Unknown item" in resp.json()["detail"]


def test_create_order_unknown_item_lists_available_items(client):
    resp = client.post("/order", json={"item": "water"})

    detail = resp.json()["detail"]
    for item in MENU:
        assert item in detail


def test_create_order_blank_item_returns_422(client):
    """Pydantic validation rejects blank items before the handler runs."""
    resp = client.post("/order", json={"item": "   "})

    assert resp.status_code == 422


# ── GET /order/{id} ───────────────────────────────────────────────────────────


@respx.mock
def test_get_order_returns_order(client):
    respx.get(f"{ORDER_SERVICE_URL}/order/1").mock(
        return_value=httpx.Response(200, json=_stub("espresso", 2.50, 10))
    )

    resp = client.get("/order/1")

    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == 1
    assert data["status"] == "completed"


@respx.mock
def test_get_order_not_found_returns_404(client):
    respx.get(f"{ORDER_SERVICE_URL}/order/999").mock(return_value=httpx.Response(404))

    resp = client.get("/order/999")

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Order not found"
