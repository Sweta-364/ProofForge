#!/usr/bin/env python3
"""Verify every problem end-to-end (outside Docker):

1. starter + tests  -> pytest must FAIL (the bug is demonstrated)
2. solution + tests -> pytest must PASS (the reference fix works)

Mirrors the sandbox layout: workspace/starter/, workspace/tests/, and the
pytest.ini the runner injects at the workspace root.

Usage: python scripts/verify_problems.py [slug ...]
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PROBLEMS = REPO / "problems"

RUNNER_PYTEST_INI = (
    "[pytest]\n"
    "asyncio_mode = auto\n"
    "asyncio_default_fixture_loop_scope = session\n"
)


def run_pytest(workspace: Path) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests", "-q", "--no-header",
         "-p", "no:cacheprovider"],
        cwd=workspace,
        capture_output=True,
        text=True,
        timeout=120,
    )
    return proc.returncode, proc.stdout + proc.stderr


def build_workspace(problem_dir: Path, base: Path, use_solution: bool) -> Path:
    workspace = base / ("solution" if use_solution else "starter")
    shutil.copytree(problem_dir / "starter", workspace / "starter")
    shutil.copytree(problem_dir / "tests", workspace / "tests")
    (workspace / "pytest.ini").write_text(RUNNER_PYTEST_INI, encoding="utf-8")
    if use_solution:
        solution = problem_dir / "solution"
        for f in solution.rglob("*"):
            if f.is_file():
                dest = workspace / "starter" / f.relative_to(solution)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, dest)
    return workspace


def verify(problem_dir: Path) -> bool:
    slug = problem_dir.name
    has_solution = (problem_dir / "solution").exists()
    ok = True

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)

        code, out = run_pytest(build_workspace(problem_dir, base, use_solution=False))
        if code == 0:
            print(f"FAIL {slug}: starter PASSES the tests (no bug demonstrated)")
            ok = False
        elif "error" in out.lower() and "failed" not in out.lower() and "collect" in out.lower():
            print(f"WARN {slug}: starter run looks like a collection error:\n{out[-800:]}")

        if has_solution:
            code, out = run_pytest(build_workspace(problem_dir, base, use_solution=True))
            if code != 0:
                print(f"FAIL {slug}: solution does NOT pass:\n{out[-1500:]}")
                ok = False
        else:
            print(f"NOTE {slug}: no solution/ dir - starter-fails check only")

    if ok:
        print(f"OK   {slug}")
    return ok


def main() -> None:
    requested = sys.argv[1:]
    dirs = sorted(
        d for d in PROBLEMS.iterdir()
        if d.is_dir() and (d / "meta.json").exists()
        and (not requested or d.name in requested)
    )
    results = [verify(d) for d in dirs]
    failed = results.count(False)
    print(f"\n{len(results) - failed}/{len(results)} problems verified")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
