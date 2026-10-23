import os
import tempfile

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://mealsense:mealsense@localhost:5432/mealsenseai_test")
os.environ.setdefault("DATA_DIR", tempfile.mkdtemp())
os.environ.setdefault("OLLAMA_URL", "http://127.0.0.1:9")  # SLM offline unless overridden

import pytest
from fastapi.testclient import TestClient

from app.core.db import Base, engine
from app.main import app


@pytest.fixture(scope="session")
def client():
    Base.metadata.drop_all(engine)
    with TestClient(app) as c:
        yield c


@pytest.fixture
def auth(client):
    import uuid
    r = client.post("/api/v1/auth/register",
                    json={"email": f"u{uuid.uuid4().hex[:8]}@test.io", "password": "secret123", "name": "Test"})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}
