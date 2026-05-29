from __future__ import annotations

from contextlib import ExitStack
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from contextlib import AbstractContextManager
    from types import TracebackType

    from bdbox.actions.action import Action


@dataclass
class ActionState:
    """Holds the active action and manages its lifecycle."""

    action: Action | None = None
    acted: bool = False
    stack: ExitStack = field(default_factory=ExitStack, init=False, repr=False)
    render_active: bool = False

    def act_once(self) -> None:
        if self.acted:
            return
        self.acted = True
        self.action_or_run()

    @property
    def action_or_run(self) -> Action:
        from bdbox.actions.run import RunAction  # noqa: PLC0415

        return self.action or RunAction()

    def on_model_render(self) -> AbstractContextManager[None]:
        class OnRender:
            def __enter__(_self) -> None:  # noqa: N805
                if not self.render_active:
                    self.stack.enter_context(
                        self.action_or_run.on_model_render()
                    )
                self.render_active = True
                return

            def __exit__(
                _self,  # noqa: N805
                exc_type: type[BaseException] | None,
                exc_val: BaseException | None,
                exc_tb: TracebackType | None,
            ) -> bool | None:
                if not self.render_active:
                    return None
                self.render_active = False
                return self.stack.__exit__(exc_type, exc_val, exc_tb)

        return OnRender()
