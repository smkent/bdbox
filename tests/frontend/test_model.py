from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from playwright.sync_api import expect

from bdbox.model.model import Model
from bdbox.model.preset import Preset
from bdbox.protocol import (
    ModelDetailsMessage,
    ModelDisplayInfo,
    ModelParamsState,
    ModelRunStatusMessage,
    ModelSetParamMessage,
)
from bdbox.serializer import serializer

if TYPE_CHECKING:
    from .conftest import BackendTestApp


def test_model_form_renders(app: BackendTestApp) -> None:

    def _expect_no_jedison_errors() -> None:
        expect(app.page.locator(".jedi-error-message")).to_have_count(0)
        expect(app.page.locator(".jedi-error-message")).not_to_be_visible()

    class Box(Model):
        width: int = 10
        height: int = 5

        presets = (Preset("Square", description="Equal sides"),)

    app.send(
        ModelDetailsMessage(
            schema=serializer.json_schema(Box),
            model_info=ModelDisplayInfo(
                filename="box.py", class_name=Box.__name__
            ),
            params=ModelParamsState(values={"width": 10, "height": 5}),
        )
    )
    expect(app.page.locator(".status-model-name")).to_contain_text("Box")
    expect(app.page.locator(".params-preset-btn")).to_have_text("Square")
    expect(app.page.locator(".params-reset-btn")).to_be_visible()
    expect(app.page.locator(".params-form")).not_to_be_empty()
    _expect_no_jedison_errors()

    # Change a parameter value
    app.send(
        ModelDetailsMessage(
            params=ModelParamsState(values={"width": 5, "height": 5}),
        )
    )
    _expect_no_jedison_errors()


def test_model_status_lifecycle(app: BackendTestApp) -> None:
    expect(app.page.locator(".status-idle")).to_be_visible()
    app.send(
        ModelRunStatusMessage.running(
            started_at=datetime(1977, 5, 25, 11, 38, 00, tzinfo=timezone.utc)
        )
    )
    expect(app.page.locator(".status-running")).to_be_visible()


def test_param_change_sends_message(app: BackendTestApp) -> None:

    class Box(Model):
        width: int = 10
        height: int = 5

        presets = (Preset("Square", description="Equal sides"),)

    app.send(
        ModelDetailsMessage(
            schema=serializer.json_schema(Box),
            model_info=ModelDisplayInfo(
                filename="box.py", class_name=Box.__name__
            ),
            params=ModelParamsState(values={"width": 10, "height": 5}),
        )
    )

    expect(app.page.locator(".params-form")).not_to_be_empty()

    # Exact selector depends on Jedison's output
    # inspect with page.pause() first run
    width_input = app.page.locator('input[name="root-width"]').first
    width_input.fill("25")
    width_input.press("Tab")

    while message := app.messages.get(timeout=3.0):
        if isinstance(message, ModelSetParamMessage):
            break

    assert message == ModelSetParamMessage(field="width", value=25)
