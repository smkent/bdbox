"""bdbox parameter panel FastAPI app."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from bdbox.console import log
from bdbox.dispatch import Event
from bdbox.errors import InternalError
from bdbox.protocol import (
    ModelParamsState,
    ModelResetParamsMessage,
    ModelSetParamMessage,
    ModelSetPresetMessage,
)
from bdbox.serializer import serializer

if TYPE_CHECKING:
    from bdbox.model.parameters import Params
    from bdbox.protocol import BrowserMessage


@dataclass
class ViewState:
    rerender_event: Event = field(
        default_factory=lambda: Event(name="rerender_event"),
        init=False,
        repr=False,
    )
    model_class: type[Params] | None = None
    params: ModelParamsState = field(default_factory=ModelParamsState)

    def handle_model_message(self, msg: BrowserMessage) -> None:
        if isinstance(msg, ModelSetParamMessage):
            self.params.overrides[msg.field] = msg.value
            self.rerender_event.set()
            log.debug(f"Parameter updated: {msg.field} = {msg.value}")
        elif isinstance(msg, ModelSetPresetMessage):
            if self.model_class:
                for preset in self.model_class.presets:
                    if preset.name == msg.preset:
                        self.params.overrides.clear()
                        self.params.overrides.update(
                            {
                                name: serializer.unstructure(value)
                                for name, value in preset.values.items()
                            }
                        )
                        self.rerender_event.set()
                        log.debug(f"Preset selected: {preset.name}")
                        break
        elif isinstance(msg, ModelResetParamsMessage):
            self.params.overrides.clear()
            self.rerender_event.set()
            log.debug("Parameters reset")
        else:
            raise InternalError(f"Unable to handle message {msg}")
