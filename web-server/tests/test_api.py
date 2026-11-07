"""API smoke tests for web-server."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from gridpulse_server.app import create_app


@pytest.fixture()
def events_file(tmp_path: Path) -> Path:
    path = tmp_path / "events.jsonl"
    tick = {
        "tick_index": 0,
        "timestamp": "2024-01-01T00:00:00",
        "measurements": [
            {
                "timestamp": "2024-01-01T00:00:00",
                "signal_id": "load_0_p_mw",
                "value": 1.0,
                "quality": "good",
            }
        ],
        "gate": {"action": "run"},
        "powerflow": {"ran": True, "converged": True},
        "anomalies": [],
    }
    path.write_text(json.dumps(tick) + "\n", encoding="utf-8")
    return path


@pytest.fixture()
def client(events_file: Path):
    application = create_app(events_path=events_file)
    with TestClient(application) as c:
        yield c


def test_health(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_list_networks(client: TestClient) -> None:
    r = client.get("/networks")
    assert r.status_code == 200
    nets = r.json()["networks"]
    assert "case14" in nets


def test_topology_case14(client: TestClient) -> None:
    r = client.get("/networks/case14/topology")
    assert r.status_code == 200
    body = r.json()
    assert body["network_id"] == "case14"
    assert body["buses"]["type"] == "FeatureCollection"
    assert len(body["buses"]["features"]) == 14
    assert body["lines"]["type"] == "FeatureCollection"
    assert len(body["lines"]["features"]) > 0


def test_topology_unknown(client: TestClient) -> None:
    r = client.get("/networks/not-a-net/topology")
    assert r.status_code == 404


def test_powerflow_post(client: TestClient) -> None:
    r = client.post("/powerflow", json={"network_id": "case14"})
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert "gate" in body
    assert "rating_exceedances" in body
    assert "ensemble_anomalies" in body


def test_ws_telemetry_catchup(client: TestClient) -> None:
    with client.websocket_connect("/ws/telemetry") as ws:
        msg = json.loads(ws.receive_text())
        assert msg["type"] == "telemetry"
        assert "event" in msg
        done = json.loads(ws.receive_text())
        assert done["type"] == "catchup_done"
