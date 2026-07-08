#!/usr/bin/env python3
"""Stop hook: run ruff and pytest before letting the session end; block on failure.

Reads the hook JSON payload from stdin. Exit 0 = pass, exit 2 = block (stderr is fed back
to Claude with the tail of the failing output). Guards against infinite loops via
stop_hook_active, and fails open on any parsing error or if ruff/pytest aren't installed.
"""

import json
import os
import subprocess
import sys


def _tail(text: str, n: int = 30) -> str:
    lines = text.splitlines()
    return "\n".join(lines[-n:])


def main() -> None:
    try:
        payload = json.load(sys.stdin)

        # Infinite-loop guard: don't re-run verification triggered by our own Stop hook.
        if payload.get("stop_hook_active"):
            sys.exit(0)

        project_dir = os.environ.get("CLAUDE_PROJECT_DIR", ".")

        try:
            ruff_result = subprocess.run(
                ["ruff", "check", "."],
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=120,
            )
        except FileNotFoundError:
            sys.exit(0)

        if ruff_result.returncode != 0:
            sys.stderr.write(_tail(ruff_result.stdout + ruff_result.stderr))
            sys.exit(2)

        try:
            pytest_result = subprocess.run(
                ["pytest", "-q"],
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=120,
            )
        except FileNotFoundError:
            sys.exit(0)

        if pytest_result.returncode != 0:
            sys.stderr.write(_tail(pytest_result.stdout + pytest_result.stderr))
            sys.exit(2)

        sys.exit(0)
    except Exception:
        # Fail open: a malformed payload must never brick the session.
        sys.exit(0)


if __name__ == "__main__":
    main()
