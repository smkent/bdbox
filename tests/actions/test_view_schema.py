from __future__ import annotations

import sys
import time
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass, field
from functools import cached_property, partial
from pathlib import Path  # noqa: TC003
from queue import Empty, Queue
from threading import Thread
from typing import TYPE_CHECKING, Any

import pytest
from starlette.testclient import TestClient

from bdbox.console import log
from bdbox.dispatch import Event, dispatch
from bdbox.protocol import (
    BrowserMessage,
    ModelDetailsMessage,
    ModelSetParamMessage,
    ModelSetPresetMessage,
    ServerMessage,
)
from bdbox.runner.harness import ModelHarness
from tests.utils import Models

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence
    from types import TracebackType
    from unittest.mock import MagicMock

    from starlette.testclient import WebSocketTestSession

    from bdbox.view.ui.server import UIServer


pytestmark = pytest.mark.usefixtures("mock_ocp_cad_viewer_start")


class SchemaModels:
    DIR = Models.DIR / "schema"

    START = DIR / "model_start.py"
    REMOVE_PARAMETERS = DIR / "model_remove_parameters.py"


@dataclass
class UIServerClient:
    ui_server: UIServer
    stack: ExitStack = field(default_factory=ExitStack, init=False)
    ws: WebSocketTestSession = field(init=False)
    queue: Queue[dict[str, Any] | BaseException] = field(default_factory=Queue)

    def __enter__(self) -> Self:
        client = self.stack.enter_context(TestClient(self.ui_server.app))
        self.ws = self.stack.enter_context(client.websocket_connect("/ws"))
        self.run_receive_queue()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool | None:
        return self.stack.__exit__(exc_type, exc_val, exc_tb)

    def run_receive_queue(self) -> None:
        def _receive() -> None:
            while True:
                try:
                    msg = self.ws.receive_json()
                except BaseException as e:  # noqa: BLE001
                    self.queue.put(e)
                    break
                self.queue.put(msg)

        Thread(target=_receive, daemon=True).start()

    def send_message(self, message: BrowserMessage) -> None:
        self.ws.send_json(message.to_dict())

    def get_message(self, timeout: float = 5.0) -> ServerMessage:
        try:
            item = self.queue.get(timeout=timeout)
        except Empty:
            raise TimeoutError(
                f"No websocket message received within {timeout}s"
            ) from None
        if isinstance(item, BaseException):
            raise item
        msg = ServerMessage.from_dict(item)
        log.debug("Received: %s", msg)
        return msg


@dataclass
class UIServerManager:
    mock_server_start: MagicMock
    server_ready: Event = field(
        default_factory=lambda: Event(name="server_ready"), init=False
    )

    def __post_init__(self) -> None:
        def _started(*_: Any, **__: Any) -> None:
            self.server_ready.set()

        self.mock_server_start.side_effect = _started

    @property
    def ui_server(self) -> UIServer:
        assert self.server_ready.wait(timeout=5.0), "server never started"
        return self.mock_server_start.call_args[0][0]

    @contextmanager
    def run_model_client(
        self, model_argv: Sequence[Path | str]
    ) -> Iterator[UIServerClient]:
        model_argv = [*model_argv, "--server-port", "0"]

        def _run_harness() -> None:
            ModelHarness(model_argv)()

        thread = Thread(target=_run_harness, daemon=True, name="test-harness")
        thread.start()
        try:
            with UIServerClient(self.ui_server) as client:
                yield client
        finally:
            dispatch.exit.set()
            thread.join(timeout=5.0)


@dataclass
class ViewSession:
    tmp_path: Path = field(kw_only=True)
    ui_server: UIServerManager = field(kw_only=True)

    start_model: Path
    model_argv: Sequence[Path | str] = field(default_factory=list)

    stack: ExitStack = field(default_factory=ExitStack, init=False)
    client: UIServerClient = field(init=False)

    @cached_property
    def model_file(self) -> Path:
        return self.tmp_path / "model.py"

    def __post_init__(self) -> None:
        self.model_file.write_text(self.start_model.read_text())

    def __enter__(self) -> Self:
        self.client = self.stack.enter_context(
            self.ui_server.run_model_client(
                [self.model_file, "view", *self.model_argv]
            )
        )
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool | None:
        return self.stack.__exit__(exc_type, exc_val, exc_tb)

    def get_message(self, timeout: float = 5.0) -> ServerMessage:
        deadline = time.monotonic() + timeout
        while (remaining := deadline - time.monotonic()) > 0:
            try:
                msg = self.client.get_message(remaining)
                log.debug("Received: %s", msg)
            except TimeoutError:
                break
            return msg
        raise TimeoutError("No message received")

    def wait_for_model_details_message(
        self, timeout: float = 5.0
    ) -> ModelDetailsMessage:
        while msg := self.client.get_message(timeout=timeout):
            if isinstance(msg, ModelDetailsMessage):
                return msg
        raise RuntimeError("No matching message received")


@pytest.fixture
def ui_server(mock_server_start: MagicMock) -> UIServerManager:
    return UIServerManager(mock_server_start)


@pytest.fixture
def view_session(tmp_path: Path, ui_server: UIServerManager) -> partial:
    return partial(ViewSession, tmp_path=tmp_path, ui_server=ui_server)


def test_reload_removes_overrides_for_removed_parameters(
    view_session: partial,
) -> None:
    with view_session(SchemaModels.START) as session:
        initial = session.wait_for_model_details_message()
        assert initial.params.overrides == {}

        session.client.send_message(ModelSetPresetMessage(preset="custom"))
        for _attempt in range(2):
            after_override = session.wait_for_model_details_message()
            if after_override.params.overrides == {}:
                # Skip stray initial render model details message
                continue
            assert after_override.params.overrides == {
                "width": 50.0,
                "length": 50.0,
                "height": 50.0,
                "sub_options": {
                    "color": {"code": "ffffff", "alpha": 0xFF},
                    "first": 3,
                    "several": [1138, 2187],
                },
            }
            break
        else:
            raise RuntimeError("Attempts exceeded")

        session.client.send_message(
            ModelSetParamMessage(field="width", value=25.0)
        )
        after_override = session.wait_for_model_details_message()
        assert after_override.params.overrides == {
            "width": 25.0,
            "length": 50.0,
            "height": 50.0,
            "sub_options": {
                "color": {"code": "ffffff", "alpha": 0xFF},
                "first": 3,
                "several": [1138, 2187],
            },
        }

        session.model_file.write_text(
            SchemaModels.REMOVE_PARAMETERS.read_text()
        )
        after_reload = session.wait_for_model_details_message()
        assert after_reload.params.overrides == {
            "width": 25.0,
            "sub_options": {"several": [1138, 2187]},
        }
