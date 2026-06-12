"""Visible tests - the platform review findings."""
from pathlib import Path

from tests.docker_helper import dockerfile_lines

STARTER = Path(__file__).resolve().parent.parent / "starter"


def test_base_image_is_pinned():
    from_lines = [l for l in dockerfile_lines(STARTER) if l.upper().startswith("FROM ")]
    assert from_lines, "Dockerfile needs a FROM line"
    image = from_lines[0].split()[1]
    assert not image.endswith(":latest"), "pin the base image instead of :latest"
    assert ":" in image, "pin the base image to a specific tag"


def test_runs_as_non_root_user():
    user_lines = [l for l in dockerfile_lines(STARTER) if l.upper().startswith("USER ")]
    assert user_lines, "add a USER directive - the container must not run as root"
    user = user_lines[-1].split()[1]
    assert user not in ("root", "0"), "the runtime user must not be root"


def test_pip_does_not_cache_wheels():
    pip_lines = [l for l in dockerfile_lines(STARTER) if "pip install" in l]
    assert pip_lines, "expected a pip install layer"
    assert all("--no-cache-dir" in l for l in pip_lines), "use pip install --no-cache-dir"


def test_workdir_is_set():
    assert any(
        l.upper().startswith("WORKDIR ") for l in dockerfile_lines(STARTER)
    ), "set a WORKDIR instead of installing into /"
