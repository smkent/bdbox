"""Run action."""

from dataclasses import dataclass

from .action import ModelAction


@dataclass
class RunAction(ModelAction):
    """Run the model without processing collected geometry."""

    def __call__(self) -> None:
        """No-op: model is responsible for its own geometry handling."""
