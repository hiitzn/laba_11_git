import pytest
from fastapi.testclient import TestClient

from main import create_app


@pytest.fixture()
def client():
    """Fresh app + TestClient per test; lifespan runs automatically."""
    with TestClient(create_app()) as c:
        yield c