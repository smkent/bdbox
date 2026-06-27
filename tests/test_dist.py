import subprocess
from pathlib import Path
from zipfile import ZipFile

import pytest

from .utils import DisallowCallable


@pytest.fixture
def repo_copy(tmp_path: Path, disallow_subprocess: DisallowCallable) -> Path:
    repo_dir = tmp_path / "repo_copy"
    with disallow_subprocess.pause():
        subprocess.check_call(["git", "clone", ".", repo_dir])  # noqa: S603
    return repo_dir


@pytest.fixture
def dist_wheel(
    tmp_path: Path, repo_copy: Path, disallow_subprocess: DisallowCallable
) -> Path:
    dist_dir = tmp_path / "dist"
    with disallow_subprocess.pause():
        subprocess.check_call(  # noqa: S603
            [
                "uv",
                "--offline",
                "build",
                "--wheel",
                "--out-dir",
                str(dist_dir),
            ],
            cwd=repo_copy,
        )
    wheels = list(dist_dir.glob("*.whl"))
    assert len(wheels) == 1
    wheel = wheels[0]
    assert wheel.stem.startswith("bdbox-")
    return wheel


def test_dist_ui_statics(dist_wheel: Path) -> None:
    expected_files = {
        f"bdbox/view/ui/static/{fn}"
        for fn in ("app.css", "app.js", "favicon.png")
    }
    with ZipFile(dist_wheel, "r") as whl:
        present_files = expected_files & set(whl.namelist())
    assert present_files == expected_files
