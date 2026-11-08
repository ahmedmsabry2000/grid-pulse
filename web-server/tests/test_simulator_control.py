"""Simulator start/stop/status control plane."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from gridpulse_server.app import create_app
from gridpulse_server.simulator_control import SimulatorSupervisor


@pytest.fixture()
def events_file(tmp_path: Path) -> Path:
    path = tmp_path / "events.jsonl"
    path.write_text("", encoding="utf-8")
    return path


@pytest.fixture()
def fake_sim_script(tmp_path: Path) -> Path:
    """Long-lived fake simulator that appends a heartbeat line until killed."""
    script = tmp_path / "fake_sim.py"
    script.write_text(
        "import os, sys, time\n"
        "path = os.environ['GRIDPULSE_EVENTS_PATH']\n"
        "while True:\n"
        "    with open(path, 'a', encoding='utf-8') as f:\n"
        "        f.write('{\"tick_index\":0}\\n')\n"
        "        f.flush()\n"
        "    time.sleep(0.05)\n",
        encoding="utf-8",
    )
    return script


@pytest.fixture()
def client(events_file: Path, fake_sim_script: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("GRIDPULSE_EVENTS_PATH", str(events_file))
    supervisor = SimulatorSupervisor(
        events_path=events_file,
        command=[sys_executable(), str(fake_sim_script)],
    )
    application = create_app(events_path=events_file, simulator=supervisor)
    with TestClient(application) as c:
        yield c
    supervisor.stop()


def sys_executable() -> str:
    import sys

    return sys.executable


def test_simulator_status_stopped_by_default(client: TestClient) -> None:
    r = client.get("/simulator")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "stopped"
    assert body.get("pid") is None


def test_simulator_start_stop_cycle(client: TestClient, events_file: Path) -> None:
    start = client.post("/simulator/start")
    assert start.status_code == 200
    assert start.json()["status"] == "running"
    assert isinstance(start.json()["pid"], int)

    status = client.get("/simulator")
    assert status.json()["status"] == "running"

    # Idempotent start while running
    again = client.post("/simulator/start")
    assert again.status_code == 200
    assert again.json()["status"] == "running"

    stop = client.post("/simulator/stop")
    assert stop.status_code == 200
    assert stop.json()["status"] == "stopped"

    final = client.get("/simulator")
    assert final.json()["status"] == "stopped"

    # stop while already stopped is ok
    stop2 = client.post("/simulator/stop")
    assert stop2.status_code == 200
    assert stop2.json()["status"] == "stopped"


def test_simulator_start_failure_is_plain_text_error(
    events_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GRIDPULSE_EVENTS_PATH", str(events_file))
    supervisor = SimulatorSupervisor(
        events_path=events_file,
        command=["/nonexistent/gridpulse-simulate-missing"],
    )
    application = create_app(events_path=events_file, simulator=supervisor)
    with TestClient(application) as c:
        r = c.post("/simulator/start")
        assert r.status_code == 500
        # FastAPI detail is a plain string for operators
        assert isinstance(r.json()["detail"], str)
        assert "JSON" not in r.json()["detail"]
    supervisor.stop()
