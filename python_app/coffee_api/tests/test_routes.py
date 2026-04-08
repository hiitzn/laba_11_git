"""Integration tests for routes.py — HTTP layer via Flask test client.

All tests use the `client` fixture from conftest.py which spins up
a fresh in-memory database per test function.
"""


# ── GET /drinks/ ──────────────────────────────────────────────────────────────

def test_list_drinks_empty(client):
    resp = client.get("/drinks/")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["status"] == "success"
    assert body["data"] == []


def test_list_drinks_after_create(client):
    client.post("/drinks/", json={"name": "Flat White", "price": 3.5})
    resp = client.get("/drinks/")
    assert len(resp.get_json()["data"]) == 1


def test_list_drinks_ordered_newest_first(client):
    client.post("/drinks/", json={"name": "Americano", "price": 2.0})
    client.post("/drinks/", json={"name": "Ristretto", "price": 3.0})
    data = client.get("/drinks/").get_json()["data"]
    assert data[1]["name"] == "Ristretto"


# ── POST /drinks/ ─────────────────────────────────────────────────────────────

def test_create_drink_success(client):
    resp = client.post("/drinks/", json={"name": "Espresso", "price": 2.5})
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["status"] == "success"
    assert body["data"]["name"] == "Espresso"
    assert body["data"]["price"] == 2.5


def test_create_drink_with_description(client):
    resp = client.post("/drinks/", json={"name": "Latte", "price": 3.5, "description": "Milky"})
    assert resp.status_code == 201
    assert resp.get_json()["data"]["description"] == "Milky"


def test_create_drink_invalid_body(client):
    resp = client.post("/drinks/", data="not-json", content_type="text/plain")
    assert resp.status_code == 400
    assert resp.get_json()["status"] == "error"


def test_create_drink_missing_price(client):
    resp = client.post("/drinks/", json={"name": "Latte"})
    assert resp.status_code == 400


def test_create_drink_missing_name(client):
    resp = client.post("/drinks/", json={"price": 2.0})
    assert resp.status_code == 400


def test_create_drink_invalid_price(client):
    resp = client.post("/drinks/", json={"name": "Latte", "price": -1.0})
    assert resp.status_code == 400


def test_create_drink_zero_price(client):
    resp = client.post("/drinks/", json={"name": "Latte", "price": 0})
    assert resp.status_code == 400


def test_create_drink_duplicate(client):
    client.post("/drinks/", json={"name": "Mocha", "price": 3.0})
    resp = client.post("/drinks/", json={"name": "Mocha", "price": 3.0})
    assert resp.status_code == 409


# ── PUT /drinks/<id> ──────────────────────────────────────────────────────────

def test_update_drink_price(client):
    created = client.post("/drinks/", json={"name": "Latte", "price": 3.0}).get_json()
    drink_id = created["data"]["id"]
    resp = client.put(f"/drinks/{drink_id}", json={"price": 4.5})
    assert resp.status_code == 200
    assert resp.get_json()["data"]["price"] == 4.5


def test_update_drink_description(client):
    created = client.post("/drinks/", json={"name": "Lungo", "price": 2.5}).get_json()
    drink_id = created["data"]["id"]
    resp = client.put(f"/drinks/{drink_id}", json={"description": "Long shot"})
    assert resp.status_code == 200
    assert resp.get_json()["data"]["description"] == "Long shot"


def test_update_drink_not_found(client):
    resp = client.put("/drinks/9999", json={"price": 1.0})
    assert resp.status_code == 404


def test_update_drink_invalid_body(client):
    resp = client.put("/drinks/1", data="bad", content_type="text/plain")
    assert resp.status_code == 400


def test_update_drink_empty_json(client):
    resp = client.put("/drinks/1", json={})
    assert resp.status_code == 400


# ── DELETE /drinks/<id> ───────────────────────────────────────────────────────

def test_delete_drink_success(client):
    created = client.post("/drinks/", json={"name": "Cold Brew", "price": 5.0}).get_json()
    drink_id = created["data"]["id"]
    resp = client.delete(f"/drinks/{drink_id}")
    assert resp.status_code == 200
    assert resp.get_json()["data"]["name"] == "Cold Brew"


def test_delete_drink_removes_from_list(client):
    created = client.post("/drinks/", json={"name": "Nitro", "price": 4.0}).get_json()
    drink_id = created["data"]["id"]
    client.delete(f"/drinks/{drink_id}")
    resp = client.get("/drinks/")
    assert resp.get_json()["data"] == []


def test_delete_drink_not_found(client):
    resp = client.delete("/drinks/9999")
    assert resp.status_code == 404


# ── Response envelope ─────────────────────────────────────────────────────────

def test_response_envelope_success(client):
    resp = client.get("/drinks/")
    body = resp.get_json()
    assert "status" in body
    assert "data" in body
    assert "error" in body
    assert body["error"] == ""


def test_response_envelope_error(client):
    resp = client.delete("/drinks/9999")
    body = resp.get_json()
    assert body["status"] == "error"
    assert body["data"] == {}
    assert body["error"] != ""