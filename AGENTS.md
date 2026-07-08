# AGENTS.md

Rules and context for AI coding agents working on reddit-kb. This file is canonical;
`CLAUDE.md` and `GEMINI.md` are symlinks to it (Codex/Cursor read `AGENTS.md` natively,
Claude Code reads `CLAUDE.md`, Gemini CLI reads `GEMINI.md`). Windows checkouts need
`git config core.symlinks true` (and a re-clone) for the symlinks to resolve; otherwise
read `AGENTS.md` directly.

## Overview + architecture

reddit-kb is a small FastMCP server that turns a user's saved Reddit content into a
searchable local knowledge base.

```
server.py        FastMCP registration only: instructions, tool annotations, /health route
  -> tools/       MCP-facing tools: typed params (Annotated + pydantic.Field), TypedDict
                  results, expanded "when to use" docstrings (these ARE the MCP tool
                  descriptions), raise fastmcp.exceptions.ToolError at the boundary
  -> lib/         reddit.py (cookie-authenticated old.reddit JSON client), embeddings.py
                  (Ollama), chroma.py (persistent vector store) — all raise RuntimeError

Data flow: ingest_saved pulls saved items via lib/reddit.py -> embeds via lib/embeddings.py
-> stores in lib/chroma.py. search_saved embeds a query and does a similarity lookup in
the same store. fetch_reddit_thread/search_reddit go straight to lib/reddit.py, bypassing
the store entirely.
```

## Commands

```sh
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt   # requirements.txt + ruff + pytest

python server.py                      # run locally, stdio transport
docker compose -f docker/docker-compose.yml up --build -d   # run in Docker, HTTP transport

ruff check .                          # lint
ruff format .                         # format
pytest                                # offline test suite
```

## Conventions

- **Lazy imports inside functions in `lib/` are deliberate** (`import requests`,
  `import chromadb`, `import ollama`, `from dotenv import load_dotenv`, etc.) — importing
  the module must not require env vars or heavy deps to be present. Keep this pattern for
  any new `lib/` code.
- **Tool docstrings are user-facing MCP descriptions**, consumed by Claude, Codex, Gemini,
  Cursor, and any other MCP client — the first line matters most. Keep the "when the model
  should choose this tool" guidance; never strip docstrings down to internal-style
  comments.
- **Keep tool parameter and return schemas flat and primitive** (no nested unions) for
  Gemini function-calling compatibility. A new tool must ship: `Annotated[..., Field(...)]`
  params, a `TypedDict` return type (defined via `typing_extensions.TypedDict`, not
  `typing.TypedDict` — pydantic requires the former on Python < 3.12), tool annotations
  registered in `server.py`, offline tests, and a README table row.
- **Error boundary**: tools (`tools/*.py`) raise `fastmcp.exceptions.ToolError` — its
  message reaches MCP clients even with error masking on. `lib/*.py` keeps raising
  `RuntimeError`; tools catch that at the boundary and re-raise as `ToolError`.

## Security (hard rules)

- Never read, print, log, or commit `.env`. It holds `REDDIT_SESSION_COOKIE`, the one real
  secret in this repo, and is gitignored.
- `REDDIT_SESSION_COOKIE` must never appear in logs, error messages, or exception chains.
  See the deliberate non-chaining in `lib/reddit.py::fetch_json`: on a `requests`
  exception, the handler does not chain (`raise ... from exc`) or interpolate the original
  exception, because its repr can carry the cookie via request headers. Preserve that
  pattern in any code that touches the Reddit request.
- `.env.example` is the only environment file that should ever be edited — it documents
  config shape without real values.

## Testing

- Tests are offline-only: no network, no Ollama, no real Chroma store. Mock at the `lib/`
  boundary (`get_saved_items`, `fetch_json`, `embed`, `get_collection`) rather than the
  underlying HTTP/SDK calls.
- Run `pytest` before finishing any change; it must pass with no environment variables set
  other than what individual tests `monkeypatch.setenv`.
