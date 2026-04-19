"""Run action."""

from dataclasses import dataclass

from .action import Action


@dataclass
class RunAction(Action):
    """Run the model without processing collected geometry."""

    def __call__(self) -> None:
        """No-op: model is responsible for its own geometry handling."""
