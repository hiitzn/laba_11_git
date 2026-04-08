"""Shared pytest fixtures for Coffee Menu API tests."""

import pytest

from app import create_app
from models import Database
from schemas import CreateDrinkSchema, UpdateDrinkSchema
from services import DrinkService


@pytest.fixture
def db():
    database = Database(":memory:")
    database.init_schema()
    return database


@pytest.fixture
def svc(db):
    return DrinkService(db)


@pytest.fixture
def make_drink(svc):
    """Factory: call make_drink() to insert a drink and get its dict back."""
    def _factory(name="Espresso", price=2.5, description=None) -> dict:
        return svc.create(CreateDrinkSchema(name=name, price=price, description=description))
    return _factory


@pytest.fixture
def update_drink(svc):
    """Factory: call update_drink(id, price=..., description=...)."""
    def _factory(drink_id, **kw) -> dict:
        return svc.update(drink_id, UpdateDrinkSchema(**kw))
    return _factory


@pytest.fixture
def client():
    """Flask test client backed by a fresh in-memory database."""
    app = create_app({"DATABASE_URL": ":memory:", "TESTING": True})
    with app.test_client() as c:
        yield c