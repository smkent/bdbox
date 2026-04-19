"""bdbox harness CLI entry point."""

from .runner.harness import ModelHarness


def main() -> None:
    """Run the bdbox CLI."""
    ModelHarness().run_model()


if __name__ == "__main__":
    main()
