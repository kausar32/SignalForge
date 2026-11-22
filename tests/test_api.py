"""API tests. Skipped automatically when the web/database dependencies are not installed."""

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("sqlalchemy")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from app.api import create_app  # noqa: E402


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_PROVIDER", "synthetic")
    app = create_app(f"sqlite:///{tmp_path / 'test.db'}", init_schema=True)
    return TestClient(app)


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_assets_lists_the_five_tracked_assets(client):
    symbols = {a["symbol"] for a in client.get("/assets").json()}
    assert symbols == {"NIFTY", "SENSEX", "BANKNIFTY", "GOLD", "BITCOIN"}


def test_subscription_roundtrip(client):
    assert client.put("/users/1/subscriptions/gold", json={"channels": ["in_app"]}).status_code == 200
    assets = {s["asset"] for s in client.get("/users/1/subscriptions").json()}
    assert "GOLD" in assets
    assert client.delete("/users/1/subscriptions/GOLD").json() == {"removed": True}


def test_bad_inputs_are_rejected(client):
    assert client.put("/users/1/subscriptions/DOGE", json={}).status_code == 404
    assert client.put("/users/1/subscriptions/GOLD", json={"channels": ["fax"]}).status_code == 422
    assert client.get("/users/999/subscriptions").status_code == 404


def test_pipeline_endpoint_runs(client):
    body = client.post("/pipeline/run").json()
    assert set(body) == {"signals_created", "notifications", "errors"}
