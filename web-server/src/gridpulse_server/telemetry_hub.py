"""Tail events.jsonl and fan out lines to WebSocket subscribers."""

import asyncio
import json
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from fastapi import WebSocket


class TelemetryHub:
    """Broadcast new JSONL event lines to connected WebSocket clients."""

    def __init__(self, path: Path, *, poll_interval: float = 0.25) -> None:
        self.path = path
        self.poll_interval = poll_interval
        self._clients: set[WebSocket] = set()
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()

    @property
    def client_count(self) -> int:
        return len(self._clients)

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._clients.add(ws)

    def disconnect(self, ws: WebSocket) -> None:
        self._clients.discard(ws)

    async def broadcast(self, payload: dict[str, Any]) -> None:
        dead: list[WebSocket] = []
        text = json.dumps(payload)
        for ws in list(self._clients):
            try:
                await ws.send_text(text)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

    async def _tail_loop(self) -> None:
        offset = 0
        if self.path.is_file():
            offset = self.path.stat().st_size
        while not self._stop.is_set():
            try:
                if self.path.is_file():
                    size = self.path.stat().st_size
                    if size < offset:
                        offset = 0  # truncated / rotated
                    if size > offset:
                        with self.path.open("r", encoding="utf-8") as fh:
                            fh.seek(offset)
                            chunk = fh.read()
                            offset = fh.tell()
                        for line in chunk.splitlines():
                            line = line.strip()
                            if not line:
                                continue
                            try:
                                event = json.loads(line)
                            except json.JSONDecodeError:
                                continue
                            await self.broadcast({"type": "telemetry", "event": event})
            except OSError:
                pass
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=self.poll_interval)
            except TimeoutError:
                continue

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._stop.clear()
            self._task = asyncio.create_task(self._tail_loop())

    async def stop(self) -> None:
        self._stop.set()
        if self._task is not None:
            await self._task
            self._task = None


async def iter_existing_events(path: Path, *, max_lines: int = 200) -> AsyncIterator[dict[str, Any]]:
    """Yield up to the last ``max_lines`` parsed JSONL events (startup catch-up)."""
    if not path.is_file():
        return
    lines = path.read_text(encoding="utf-8").splitlines()
    for line in lines[-max_lines:]:
        line = line.strip()
        if not line:
            continue
        try:
            yield json.loads(line)
        except json.JSONDecodeError:
            continue
