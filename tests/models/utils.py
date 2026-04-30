import sys
from types import ModuleType
from unittest.mock import MagicMock


class SnapshotMock(MagicMock):
    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__} name='{self._extract_mock_name()}'>"
        )


def _import_build123d() -> ModuleType | MagicMock:
    if "build123d" in sys.modules:
        import build123d  # noqa: PLC0415
    else:
        sys.modules["build123d"] = SnapshotMock(name="b123d")
        import build123d  # noqa: PLC0415
    return build123d


build123d = _import_build123d()
