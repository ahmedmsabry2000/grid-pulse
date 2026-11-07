"""Fixed events path resolution — no UI prompt."""

from pathlib import Path

from gridpulse.config.paths import DEFAULT_EVENTS_FILENAME, resolve_events_path


def test_resolve_events_path_defaults_to_cwd_events_jsonl(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("GRIDPULSE_EVENTS_PATH", raising=False)
    assert resolve_events_path() == tmp_path / DEFAULT_EVENTS_FILENAME
    assert DEFAULT_EVENTS_FILENAME == "events.jsonl"


def test_resolve_events_path_respects_env_override(tmp_path: Path, monkeypatch) -> None:
    override = tmp_path / "custom" / "stream.jsonl"
    monkeypatch.setenv("GRIDPULSE_EVENTS_PATH", str(override))
    assert resolve_events_path() == override


def test_resolve_events_path_accepts_explicit_env_mapping(tmp_path: Path) -> None:
    override = tmp_path / "alt.jsonl"
    got = resolve_events_path(env={"GRIDPULSE_EVENTS_PATH": str(override)}, cwd=tmp_path)
    assert got == override
    # Empty / whitespace env falls back to cwd default
    got2 = resolve_events_path(env={"GRIDPULSE_EVENTS_PATH": "  "}, cwd=tmp_path)
    assert got2 == tmp_path / "events.jsonl"


def test_ui_does_not_prompt_for_path() -> None:
    """app.py must not use text_input / file_uploader for the events path."""
    app_src = Path(__file__).resolve().parents[2] / "src" / "gridpulse" / "ui" / "app.py"
    text = app_src.read_text(encoding="utf-8")
    assert "text_input" not in text
    assert "file_uploader" not in text
    assert "resolve_events_path" in text
