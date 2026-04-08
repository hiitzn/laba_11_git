"""Unit tests for models.py and schemas.py.

Pure logic — no HTTP, no Flask, no shared state between tests.
"""

from datetime import datetime

import pytest

from models import Database, Drink, utc_now
from schemas import validate_create, validate_update


# ── utc_now ───────────────────────────────────────────────────────────────────

def test_utc_now_returns_string():
    assert isinstance(utc_now(), str)


def test_utc_now_is_valid_iso8601():
    datetime.fromisoformat(utc_now())  # raises on bad format


def test_utc_now_is_utc():
    assert utc_now().endswith("+00:00")


# ── Drink dataclass ───────────────────────────────────────────────────────────

def _make_drink(**kw) -> Drink:
    return Drink(**{"id": 1, "name": "X", "price": 1.0,
                    "description": None, "created_at": "t", "updated_at": "t", **kw})


def test_drink_to_dict_has_all_keys():
    assert _make_drink().to_dict().keys() == {
        "id", "name", "price", "description", "created_at", "updated_at"
    }


def test_drink_to_dict_none_description():
    assert _make_drink(description=None).to_dict()["description"] is None


def test_drink_from_row_roundtrip(db):
    ts = utc_now()
    with db.connect() as conn:
        conn.execute(
            "INSERT INTO drinks (name, description, price, created_at, updated_at)"
            " VALUES (?,?,?,?,?)", ("Latte", "Milky", 4.0, ts, ts)
        )
        row = conn.execute("SELECT * FROM drinks").fetchone()
    d = Drink.from_row(row)
    assert d.name == "Latte"
    assert d.price == 4.0
    assert d.description == "Milky"


# ── Database ──────────────────────────────────────────────────────────────────

def test_init_schema_idempotent(db):
    db.init_schema()  # second call must not raise


def test_connect_commits(db):
    ts = utc_now()
    with db.connect() as conn:
        conn.execute(
            "INSERT INTO drinks (name, description, price, created_at, updated_at)"
            " VALUES (?,?,?,?,?)", ("A", None, 1.0, ts, ts)
        )
    with db.connect() as conn:
        count = conn.execute("SELECT COUNT(*) FROM drinks").fetchone()[0]
    assert count == 1


def test_connect_rollback_on_error(db):
    with pytest.raises(RuntimeError):
        with db.connect() as conn:
            conn.execute(
                "INSERT INTO drinks (name, description, price, created_at, updated_at)"
                " VALUES (?,?,?,?,?)", ("B", None, 1.0, utc_now(), utc_now())
            )
            raise RuntimeError("forced")
    with db.connect() as conn:
        count = conn.execute("SELECT COUNT(*) FROM drinks").fetchone()[0]
    assert count == 0


# ── validate_create — happy path ──────────────────────────────────────────────

def test_validate_create_minimal_valid():
    schema, err = validate_create({"name": "X", "price": 1.0})
    assert err is None
    assert schema.name == "X"
    assert schema.price == 1.0


def test_validate_create_int_price_coerced_to_float():
    schema, _ = validate_create({"name": "X", "price": 3})
    assert isinstance(schema.price, float)


def test_validate_create_name_stripped():
    schema, _ = validate_create({"name": "  Latte  ", "price": 1.0})
    assert schema.name == "Latte"


def test_validate_create_description_stripped():
    schema, _ = validate_create({"name": "X", "price": 1.0, "description": "  Bold  "})
    assert schema.description == "Bold"


def test_validate_create_whitespace_description_becomes_none():
    schema, _ = validate_create({"name": "X", "price": 1.0, "description": "   "})
    assert schema.description is None


def test_validate_create_absent_description_is_none():
    schema, _ = validate_create({"name": "X", "price": 1.0})
    assert schema.description is None


def test_validate_create_name_at_max_length_ok():
    _, err = validate_create({"name": "A" * 100, "price": 1.0})
    assert err is None


# ── validate_create — name errors ─────────────────────────────────────────────

def test_validate_create_missing_name():
    _, err = validate_create({"price": 1.0})
    assert err is not None


def test_validate_create_empty_name():
    _, err = validate_create({"name": "", "price": 1.0})
    assert err is not None


def test_validate_create_whitespace_name():
    _, err = validate_create({"name": "  ", "price": 1.0})
    assert err is not None


def test_validate_create_non_string_name():
    _, err = validate_create({"name": 42, "price": 1.0})
    assert err is not None


def test_validate_create_name_too_long():
    _, err = validate_create({"name": "A" * 101, "price": 1.0})
    assert err is not None


# ── validate_create — price errors ────────────────────────────────────────────

def test_validate_create_missing_price():
    _, err = validate_create({"name": "X"})
    assert err is not None


def test_validate_create_zero_price():
    _, err = validate_create({"name": "X", "price": 0})
    assert err is not None


def test_validate_create_negative_price():
    _, err = validate_create({"name": "X", "price": -0.01})
    assert err is not None


def test_validate_create_string_price():
    _, err = validate_create({"name": "X", "price": "free"})
    assert err is not None


def test_validate_create_bool_price_rejected():
    _, err = validate_create({"name": "X", "price": True})
    assert err is not None


# ── validate_create — description errors ──────────────────────────────────────

def test_validate_create_non_string_description():
    _, err = validate_create({"name": "X", "price": 1.0, "description": 99})
    assert err is not None


def test_validate_create_description_too_long():
    _, err = validate_create({"name": "X", "price": 1.0, "description": "D" * 501})
    assert err is not None


# ── validate_update ───────────────────────────────────────────────────────────

def test_validate_update_price_only():
    schema, err = validate_update({"price": 5.0})
    assert err is None
    assert schema.price == 5.0


def test_validate_update_description_only():
    schema, err = validate_update({"description": "Updated"})
    assert err is None
    assert schema.description == "Updated"


def test_validate_update_both_fields():
    _, err = validate_update({"price": 3.0, "description": "New"})
    assert err is None


def test_validate_update_empty_dict():
    _, err = validate_update({})
    assert err is not None


def test_validate_update_unrecognised_fields_only():
    _, err = validate_update({"color": "black"})
    assert err is not None


def test_validate_update_invalid_price():
    _, err = validate_update({"price": -1})
    assert err is not None


def test_validate_update_bool_price_rejected():
    _, err = validate_update({"price": False})
    assert err is not None


def test_validate_update_non_string_description():
    _, err = validate_update({"description": 123})
    assert err is not None


def test_validate_update_whitespace_description_becomes_none():
    schema, err = validate_update({"description": "  "})
    assert err is None
    assert schema.description is None


def test_validate_update_description_too_long():
    _, err = validate_update({"description": "X" * 501})
    assert err is not None