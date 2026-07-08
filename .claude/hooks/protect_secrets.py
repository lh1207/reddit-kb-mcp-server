#!/usr/bin/env python3
"""PreToolUse hook (Bash): block commands that touch .env or the Reddit session cookie.

Reads the hook JSON payload from stdin. Exit 0 = allow, exit 2 = block (stderr is fed
back to Claude as the refusal reason). Fails open on any parsing error.
"""

import json
import re
import sys


def main() -> None:
    try:
        payload = json.load(sys.stdin)
        command = payload.get("tool_input", {}).get("command", "") or ""

        # .env.example is fine to read/reference; strip it before checking for .env
        # itself so "cat .env.example" doesn't trip the .env\b match.
        stripped = command.replace(".env.example", "")

        blocked = bool(re.search(r"\.env\b", stripped)) or "REDDIT_SESSION_COOKIE" in stripped

        if blocked:
            print(
                "blocked: .env / session cookie access — the Reddit session cookie is a "
                "secret; use .env.example for config docs",
                file=sys.stderr,
            )
            sys.exit(2)

        sys.exit(0)
    except Exception:
        # Fail open: a malformed payload must never brick the session.
        sys.exit(0)


if __name__ == "__main__":
    main()
