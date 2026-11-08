"""Supervise the external gridpulse-simulate process for the web-server control plane."""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
from pathlib import Path
from threading import Lock


class SimulatorSupervisor:
    """Start/stop a simulator subprocess that writes the shared events path."""

    def __init__(
        self,
        *,
        events_path: Path,
        command: list[str] | None = None,
        env: dict[str, str] | None = None,
    ) -> None:
        self.events_path = Path(events_path)
        self._command = list(command) if command is not None else self.default_command()
        self._extra_env = dict(env or {})
        self._proc: subprocess.Popen[str] | None = None
        self._lock = Lock()

    @staticmethod
    def default_command() -> list[str]:
        """Resolve gridpulse-simulate from PATH or known repo venvs."""
        found = shutil.which("gridpulse-simulate")
        if found:
            return [found, "--interval", "1", "--inject-rate", "0.1", "--seed", "42"]
        # Prefer data-simulator editable install next to this monorepo checkout.
        here = Path(__file__).resolve()
        repo = here.parents[3]  # .../web-server/src/gridpulse_server → repo root
        candidates = [
            repo / "data-simulator" / ".venv" / "bin" / "gridpulse-simulate",
            repo / "packages" / "gridpulse" / ".venv" / "bin" / "gridpulse-simulate",
        ]
        for path in candidates:
            if path.is_file() and os.access(path, os.X_OK):
                return [
                    str(path),
                    "--interval",
                    "1",
                    "--inject-rate",
                    "0.1",
                    "--seed",
                    "42",
                ]
        return ["gridpulse-simulate", "--interval", "1", "--inject-rate", "0.1", "--seed", "42"]

    def status(self) -> dict[str, object]:
        with self._lock:
            self._reap_if_dead()
            if self._proc is not None and self._proc.poll() is None:
                return {"status": "running", "pid": self._proc.pid}
            return {"status": "stopped", "pid": None}

    def start(self) -> dict[str, object]:
        with self._lock:
            self._reap_if_dead()
            if self._proc is not None and self._proc.poll() is None:
                return {"status": "running", "pid": self._proc.pid}
            self.events_path.parent.mkdir(parents=True, exist_ok=True)
            env = os.environ.copy()
            env["GRIDPULSE_EVENTS_PATH"] = str(self.events_path)
            env.update(self._extra_env)
            try:
                self._proc = subprocess.Popen(
                    self._command,
                    env=env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                    text=True,
                    start_new_session=True,
                )
            except OSError as exc:
                raise RuntimeError(f"failed to start simulator: {exc}") from exc
            # Brief settle — catch immediate spawn failures
            try:
                code = self._proc.wait(timeout=0.15)
            except subprocess.TimeoutExpired:
                return {"status": "running", "pid": self._proc.pid}
            err = ""
            if self._proc.stderr is not None:
                err = (self._proc.stderr.read() or "").strip()
            self._proc = None
            detail = err or f"simulator exited immediately (code {code})"
            raise RuntimeError(detail)

    def stop(self) -> dict[str, object]:
        with self._lock:
            self._reap_if_dead()
            if self._proc is None or self._proc.poll() is not None:
                self._proc = None
                return {"status": "stopped", "pid": None}
            proc = self._proc
            try:
                os.killpg(proc.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                proc.wait(timeout=2)
            self._proc = None
            return {"status": "stopped", "pid": None}

    def _reap_if_dead(self) -> None:
        if self._proc is not None and self._proc.poll() is not None:
            self._proc = None


def python_for_tests() -> str:
    return sys.executable
