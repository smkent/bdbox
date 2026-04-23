"""bdbox harness CLI entry point."""

from __future__ import annotations

from .runner.harness import ModelHarness


def main() -> None:
    """Run the bdbox CLI."""
    ModelHarness()()


if __name__ == "__main__":
    main()
