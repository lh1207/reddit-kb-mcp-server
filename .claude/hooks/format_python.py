#!/usr/bin/env python3
"""PostToolUse hook (Edit|MultiEdit|Write): auto-fix lint issues and format the edited
Python file.

Reads the hook JSON payload from stdin. Exit 0 = pass, exit 2 = block (stderr is fed back
to Claude, e.g. remaining lint errors after --fix). Fails open on any parsing error or if
ruff isn't installed.
"""

import json
import os
import subprocess
import sys


def main() -> None:
    try:
        payload = json.load(sys.stdin)
        file_path = payload.get("tool_input", {}).get("file_path", "") or ""

        if not file_path.endswith(".py") or not os.path.isfile(file_path):
            sys.exit(0)

        try:
            subprocess.run(
                ["ruff", "check", "--fix", file_path],
                capture_output=True,
                text=True,
                timeout=60,
            )
            subprocess.run(
                ["ruff", "format", file_path],
                capture_output=True,
                text=True,
                timeout=60,
            )
            check_result = subprocess.run(
                ["ruff", "check", file_path],
                capture_output=True,
                text=True,
                timeout=60,
            )
        except FileNotFoundError:
            sys.exit(0)

        if check_result.returncode != 0:
            sys.stderr.write(check_result.stdout)
            sys.stderr.write(check_result.stderr)
            sys.exit(2)

        sys.exit(0)
    except Exception:
        # Fail open: a malformed payload must never brick the session.
        sys.exit(0)


if __name__ == "__main__":
    main()
