"""FastAPI REST + WebSocket entry for Grid Pulse."""

import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from gridpulse.config.paths import resolve_events_path
from gridpulse.network import UnknownNetworkError, layout_network, list_networks
from gridpulse.ui.events import load_events
from gridpulse.ui.powerflow_panel import run_powerflow_on_latest
from gridpulse_server.telemetry_hub import TelemetryHub, iter_existing_events


class PowerflowRequest(BaseModel):
    network_id: str = Field(default="case14")
    events_path: str | None = None


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return load_events(path)


def create_app(*, events_path: Path | None = None) -> FastAPI:
    path = events_path if events_path is not None else resolve_events_path()
    hub = TelemetryHub(path)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.events_path = path
        app.state.hub = hub
        hub.start()
        yield
        await hub.stop()

    app = FastAPI(title="Grid Pulse", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/events")
    def events(limit: int = 500) -> dict[str, Any]:
        """Return recent Stage 6 JSONL events for history scrubbing."""
        cap = max(1, min(int(limit), 2000))
        rows = _load_jsonl(Path(app.state.events_path))
        return {"events": rows[-cap:], "path": str(app.state.events_path)}

    @app.get("/networks")
    def networks() -> dict[str, list[str]]:
        return {"networks": list_networks()}

    @app.get("/networks/{network_id}/topology")
    def topology(network_id: str, seed: int = 42, algorithm: str = "spring") -> dict[str, Any]:
        if algorithm not in {"spring", "kamada_kawai"}:
            raise HTTPException(status_code=400, detail="algorithm must be spring or kamada_kawai")
        try:
            return layout_network(network_id, seed=seed, algorithm=algorithm)  # type: ignore[arg-type]
        except UnknownNetworkError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/powerflow")
    def powerflow(body: PowerflowRequest) -> dict[str, Any]:
        ev_path = Path(body.events_path) if body.events_path else app.state.events_path
        events = _load_jsonl(Path(ev_path))
        try:
            result = run_powerflow_on_latest(events, network=body.network_id)
        except UnknownNetworkError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return result

    @app.websocket("/ws/telemetry")
    async def ws_telemetry(ws: WebSocket) -> None:
        await hub.connect(ws)
        try:
            async for event in iter_existing_events(Path(app.state.events_path)):
                await ws.send_text(json.dumps({"type": "telemetry", "event": event}))
            await ws.send_text(json.dumps({"type": "catchup_done"}))
            while True:
                # Keep the socket alive; server pushes via hub. Optional client pings.
                msg = await ws.receive_text()
                if msg.strip().lower() in {"ping", '{"type":"ping"}'}:
                    await ws.send_text(json.dumps({"type": "pong"}))
        except WebSocketDisconnect:
            hub.disconnect(ws)
        except Exception:
            hub.disconnect(ws)
            raise

    return app


app = create_app()


def main() -> None:
    import uvicorn

    uvicorn.run("gridpulse_server.app:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    main()
