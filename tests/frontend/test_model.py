from __future__ import annotations

import json
from typing import TYPE_CHECKING

from playwright.sync_api import WebSocketRoute, expect

if TYPE_CHECKING:
    from .conftest import LoadApp

SCHEMA = {
    "type": "object",
    "properties": {
        "width": {"type": "number", "title": "Width", "default": 10},
        "height": {"type": "number", "title": "Height", "default": 5},
    },
    "required": ["width", "height"],
    "x-presets": [{"name": "Square", "description": "Equal sides"}],
}


def connect_with_model(ws: WebSocketRoute) -> None:
    ws.send(
        json.dumps(
            {
                "type": "hello",
                "session_id": "test-session",
                "version": {"bdbox": "0.0.0"},
            }
        )
    )
    ws.send(
        json.dumps(
            {
                "type": "model.details",
                "schema": SCHEMA,
                "current_values": {"width": 10, "height": 5},
                "model_info": {
                    "filename": "box.py",
                    "module_name": None,
                    "class_name": "Box",
                },
            }
        )
    )


def test_model_form_renders(load_app: LoadApp) -> None:
    page = load_app(connect_with_model)

    expect(page.locator(".status-model-name")).to_contain_text("Box")
    expect(page.locator(".params-preset-btn")).to_have_text("Square")
    expect(page.locator(".params-reset-btn")).to_be_visible()
    expect(page.locator(".params-form")).not_to_be_empty()


def test_model_status_lifecycle(load_app: LoadApp) -> None:
    ws_ref: list[WebSocketRoute] = []

    def ws_setup(ws: WebSocketRoute) -> None:
        ws_ref.append(ws)
        connect_with_model(ws)

    page = load_app(ws_setup)
    ws = ws_ref[0]

    expect(page.locator(".status-idle")).to_be_visible()

    ws.send(
        json.dumps(
            {
                "type": "model.status",
                "status": "running",
                "started_at": "2026-01-01T00:00:00",
            }
        )
    )
    expect(page.locator(".status-running")).to_be_visible()

    ws.send(
        json.dumps(
            {"type": "model.status", "status": "done", "elapsed_ms": 1234}
        )
    )
    expect(page.locator(".status-ok")).to_be_visible()
    expect(page.locator(".status-ok")).to_contain_text("1.2s")
