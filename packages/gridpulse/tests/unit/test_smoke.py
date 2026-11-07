"""Stage 0 smoke: package is importable."""

import gridpulse


def test_gridpulse_importable() -> None:
    assert gridpulse.__version__
    assert isinstance(gridpulse.__version__, str)
