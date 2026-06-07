from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest

from bdbox.protocol import (
    ConnectedMessage,
    VersionInfo,
)

if TYPE_CHECKING:
    from .conftest import BackendTestApp


@pytest.mark.parametrize(
    ("version_changes", "expected_console"),
    [
        pytest.param(
            {"bdbox": "21.87.77"},
            "bdbox version changed from 11.38.77 to 21.87.77",
            id="bdbox_change",
        ),
        pytest.param(
            {"protocol": 2187},
            "protocol version changed from 1138 to 2187",
            id="protocol_change",
        ),
    ],
)
def test_version_change_logged(
    app: BackendTestApp,
    version_changes: dict[str, object],
    expected_console: str,
) -> None:
    session_id = app.backend_server.view_state.session_id
    start_version = VersionInfo(bdbox="11.38.77", protocol=1138)
    app.send(ConnectedMessage(session_id=session_id, version=start_version))

    with app.page.expect_console_message(
        lambda msg: expected_console in msg.text
    ):
        app.send(
            ConnectedMessage(
                session_id=uuid4(),
                version=replace(start_version, **version_changes),
            )
        )
