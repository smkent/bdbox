from __future__ import annotations

import pytest


@pytest.fixture(scope="session", autouse=True)
def cache_build123d() -> None:
    """Import build123d at session scope for reuse across tests."""
    import build123d  # noqa: F401, PLC0415
