"""
Sandbox runner integration tests.

These tests require:
- Docker socket accessible (/var/run/docker.sock)
- proofforge/python-runner:3.12 image built
- MinIO running with problems bucket seeded (002_seed_problems.py run)
- pytest mark: sandbox (skip if docker not available)
"""
import docker
import pytest

from sandbox.runner import SandboxRunner

# ── Helpers ───────────────────────────────────────────────────────────────────

def _docker_available() -> bool:
    try:
        docker.from_env().ping()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _docker_available(),
    reason="Docker not available in this environment",
)


@pytest.fixture(scope="module")
def runner():
    return SandboxRunner()


def _no_runner_containers(client: docker.DockerClient) -> bool:
    containers = client.containers.list(
        all=True,
        filters={"ancestor": "proofforge/python-runner:3.12"},
    )
    return len(containers) == 0


# ── Tests ─────────────────────────────────────────────────────────────────────

async def test_sandbox_broken_starter(runner: SandboxRunner):
    """Broken cors-fix starter → at least one visible test fails."""
    broken_code = {
        "starter/__init__.py": "",
        "starter/main.py": (
            "from fastapi import FastAPI\n"
            "app = FastAPI()\n\n"
            "@app.get('/api/users')\n"
            "async def get_users(): return []\n"
        ),
    }
    result = await runner.run_tests(
        problem_slug="001-cors-fix",
        code_files=broken_code,
        test_suite="visible",
        problem_meta={"docker_image": "proofforge/python-runner:3.12"},
    )
    assert result["status"] == "completed"
    assert result["failed"] >= 1, "Broken code must fail at least one test"


async def test_sandbox_fixed_code(runner: SandboxRunner):
    """Correctly fixed cors-fix code → all visible tests pass."""
    fixed_code = {
        "starter/__init__.py": "",
        "starter/main.py": (
            "from fastapi import FastAPI\n"
            "from fastapi.middleware.cors import CORSMiddleware\n\n"
            "app = FastAPI()\n"
            "app.add_middleware(\n"
            "    CORSMiddleware,\n"
            "    allow_origins=['*'],\n"
            "    allow_methods=['*'],\n"
            "    allow_headers=['*'],\n"
            ")\n\n"
            "MOCK_USERS = [\n"
            "    {'id': 1, 'username': 'alice', 'email': 'alice@example.com'},\n"
            "    {'id': 2, 'username': 'bob', 'email': 'bob@example.com'},\n"
            "]\n\n"
            "@app.get('/api/users')\n"
            "async def get_users(): return MOCK_USERS\n\n"
            "@app.get('/api/health')\n"
            "async def health(): return {'status': 'ok'}\n\n"
            "@app.post('/api/login')\n"
            "async def login(payload: dict): return {'token': 'mock-token-abc123'}\n"
        ),
    }
    result = await runner.run_tests(
        problem_slug="001-cors-fix",
        code_files=fixed_code,
        test_suite="visible",
        problem_meta={"docker_image": "proofforge/python-runner:3.12"},
    )
    assert result["status"] == "completed"
    assert result["failed"] == 0, f"Fixed code must pass all tests; failures: {result['tests']}"
    assert result["passed"] >= 1


async def test_sandbox_timeout(runner: SandboxRunner):
    """Code with an infinite loop must return timeout result, not hang forever."""
    infinite_loop = {
        "starter/__init__.py": "",
        "starter/main.py": (
            "from fastapi import FastAPI\n"
            "app = FastAPI()\n\n"
            "@app.get('/api/users')\n"
            "async def get_users():\n"
            "    while True:\n"
            "        pass\n"
        ),
    }
    # Lower the runner's effective timeout by using a tiny wait test
    # The test suite itself will time out the container
    result = await runner.run_tests(
        problem_slug="001-cors-fix",
        code_files=infinite_loop,
        test_suite="visible",
        problem_meta={"docker_image": "proofforge/python-runner:3.12"},
    )
    # Could be timeout OR error (if pytest collects but the test hangs, container is killed)
    assert result["status"] in ("timeout", "completed", "error"), (
        f"Unexpected status: {result['status']}"
    )
    # Crucial: no container must remain
    client = docker.from_env()
    assert _no_runner_containers(client), "Leaked container detected after timeout test"


async def test_sandbox_network_blocked(runner: SandboxRunner):
    """Code that tries a network call must still complete (network=none makes it fail, not hang)."""
    net_code = {
        "starter/__init__.py": "",
        "starter/main.py": (
            "import socket\n"
            "from fastapi import FastAPI\n"
            "app = FastAPI()\n\n"
            "try:\n"
            "    socket.create_connection(('8.8.8.8', 80), timeout=1)\n"
            "except Exception:\n"
            "    pass  # expected — no network in sandbox\n\n"
            "@app.get('/api/users')\n"
            "async def get_users(): return []\n"
        ),
    }
    result = await runner.run_tests(
        problem_slug="001-cors-fix",
        code_files=net_code,
        test_suite="visible",
        problem_meta={"docker_image": "proofforge/python-runner:3.12"},
    )
    # Container must complete — it won't pass tests but should not hang
    assert result["status"] in ("completed", "error")


async def test_sandbox_cleanup(runner: SandboxRunner):
    """After every run, no proofforge/python-runner containers remain."""
    code = {
        "starter/__init__.py": "",
        "starter/main.py": (
            "from fastapi import FastAPI\n"
            "app = FastAPI()\n"
        ),
    }
    await runner.run_tests(
        problem_slug="001-cors-fix",
        code_files=code,
        test_suite="visible",
        problem_meta={"docker_image": "proofforge/python-runner:3.12"},
    )
    client = docker.from_env()
    assert _no_runner_containers(client), "Container leaked after run_tests()"
