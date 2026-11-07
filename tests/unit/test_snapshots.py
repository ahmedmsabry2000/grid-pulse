"""Immutable powerflow snapshot pages: freeze on click, live append does not mutate."""

import copy

from gridpulse.ui.snapshots import append_snapshot, freeze_snapshot


def _events(n: int, *, start: int = 0) -> list[dict]:
    out = []
    for i in range(start, start + n):
        out.append(
            {
                "tick_index": i,
                "gate": {"action": "run", "reason": None},
                "powerflow": {"ran": True, "converged": True, "error": None},
                "anomalies": [],
                "measurements": [
                    {
                        "timestamp": f"2026-01-01T00:00:{i:02d}+00:00",
                        "signal_id": "bus_1_vm_pu",
                        "value": 1.0 + i * 0.001,
                        "quality": "good",
                    },
                    {
                        "timestamp": f"2026-01-01T00:00:{i:02d}+00:00",
                        "signal_id": "bus_2_vm_pu",
                        "value": 0.99 + i * 0.001,
                        "quality": "good",
                    },
                ],
            }
        )
    return out


def test_freeze_snapshot_deep_copies_events_and_result() -> None:
    events = _events(3)
    result = {
        "ok": True,
        "rating_exceedances": [{"signal_id": "line:0"}],
        "ensemble_anomalies": [],
    }
    snap = freeze_snapshot(events, result)
    assert snap["tick_start"] == 0
    assert snap["tick_end"] == 2
    assert snap["n_ticks"] == 3
    assert snap["events"] == events
    assert snap["events"] is not events
    assert snap["events"][0] is not events[0]
    assert snap["result"] == result
    assert snap["result"] is not result
    # Mutating the live stream must not touch the frozen payload
    events.append({"tick_index": 99, "measurements": []})
    result["rating_exceedances"].append({"signal_id": "line:1"})
    assert snap["n_ticks"] == 3
    assert snap["tick_end"] == 2
    assert len(snap["events"]) == 3
    assert len(snap["result"]["rating_exceedances"]) == 1


def test_append_snapshot_grows_list_and_selects_latest() -> None:
    snapshots: list[dict] = []
    first = freeze_snapshot(_events(2), {"ok": True, "rating_exceedances": [], "ensemble_anomalies": []})
    snapshots, index = append_snapshot(snapshots, first)
    assert len(snapshots) == 1
    assert index == 0

    second = freeze_snapshot(
        _events(4),
        {"ok": True, "rating_exceedances": [{"type": "rating_exceedance"}], "ensemble_anomalies": []},
    )
    snapshots, index = append_snapshot(snapshots, second)
    assert len(snapshots) == 2
    assert index == 1
    assert snapshots[0]["n_ticks"] == 2
    assert snapshots[1]["n_ticks"] == 4


def test_live_append_without_click_does_not_mutate_prior_snapshots() -> None:
    live = _events(3)
    snap = freeze_snapshot(
        live,
        {"ok": True, "rating_exceedances": [], "ensemble_anomalies": [{"signal_id": "bus_1_vm_pu"}]},
    )
    snapshots, _ = append_snapshot([], snap)
    frozen = copy.deepcopy(snapshots[0])

    # Simulate live simulator appends without a new Run powerflow click
    live.extend(_events(2, start=3))
    assert snapshots[0] == frozen
    assert len(snapshots[0]["events"]) == 3
    assert snapshots[0]["result"]["ensemble_anomalies"][0]["signal_id"] == "bus_1_vm_pu"
