from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
from playwright.sync_api import Page, WebSocketRoute

ORIGIN = "http://bdbox.test"
STATIC = Path("bdbox/view/static")

APP_HTML = """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <link rel="stylesheet" href="/static/app.css">
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { overflow: hidden; background: #111; }
  </style>
  <script>window.__BDBOX__ = {"viewerPort": 9999};</script>
  <script src="/static/app.js" defer></script>
</head>
<body>
  <div id="layout" style="width: 100%; height: 100vh;"></div>
</body>
</html>"""


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Dynamically add frontend marker to tests in this directory."""
    this_dir = Path(__file__).parent
    for item in items:
        if item.path and item.path.is_relative_to(this_dir):
            item.add_marker(pytest.mark.frontend)


LoadApp = Callable[[Callable[[WebSocketRoute], None]], Page]


@pytest.fixture
def load_app(page: Page) -> LoadApp:
    page.route(
        f"{ORIGIN}/",
        lambda r: r.fulfill(content_type="text/html", body=APP_HTML),
    )
    page.route(
        f"{ORIGIN}/static/app.js",
        lambda r: r.fulfill(
            content_type="application/javascript", path=str(STATIC / "app.js")
        ),
    )
    page.route(
        f"{ORIGIN}/static/app.css",
        lambda r: r.fulfill(
            content_type="text/css", path=str(STATIC / "app.css")
        ),
    )
    page.route(f"{ORIGIN}/viewer**", lambda r: r.fulfill(status=200, body=""))

    def _load(ws_setup: Callable[[WebSocketRoute], None]) -> Page:
        page.route_web_socket("ws://bdbox.test/ws", ws_setup)
        page.goto(f"{ORIGIN}/")
        return page

    return _load
