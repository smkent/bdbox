import sys

import pytest

import bdbox
from bdbox.__main__ import main


def test_version(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    assert bdbox.version not in ("", "0.0.0")
    monkeypatch.setattr(sys, "argv", ["bdbox", "version"])
    with pytest.raises(SystemExit):
        main()

    assert capsys.readouterr().out.strip() == bdbox.version
