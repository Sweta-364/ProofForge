"""
Isolated Docker sandbox for running student code against test suites.
Security settings mirror CLAUDE.md exactly — do not change them.
"""
import asyncio
import json
import logging
import shutil
import tarfile
import uuid
from io import BytesIO
from pathlib import Path

import docker

from app import minio as minio_module
from app.config import settings

logger = logging.getLogger(__name__)


class SandboxRunner:
    def __init__(self):
        self.client = docker.from_env()
        self.temp_dir = Path(settings.SANDBOX_TEMP_DIR)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    async def run_tests(
        self,
        problem_slug: str,
        code_files: dict[str, str],
        test_suite: str = "visible",
        problem_meta: dict | None = None,
    ) -> dict:
        """Run student code in an isolated container and return structured results."""
        session_id = str(uuid.uuid4())
        session_dir = self.temp_dir / session_id
        submission_dir = session_dir / "workspace"
        output_dir = session_dir / "output"
        submission_dir.mkdir(parents=True)
        output_dir.mkdir(parents=True)

        container = None
        try:
            # 1. Write student files
            for filepath, content in code_files.items():
                dest = (submission_dir / filepath).resolve()
                if not dest.is_relative_to(submission_dir.resolve()):
                    logger.warning("Skipping path-traversal file: %s", filepath)
                    continue
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(content, encoding="utf-8")

            # Problem pytest.ini files are not packed into the tarballs, so
            # provide the shared config (async test support) at the rootdir.
            (submission_dir / "pytest.ini").write_text(
                "[pytest]\n"
                "asyncio_mode = auto\n"
                "asyncio_default_fixture_loop_scope = session\n",
                encoding="utf-8",
            )

            # 2. Download test suite from MinIO and extract into workspace/tests/
            test_key = f"tests/{problem_slug}.tar.gz"
            test_bytes = minio_module.download_file(minio_module.PROBLEMS_BUCKET, test_key)
            test_archive = session_dir / "tests.tar.gz"
            test_archive.write_bytes(test_bytes)
            tests_dir = submission_dir / "tests"
            tests_dir.mkdir(exist_ok=True)
            with tarfile.open(test_archive) as tar:
                tar.extractall(tests_dir)

            # 3. Build test command
            if test_suite == "visible":
                test_cmd = [
                    "pytest", "/workspace/tests/test_visible.py",
                    "-v", "--tb=short", "-p", "no:cacheprovider",
                    "--json-report", "--json-report-file=/output/results.json",
                ]
            else:
                test_cmd = [
                    "pytest", "/workspace/tests/",
                    "-v", "--tb=short", "-p", "no:cacheprovider",
                    "--json-report", "--json-report-file=/output/results.json",
                ]

            image = (problem_meta or {}).get("docker_image", "proofforge/python-runner:3.12")

            # 4. Spawn container (blocking docker call off the event loop)
            loop = asyncio.get_event_loop()
            container = await loop.run_in_executor(
                None,
                lambda: self.client.containers.run(
                    image=image,
                    command=test_cmd,
                    # /workspace is read-only; run from the writable tmpfs so tests
                    # that create scratch files (uploads, temp data) don't crash.
                    working_dir="/tmp",
                    volumes={
                        str(submission_dir): {"bind": "/workspace", "mode": "ro"},
                        str(output_dir):     {"bind": "/output",    "mode": "rw"},
                    },
                    network_mode="none",
                    mem_limit="256m",
                    nano_cpus=500_000_000,
                    read_only=True,
                    tmpfs={"/tmp": "size=64m"},
                    security_opt=["no-new-privileges:true"],
                    cap_drop=["ALL"],
                    detach=True,
                    remove=False,
                ),
            )

            # 5. Wait with 30-second hard timeout
            try:
                await loop.run_in_executor(
                    None, lambda: container.wait(timeout=30)
                )
            except Exception:
                try:
                    container.kill()
                except Exception:
                    pass
                return self._timeout_result(session_id)

            # 6. Parse results
            results_path = output_dir / "results.json"
            if results_path.exists():
                raw = json.loads(results_path.read_text(encoding="utf-8"))
                return self._parse_pytest_results(raw, session_id)
            else:
                try:
                    logs = container.logs().decode("utf-8", errors="replace")
                except Exception:
                    logs = "(no logs)"
                return self._error_result(session_id, logs)

        finally:
            # ALWAYS remove the container — leaked containers crash the demo
            if container is not None:
                try:
                    container.remove(force=True)
                except Exception:
                    pass
            shutil.rmtree(session_dir, ignore_errors=True)

    # ── result parsers ─────────────────────────────────────────────────────────

    def _parse_pytest_results(self, raw: dict, session_id: str) -> dict:
        tests = raw.get("tests", [])
        summary = raw.get("summary", {})
        total = summary.get("total", 0)

        # A collection error (missing dependency, import error in the test or
        # starter code, syntax error) yields a report with 0 collected tests.
        # Surface it as an error instead of a confusing "0/0 passed".
        collect_errors = [
            c for c in raw.get("collectors", [])
            if c.get("outcome") == "failed"
        ]
        if total == 0 and collect_errors:
            longrepr = collect_errors[0].get("longrepr") or "Test collection failed"
            return {
                "session_id": session_id,
                "status": "error",
                "passed": 0,
                "failed": 0,
                "total": 0,
                "error": f"Could not collect any tests:\n{str(longrepr)[:800]}",
                "tests": [],
            }

        # Tests that error during setup/call (summary key "error") still count
        # toward the total and should read as not-passed.
        failed = summary.get("failed", 0) + summary.get("error", 0)
        return {
            "session_id": session_id,
            "status": "completed",
            "passed": summary.get("passed", 0),
            "failed": failed,
            "total": total,
            "duration_ms": int(raw.get("duration", 0) * 1000),
            "tests": [
                {
                    "name": t["nodeid"].split("::")[-1],
                    "status": t["outcome"],
                    "duration_ms": int(t.get("call", {}).get("duration", 0) * 1000),
                    "error": (
                        t.get("call", {}).get("longrepr", None)
                        if t["outcome"] != "passed"
                        else None
                    ),
                }
                for t in tests
            ],
        }

    def _timeout_result(self, session_id: str) -> dict:
        return {
            "session_id": session_id,
            "status": "timeout",
            "passed": 0,
            "failed": 0,
            "total": 0,
            "error": "Execution timed out after 30 seconds",
            "tests": [],
        }

    def _error_result(self, session_id: str, logs: str) -> dict:
        return {
            "session_id": session_id,
            "status": "error",
            "passed": 0,
            "failed": 0,
            "total": 0,
            "error": f"No test results produced. Logs: {logs[:500]}",
            "tests": [],
        }


# Module-level singleton — imported by router.py
sandbox_runner = SandboxRunner()
