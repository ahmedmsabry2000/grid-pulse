"""Fixed events JSONL path resolution."""

import os
from collections.abc import Mapping
from pathlib import Path

DEFAULT_EVENTS_FILENAME = "events.jsonl"
ENV_EVENTS_PATH = "GRIDPULSE_EVENTS_PATH"


def resolve_events_path(
    *,
    env: Mapping[str, str] | None = None,
    cwd: Path | None = None,
) -> Path:
    """Resolve the shared events file path.

    Default: ``events.jsonl`` under ``cwd`` (process cwd).
    Override: non-empty ``GRIDPULSE_EVENTS_PATH`` only.
    """
    environ = os.environ if env is None else env
    raw = environ.get(ENV_EVENTS_PATH, "")
    if raw is not None and str(raw).strip():
        return Path(str(raw).strip()).expanduser()
    base = Path.cwd() if cwd is None else Path(cwd)
    return base / DEFAULT_EVENTS_FILENAME
