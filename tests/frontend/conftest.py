from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from queue import Queue
from typing import TYPE_CHECKING

import pytest

from bdbox.console import console, log
from bdbox.dispatch import Event
from bdbox.protocol import BrowserMessage, ConnectedMessage
from bdbox.view.state import ViewState
from bdbox.view.ui.server import UIServer

if TYPE_CHECKING:
    from playwright.sync_api import Page, WebSocketRoute

    from bdbox.protocol import ServerMessage


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Dynamically add frontend marker to tests in this directory."""
    this_dir = Path(__file__).parent
    for item in items:
        if item.path and item.path.is_relative_to(this_dir):
            item.add_marker(pytest.mark.frontend)


@pytest.fixture(autouse=True)
def console_verbosity_configure(console_verbosity: None) -> None:
    console.configure()


VIEWER_PORT = 65000


@pytest.fixture(scope="session", autouse=True)
def build_frontend_assets() -> None:
    subprocess.run(["npm", "run", "build"], check=True)


@dataclass
class BackendTestApp:
    backend_server: UIServer = field(init=False)
    page: Page
    websocket: WebSocketRoute | None = field(default=None, init=False)
    websocket_connected: Event = field(
        default_factory=lambda: Event(name="websocket_connected"), init=False
    )
    websocket_received: list[BrowserMessage] = field(
        default_factory=list, init=False
    )
    messages: Queue[BrowserMessage] = field(default_factory=Queue, init=False)

    def __post_init__(self) -> None:
        self.backend_server = UIServer(
            view_state=ViewState(),
            listen_port=40404,
            open_browser=False,
        )
        self.backend_server.ready_wait()
        self.page.route(
            f"http*://localhost:{VIEWER_PORT}/viewer**",
            lambda r: r.fulfill(status=200, body=""),
        )
        self.page.route_web_socket(
            f"ws://{self.url.removeprefix('http://')}/ws",
            self.handle_websocket_connect,
        )
        self.page.goto(f"{self.url}/")
        if not self.websocket_connected.wait(timeout=3.0):
            raise Exception("Websocket did not connect within timeout")  # noqa: TRY002

    @property
    def url(self) -> str:
        return self.backend_server.base_url

    def send(self, message: ServerMessage) -> None:
        if not self.websocket:
            raise Exception("No websocket connected")  # noqa: TRY002
        msg_dict = message.to_dict()
        if message.log_ok:
            log.debug("Send: %s", json.dumps(msg_dict, indent=4))
        self.websocket.send(json.dumps(msg_dict))

    def handle_websocket_connect(self, ws: WebSocketRoute) -> None:
        if self.websocket:
            raise Exception("Websocket already connected")  # noqa: TRY002
        self.websocket = ws
        self.websocket.on_message(self.handle_websocket_message)
        self.websocket_connected.set()
        self.send(
            ConnectedMessage(session_id=self.backend_server.app.session_id)
        )

    def handle_websocket_message(self, data: str | bytes) -> None:
        msg_dict = json.loads(data)
        log.debug("Received: %s", msg_dict)
        self.messages.put(BrowserMessage.from_dict(msg_dict))


@pytest.fixture
def app(page: Page) -> BackendTestApp:
    return BackendTestApp(page=page)
