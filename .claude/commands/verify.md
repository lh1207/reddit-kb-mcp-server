---
description: Run lint, format-check, tests, and an offline server smoke check
---

Run these checks, in order, and report pass/fail for each step. If any step fails, fix
the issue and re-run that step (and any earlier steps it could have affected) before
reporting done.

1. `ruff check .`
2. `ruff format --check .`
3. `pytest`
4. Offline server smoke check (no network, no Ollama, no real Chroma store):
   ```sh
   CHROMA_PATH=$(mktemp -d) python3 -c "
   import asyncio, server
   ts = asyncio.run(server.mcp.list_tools())
   names = sorted(t.name for t in ts)
   print(names)
   assert set(names) == {'search_saved', 'fetch_reddit_thread', 'search_reddit', 'ingest_saved'}
   "
   ```

Report each step's result. Do not consider the task finished until all four pass.
