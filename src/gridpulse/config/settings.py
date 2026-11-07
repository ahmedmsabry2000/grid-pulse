"""Default pipeline settings."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    network: str = "case14"
    z_threshold: float = 3.0
    spike_threshold: float = 0.05
    # Historical ensemble (weighted spike + z-score + Isolation Forest)
    ensemble_threshold: float = 0.5
    ensemble_random_state: int = 0


DEFAULT_SETTINGS = Settings()
