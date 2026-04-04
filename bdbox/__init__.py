"""build123d utilities box."""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as import_version

try:
    version = import_version(__name__)
except PackageNotFoundError:  # pragma: no cover
    version = "0.0.0"
