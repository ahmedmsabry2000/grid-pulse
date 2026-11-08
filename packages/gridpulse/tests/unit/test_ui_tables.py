"""Flattened operator tables for Streamlit (no nested dict cells)."""

from gridpulse.ui.tables import flatten_anomaly_rows, flatten_ensemble_rows


def test_flatten_ensemble_rows_expands_member_scores() -> None:
    rows = flatten_ensemble_rows(
        [
            {
                "type": "measurement_ensemble",
                "signal_id": "bus_2_vm_pu",
                "score": 0.7,
                "detail": "hit",
                "member_scores": {"spike": 0.9, "zscore": 0.4, "iforest": 0.6},
            }
        ]
    )
    assert len(rows) == 1
    assert rows[0]["signal"] == "bus_2_vm_pu"
    assert rows[0]["score"] == 0.7
    assert rows[0]["detail"] == "hit"
    assert "member_scores" not in rows[0]
    assert isinstance(rows[0]["members"], str)
    assert "spike=0.900" in rows[0]["members"]
    assert "zscore=0.400" in rows[0]["members"]


def test_flatten_anomaly_rows_keeps_scalar_columns() -> None:
    rows = flatten_anomaly_rows(
        [
            {
                "type": "measurement_spike",
                "signal_id": "bus_1_vm_pu",
                "score": 0.95,
                "detail": "spike",
                "value": 1.2,
            },
            {
                "type": "rating_exceedance",
                "signal_id": "line:3",
                "quantity": "loading_percent",
                "value": 110,
                "limit": 100,
                "margin": -10,
                "score": 1.0,
                "detail": "over",
            },
        ]
    )
    assert rows[0] == {
        "type": "measurement_spike",
        "signal": "bus_1_vm_pu",
        "score": 0.95,
        "detail": "spike",
        "value": 1.2,
        "quantity": None,
        "limit": None,
        "margin": None,
    }
    assert rows[1]["signal"] == "line:3"
    assert rows[1]["quantity"] == "loading_percent"
    assert rows[1]["margin"] == -10
    assert all(not isinstance(v, dict) for row in rows for v in row.values())
