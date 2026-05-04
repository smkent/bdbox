"""Server WebSocket and message handler tests."""

from __future__ import annotations

import sys
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import pytest
from starlette.testclient import TestClient

from bdbox.errors import Error
from bdbox.model import Model
from bdbox.parameters.field_factories import Float, Int
from bdbox.parameters.parameters import Params
from bdbox.parameters.preset import Preset
from bdbox.server.app import App
from bdbox.server.context import Context
from bdbox.server.routes import manager

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

if TYPE_CHECKING:
    from collections.abc import Iterator

    from starlette.testclient import WebSocketTestSession
    from syrupy.assertion import SnapshotAssertion


@dataclass
class WSParamTest:
    snapshot: SnapshotAssertion | None = None
    context: Context = field(default_factory=Context)
    ws: WebSocketTestSession | None = field(default=None, init=False)
    client: TestClient | None = field(default=None, init=False)

    @contextmanager
    def __call__(self) -> Iterator[Self]:
        with (
            TestClient(App(self.context)) as client,
        ):
            self.client = client
            with self.wsconn() as ws:
                self.ws = ws
                if self.context.model_class:
                    assert ws.receive_json() == self.snapshot
                yield self

    @contextmanager
    def wsconn(self) -> Iterator[WebSocketTestSession]:
        if not self.client:
            raise Error("Client not available")
        with self.client.websocket_connect("/ws") as ws:
            yield ws

    def send(
        self,
        msg: dict[str, Any],
        expect_overrides: dict[str, Any] | None = None,
        *,
        expect_event: bool = True,
    ) -> Any:
        if not self.ws:
            raise Error("Websocket connection not available")
        self.ws.send_json(msg)
        ack = self.ws.receive_json()
        if expect_overrides is not None:
            assert ack["param_overrides"] == expect_overrides
            assert self.context.param_overrides == expect_overrides
        if expect_event:
            assert self.context.rerender_event.is_set()
        else:
            assert not self.context.rerender_event.is_set()
        return ack

    def recv(self) -> dict[str, Any]:
        if not self.ws:
            raise Error("Websocket connection not available")
        msg = self.ws.receive_json()
        assert msg == self.snapshot
        return msg


@pytest.fixture(autouse=True)
def wspt(
    snapshot: SnapshotAssertion, context: Context
) -> Iterator[WSParamTest]:
    manager.active.clear()
    with WSParamTest(snapshot=snapshot, context=context)() as wspt:
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
def context(
    model_class: type[Params], param_overrides: dict[str, Any]
) -> Context:
    return Context(
        rerender_event=threading.Event(),
        model_class=model_class,
        current_values=({"width": 10.0, "count": 3} if model_class else {}),
        param_overrides=param_overrides,
    )


def test_update_param_accumulates(wspt: WSParamTest) -> None:
    assert not wspt.context.rerender_event.is_set()
    wspt.send(
        {"type": "update_param", "field": "width", "value": 50.0},
        expect_overrides={"width": 50.0},
        expect_event=True,
    )
    wspt.send(
        {"type": "update_param", "field": "count", "value": 2},
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
        {"type": "select_preset", "preset": "small"},
        expect_overrides={"width": 5.0, "count": 1},
        expect_event=True,
    )


def test_select_preset_unknown_ignored(wspt: WSParamTest) -> None:
    wspt.send(
        {"type": "select_preset", "preset": "does_not_exist"},
        expect_overrides={},
        expect_event=False,
    )


@pytest.mark.parametrize("model_class", [None], indirect=True)
def test_select_preset_no_model_class(wspt: WSParamTest) -> None:
    wspt.send(
        {"type": "select_preset", "preset": "small"},
        expect_overrides={},
        expect_event=False,
    )


@pytest.mark.parametrize(
    "param_overrides",
    [pytest.param({"width": 99.0}, id="param_overrides")],
    indirect=True,
)
def test_reset_params(wspt: WSParamTest) -> None:
    wspt.send({"type": "reset_params"}, expect_overrides={}, expect_event=True)


def test_unknown_message_type_ignored(wspt: WSParamTest) -> None:
    wspt.send(
        {"type": "detention_block", "value": "aa23"},
        expect_overrides={},
        expect_event=False,
    )


@pytest.mark.parametrize("model_class", [None], indirect=True)
def test_ws_connect_no_model_sends_no_schema(wspt: WSParamTest) -> None:
    wspt.send(
        {"type": "update_param", "field": "width", "value": 5.0},
        expect_overrides={"width": 5.0},
        expect_event=True,
    )


def test_ws_update_param(wspt: WSParamTest) -> None:
    wspt.send({"type": "update_param", "field": "width", "value": 75.0})


def test_ws_select_preset(wspt: WSParamTest) -> None:
    wspt.send(
        {"type": "select_preset", "preset": "small"},
        expect_overrides={"width": 5.0, "count": 1},
        expect_event=True,
    )


@pytest.mark.parametrize(
    "param_overrides",
    [pytest.param({"width": 99.0}, id="param_overrides")],
    indirect=True,
)
def test_ws_reset_params(wspt: WSParamTest) -> None:
    wspt.send({"type": "reset_params"}, expect_overrides={}, expect_event=True)


def test_ws_broadcast_reaches_client(wspt: WSParamTest) -> None:
    msg = {"type": "run_ok", "elapsed_ms": 123, "current_values": {}}
    wspt.context.msg_queue.put(msg)
    assert wspt.recv() == msg


def test_ws_broadcast_reaches_multiple_clients(wspt: WSParamTest) -> None:
    msg = {"type": "run_start", "params": {}}
    with wspt.wsconn() as ws2:
        assert ws2.receive_json() == wspt.snapshot
        wspt.context.msg_queue.put(msg)
        wspt.recv()
        assert ws2.receive_json() == msg
