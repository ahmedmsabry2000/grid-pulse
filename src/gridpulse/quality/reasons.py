"""Quality / gate reason codes.

F4 (severity tiers) is deferred — enum room only; all failures hard-skip today.
"""

from enum import Enum


class ReasonCode(str, Enum):
    MISSING = "missing"
    BAD_QUALITY = "bad_quality"
    OUT_OF_RANGE = "out_of_range"
    RATE_OF_CHANGE = "rate_of_change"
    TOPOLOGY = "topology"
    # Reserved for future severity / warn tiers (F4) — not used yet:
    # WARN_OUT_OF_RANGE = "warn_out_of_range"
