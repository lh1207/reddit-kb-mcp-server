#!/usr/bin/env python3
"""Stop hook: run ruff and pytest before letting the session end; block on failure.

Reads the hook JSON payload from stdin. Exit 0 = pass, exit 2 = block (stderr is fed back
to Claude with the tail of the failing output). Guards against infinite loops via
stop_hook_active, and fails open on any parsing error or when the environment cannot run
a check (missing ruff/pytest, or project deps not importable). Prefers the project venv
(.venv) so checks run against the interpreter that has the project's dependencies.
"""

import json
import os
import subprocess
import sys


def _tail(text: str, n: int = 30) -> str:
    lines = text.splitlines()
    return "\n".join(lines[-n:])


def _python(project_dir: str) -> str:
    for rel in (".venv/bin/python", ".venv/Scripts/python.exe"):
        candidate = os.path.join(project_dir, rel)
        if os.path.isfile(candidate):
            return candidate
    return sys.executable


def _runnable(cmd: list[str], cwd: str) -> bool:
    try:
        return subprocess.run(cmd, cwd=cwd, capture_output=True, timeout=60).returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def main() -> None:
    try:
        payload = json.load(sys.stdin)

        # Infinite-loop guard: don't re-run verification triggered by our own Stop hook.
        if payload.get("stop_hook_active"):
            sys.exit(0)

        project_dir = os.environ.get("CLAUDE_PROJECT_DIR", ".")
        py = _python(project_dir)

        if _runnable([py, "-m", "ruff", "--version"], project_dir):
            result = subprocess.run(
                [py, "-m", "ruff", "check", "."],
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode != 0:
                sys.stderr.write(_tail(result.stdout + result.stderr))
                sys.exit(2)

        # Only run the suite if the interpreter can import the project deps; a
        # half-provisioned environment (pytest present, fastmcp absent) must fail
        # open rather than block every stop with collection errors.
        if _runnable([py, "-c", "import pytest, fastmcp"], project_dir):
            result = subprocess.run(
                [py, "-m", "pytest", "-q"],
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode != 0:
                sys.stderr.write(_tail(result.stdout + result.stderr))
                sys.exit(2)

        sys.exit(0)
    except Exception:
        # Fail open: a malformed payload must never brick the session.
        sys.exit(0)


if __name__ == "__main__":
    main()
