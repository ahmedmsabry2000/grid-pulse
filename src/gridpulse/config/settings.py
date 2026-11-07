"""Default pipeline settings."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    network: str = "case14"
    z_threshold: float = 3.0
    spike_threshold: float = 0.05


DEFAULT_SETTINGS = Settings()
