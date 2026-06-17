"""Server WebSocket and message handler tests."""

from __future__ import annotations

import sys
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from unittest.mock import patch
from uuid import UUID

import pytest
from starlette.testclient import TestClient

from bdbox.errors import InternalError
from bdbox.model.field_factories import Float, Int
from bdbox.model.model import Model
from bdbox.model.parameters import Params
from bdbox.model.preset import Preset
from bdbox.protocol import (
    ConnectedMessage,
    Message,
    ModelDetailsMessage,
    ModelDisplayInfo,
    ModelParamsState,
    ModelResetParamsMessage,
    ModelRunStatusMessage,
    ModelSetParamMessage,
    ModelSetPresetMessage,
    ServerMessage,
    VersionInfo,
)
from bdbox.runner.state import run_state
from bdbox.view.state import ViewState
from bdbox.view.ui.app import UIApp

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

if TYPE_CHECKING:
    from collections.abc import Iterator

    from starlette.testclient import WebSocketTestSession
    from syrupy.assertion import SnapshotAssertion


TEST_SESSION_ID = UUID("deadbeef-0327-1138-2187-c01dc0ffee77")


@dataclass
class WSParamTest:
    app: UIApp = field(init=False)
    snapshot: SnapshotAssertion | None = None
    view_state: ViewState = field(default_factory=ViewState)
    ws: WebSocketTestSession | None = field(default=None, init=False)
    client: TestClient | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        self.app = UIApp(
            view_state=self.view_state, session_id=TEST_SESSION_ID
        )

    @contextmanager
    def __call__(self) -> Iterator[Self]:
        with TestClient(self.app) as client:
            self.client = client
            with self.wsconn() as ws:
                self.ws = ws
                # Connection established message
                assert ws.receive_json() == self.snapshot
                # Model message
                if self.view_state.model_class:
                    assert ws.receive_json() == self.snapshot
                yield self

    @contextmanager
    def wsconn(self) -> Iterator[WebSocketTestSession]:
        if not self.client:
            raise InternalError("Client not available")
        with self.client.websocket_connect("/ws") as ws:
            yield ws

    def send(
        self,
        msg: Message | dict[str, Any],
        expect_overrides: dict[str, Any] | None = None,
        *,
        expect_response: bool = True,
        expect_event: bool = True,
    ) -> Any:
        if not self.ws:
            raise InternalError("Websocket connection not available")
        if isinstance(msg, Message):
            msg = msg.to_dict()
        self.ws.send_json(msg)
        ack = None
        if expect_response:
            ack = self.ws.receive_json()
            if expect_overrides is not None:
                assert ack["params"]["overrides"] == expect_overrides
                assert self.view_state.params.overrides == expect_overrides
        if expect_event:
            assert self.view_state.rerender_event.is_set()
        else:
            assert not self.view_state.rerender_event.is_set()
        return ack

    def recv(self) -> dict[str, Any]:
        if not self.ws:
            raise InternalError("Websocket connection not available")
        msg = self.ws.receive_json()
        assert msg == self.snapshot
        return msg


@pytest.fixture(autouse=True)
def mock_protocol_bdbox_version() -> Iterator[None]:
    original = VersionInfo.__init__

    def wrapper(self: VersionInfo, *args: Any, **kwargs: Any) -> None:
        original(self, *args, **kwargs)
        self.bdbox = "11.38.77"

    with patch.object(VersionInfo, "__init__", new=wrapper):
        yield


@pytest.fixture(autouse=True)
def wspt(
    snapshot: SnapshotAssertion, view_state: ViewState
) -> Iterator[WSParamTest]:
    with (
        WSParamTest(snapshot=snapshot, view_state=view_state)() as wspt,
    ):
        yield wspt


@pytest.fixture(
    params=(
        pytest.param((Params, "P"), id="Params"),
        pytest.param((Model, "M"), id="Model"),
    )
)
def model_class(request: pytest.FixtureRequest) -> type[Params] | None:
    if not request.param:
        return None
    cls, name = request.param
    return type(
        name,
        (cls,),
        {
            "width": Float(default=10.0),
            "count": Int(default=3),
            "presets": (Preset("small", width=5.0, count=1),),
        },
    )


@pytest.fixture(params=(pytest.param({}),))
def param_overrides(request: pytest.FixtureRequest) -> dict[str, Any]:
    return dict(request.param)


@pytest.fixture
def view_state(
    model_class: type[Params], param_overrides: dict[str, Any]
) -> ViewState:
    run_state.model_state.model_subclasses = [model_class]
    return ViewState(
        model_class=model_class,
        params=ModelParamsState(
            values=({"width": 10.0, "count": 3} if model_class else {}),
            overrides=param_overrides,
        ),
    )


def test_update_param_accumulates(wspt: WSParamTest) -> None:
    assert not wspt.view_state.rerender_event.is_set()
    wspt.send(
        ModelSetParamMessage(field="width", value=50.0),
        expect_overrides={"width": 50.0},
        expect_event=True,
    )
    wspt.send(
        ModelSetParamMessage(field="count", value=2),
        expect_overrides={"width": 50.0, "count": 2},
        expect_event=True,
    )


@pytest.mark.parametrize(
    "param_overrides",
    [pytest.param({"width": 99.0}, id="param_overrides")],
    indirect=True,
)
def test_select_preset_replaces_overrides(wspt: WSParamTest) -> None:
    wspt.send(
        ModelSetPresetMessage(preset="small"),
        expect_overrides={"width": 5.0, "count": 1},
        expect_event=True,
    )


def test_select_preset_unknown_ignored(wspt: WSParamTest) -> None:
    wspt.send(
        ModelSetPresetMessage(preset="does_not_exist"),
        expect_overrides={},
        expect_event=False,
    )


@pytest.mark.parametrize("model_class", [None], indirect=True)
def test_select_preset_no_model_class(wspt: WSParamTest) -> None:
    wspt.send(
        ModelSetPresetMessage(preset="small"),
        expect_overrides={},
        expect_event=False,
    )


@pytest.mark.parametrize(
    "param_overrides",
    [pytest.param({"width": 99.0}, id="param_overrides")],
    indirect=True,
)
def test_reset_params(wspt: WSParamTest) -> None:
    wspt.send(
        ModelResetParamsMessage(), expect_overrides={}, expect_event=True
    )


def test_unknown_message_type_ignored(wspt: WSParamTest) -> None:
    wspt.send(
        {"type": "detention_block", "value": "aa23"},
        expect_response=False,
        expect_event=False,
    )


def test_malformed_json_ignored(wspt: WSParamTest) -> None:
    assert wspt.ws
    wspt.ws.send_text("not valid json {{{")
    wspt.send(
        ModelSetParamMessage(field="width", value=50.0),
        expect_overrides={"width": 50.0},
        expect_event=True,
    )


def test_missing_message_fields_ignored(wspt: WSParamTest) -> None:
    wspt.send(
        {"type": "model.set_param"}, expect_event=False, expect_response=False
    )


@pytest.mark.parametrize("model_class", [None], indirect=True)
def test_ws_connect_no_model_sends_no_schema(wspt: WSParamTest) -> None:
    wspt.send(
        ModelSetParamMessage(field="width", value=5.0),
        expect_overrides={"width": 5.0},
        expect_event=True,
    )


def test_ws_update_param(wspt: WSParamTest) -> None:
    wspt.send(ModelSetParamMessage(field="width", value=75.0))


def test_ws_select_preset(wspt: WSParamTest) -> None:
    wspt.send(
        ModelSetPresetMessage(preset="small"),
        expect_overrides={"width": 5.0, "count": 1},
        expect_event=True,
    )


@pytest.mark.parametrize(
    "param_overrides",
    [pytest.param({"width": 99.0}, id="param_overrides")],
    indirect=True,
)
def test_ws_reset_params(wspt: WSParamTest) -> None:
    wspt.send(
        ModelResetParamsMessage(), expect_overrides={}, expect_event=True
    )


@pytest.mark.parametrize(
    "message",
    [
        pytest.param(
            ModelDetailsMessage(
                params=ModelParamsState(
                    values={"a": 5.0, "b": "nope"},
                    overrides={"foo": "bar"},
                ),
                model_info=ModelDisplayInfo(filename="some_model.py"),
            ),
            id="schema",
        ),
        pytest.param(
            ModelRunStatusMessage.running(
                datetime(1977, 5, 25, 11, 38, 00, tzinfo=timezone.utc)
            ),
            id="run_start",
        ),
        pytest.param(
            ModelRunStatusMessage.done(elapsed_ms=123),
            id="run_ok",
        ),
        pytest.param(
            ModelRunStatusMessage.error(elapsed_ms=234), id="run_error"
        ),
    ],
)
def test_ws_broadcast_reaches_client(
    wspt: WSParamTest, message: ServerMessage
) -> None:
    wspt.app.enqueue(message)
    received_data = wspt.recv()
    assert received_data == message.to_dict()
    assert Message.from_dict(received_data) == message


def test_ws_broadcast_reaches_multiple_clients(wspt: WSParamTest) -> None:
    message = ModelRunStatusMessage.running(
        datetime(1977, 5, 25, 11, 38, 00, tzinfo=timezone.utc)
    )
    with wspt.wsconn() as ws2:
        connected_message_data = ws2.receive_json()
        connected_message = Message.from_dict(connected_message_data)
        assert ws2.receive_json() == wspt.snapshot
        wspt.app.enqueue(message)
        wspt.recv()
        assert connected_message == ConnectedMessage(
            session_id=TEST_SESSION_ID
        )
        received_data = ws2.receive_json()
        assert received_data == message.to_dict()
        assert Message.from_dict(received_data) == message
