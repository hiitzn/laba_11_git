"""Unit tests for services.py — DrinkService in isolation (no HTTP, no Flask)."""

import pytest

from services import DrinkAlreadyExistsError, DrinkNotFoundError


# ── get_all ───────────────────────────────────────────────────────────────────

def test_get_all_empty(svc):
    assert svc.get_all() == []


def test_get_all_returns_all(svc, make_drink):
    make_drink("A")
    make_drink("B")
    assert len(svc.get_all()) == 2


# ── create ────────────────────────────────────────────────────────────────────

def test_create_returns_dict_with_id(make_drink):
    d = make_drink("Latte", 4.0)
    assert "id" in d
    assert d["id"] is not None
    assert d["name"] == "Latte"
    assert d["price"] == 4.0


def test_create_timestamps_present(make_drink):
    d = make_drink()
    assert d["created_at"] is not None
    assert d["updated_at"] is not None


def test_create_duplicate_raises(make_drink):
    make_drink("Mocha")
    with pytest.raises(DrinkAlreadyExistsError):
        make_drink("Mocha")


def test_create_with_description(make_drink):
    d = make_drink("Cappuccino", 3.5, description="With foam")
    assert d["description"] == "With foam"


def test_create_without_description(make_drink):
    d = make_drink("Espresso", 2.5)
    assert d["description"] is None


# ── update ────────────────────────────────────────────────────────────────────

def test_update_price(make_drink, update_drink):
    d = make_drink("Ristretto", 3.0)
    result = update_drink(d["id"], price=5.0)
    assert result["price"] == 5.0


def test_update_description(make_drink, update_drink):
    d = make_drink("Cortado", 3.2)
    result = update_drink(d["id"], description="With milk")
    assert result["description"] == "With milk"


def test_update_price_preserves_description(make_drink, update_drink):
    d = make_drink("V60", 4.0, description="Pour over")
    result = update_drink(d["id"], price=4.5)
    assert result["description"] == "Pour over"


def test_update_description_preserves_price(make_drink, update_drink):
    d = make_drink("Lungo", 3.0)
    result = update_drink(d["id"], description="Long shot")
    assert result["price"] == 3.0


def test_update_updated_at_changes(make_drink, update_drink):
    d = make_drink("Macchiato", 3.0)
    result = update_drink(d["id"], price=4.0)
    assert result["updated_at"] >= d["updated_at"]


def test_update_not_found_raises(update_drink):
    with pytest.raises(DrinkNotFoundError):
        update_drink(9999, price=1.0)


# ── delete ────────────────────────────────────────────────────────────────────

def test_delete_returns_drink_data(svc, make_drink):
    d = make_drink("Cold Brew", 5.0)
    deleted = svc.delete(d["id"])
    assert deleted["id"] == d["id"]
    assert deleted["name"] == "Cold Brew"


def test_delete_removes_from_db(svc, make_drink):
    d = make_drink("Affogato", 6.0)
    svc.delete(d["id"])
    assert svc.get_all() == []


def test_delete_not_found_raises(svc):
    with pytest.raises(DrinkNotFoundError):
        svc.delete(9999)


def test_delete_only_target_drink(svc, make_drink):
    make_drink("A", 1.0)
    b = make_drink("B", 2.0)
    svc.delete(b["id"])
    remaining = svc.get_all()
    assert len(remaining) == 1
    assert remaining[0]["name"] == "A"