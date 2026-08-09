from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.fixture
def client() -> TestClient:
    app = create_app(Settings(database_url="sqlite+pysqlite:///:memory:", auto_create_schema=True))
    with TestClient(app) as test_client:
        yield test_client
