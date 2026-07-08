# reddit-kb

MCP server that turns your Reddit content into a searchable knowledge base.
Saved posts/comments are embedded with `nomic-embed-text` (via Ollama) and stored
in ChromaDB; tools are exposed over MCP with fastmcp.

## Purpose

I kept bookmarking useful Reddit comments, the kind with a real answer buried in them,
and wanted to actually reference them later and keep them intact. Reddit's saved list
is basically a junk drawer: no search, no tags, and posts can get edited or deleted
out from under you.

This pulls that content into a local index you control, so a vague memory like
"that thread about Proxmox ghost nodes" can turn into an actual search instead of a
lost cause.

## Authentication

Reddit closed self-service API access in November 2025, so PRAW/OAuth is no
longer an option. Instead, reddit-kb reads the logged-in old.reddit JSON
listing (`old.reddit.com/user/<username>/saved.json`) authenticated with your
browser's `reddit_session` cookie. The cookie lives only in `.env` (gitignored)
and is never logged.

The saved listing is capped by Reddit at roughly the most recent ~1000 items.
If you need older saves, request a [Reddit data export](https://www.reddit.com/settings/data-request)
and backfill from the CSV it provides (not yet automated).

## Tools

| Tool | Purpose |
|---|---|
| `search_saved` | Semantic search over ingested saved content |
| `fetch_reddit_thread` | Fetch a live thread (post + top comments) by URL |
| `search_reddit` | Live Reddit search, optionally scoped to a subreddit |
| `ingest_saved` | Pull saved items, embed them, upsert into ChromaDB |

## Setup

1. Create a venv and install dependencies:

   ```sh
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env`, set `REDDIT_USERNAME`, and paste the
   `reddit_session` cookie value from a logged-in browser session at
   <https://old.reddit.com> into `REDDIT_SESSION_COOKIE`.

3. Pull the embedding model in Ollama:

   ```sh
   ollama pull nomic-embed-text
   ```

4. Run the server:

   ```sh
   python server.py
   ```

   Or run it in Docker — see below.

## Docker

Build and start the container (from the repo root):

```sh
docker compose -f docker/docker-compose.yml up --build -d
```

> **Ollama caveat:** inside the container, `localhost` is the container itself,
> so the bare-metal default `OLLAMA_BASE_URL=http://localhost:11434` will not
> reach the Ollama instance on your host. Before starting, set
> `OLLAMA_BASE_URL` in `.env` to `http://host.docker.internal:11434`
> (provided natively by Docker Desktop and OrbStack on macOS; OrbStack's
> `http://host.orb.internal:11434` also works), or to your host LAN /
> Tailscale IP on Linux. Credentials and config arrive only via `.env` at
> runtime — nothing is baked into the image. Note that changes to `.env`
> require recreating the container (`up -d`), not just restarting it.

Ingest your saved items from inside the container:

```sh
docker compose -f docker/docker-compose.yml exec reddit-kb \
  python -c "from tools.ingest import ingest_saved; print(ingest_saved())"
```

Stop the container:

```sh
docker compose -f docker/docker-compose.yml down
```

The vector store is bind-mounted at `./store/chroma`, so ingested data
persists on the host across restarts and rebuilds.

## Connecting an MCP client

The container serves MCP over streamable HTTP at `http://localhost:8000/mcp`
(there's also a `GET /health` endpoint for container orchestration liveness
checks). Any MCP-compatible client can connect to that endpoint; stdio clients
can run `python server.py` directly instead.

**Claude Code:**

```sh
claude mcp add --transport http reddit-kb http://localhost:8000/mcp
```

**Claude Desktop** (and other clients that read a generic `mcpServers` JSON
block, e.g. Cursor):

```json
{
  "mcpServers": {
    "reddit-kb": {
      "type": "http",
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

**Codex CLI** (`~/.codex/config.toml`) — stdio by default:

```toml
[mcp_servers.reddit-kb]
command = "/path/to/reddit-kb/.venv/bin/python"
args = ["/path/to/reddit-kb/server.py"]
```

Recent Codex releases can also speak to the HTTP endpoint directly:

```toml
[mcp_servers.reddit-kb]
url = "http://localhost:8000/mcp"
```

**Gemini CLI** (`~/.gemini/settings.json`) — HTTP:

```json
{
  "mcpServers": {
    "reddit-kb": {
      "httpUrl": "http://localhost:8000/mcp"
    }
  }
}
```

or stdio:

```json
{
  "mcpServers": {
    "reddit-kb": {
      "command": "/path/to/reddit-kb/.venv/bin/python",
      "args": ["/path/to/reddit-kb/server.py"]
    }
  }
}
```

**Cursor** (`.cursor/mcp.json`, project-local, or the global equivalent):

```json
{
  "mcpServers": {
    "reddit-kb": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

## Development

Agent rules live in [`AGENTS.md`](AGENTS.md) (canonical; `CLAUDE.md` and
`GEMINI.md` are symlinks to it — Windows checkouts need
`git config core.symlinks true`).

Install dev dependencies (adds `ruff` and `pytest` on top of `requirements.txt`):

```sh
pip install -r requirements-dev.txt
```

```sh
ruff check .           # lint
ruff format .          # format
pytest                 # offline test suite — no network, no Ollama, no real Chroma store
```

Claude Code hooks under `.claude/hooks/` protect `.env`/the session cookie
from being read or printed, auto-format edited Python files, and re-run
lint + tests before a session is allowed to stop. Slash commands:
`/verify` (lint + format-check + tests + an offline server smoke check),
`/smoke-test` (in-memory MCP client round-trip), and `/add-tool` (scaffold a
new tool following repo conventions). CI (`.github/workflows/ci.yml`) runs
the same lint/format/test checks on every push to `main` and every pull
request.

## Layout

- `server.py` — FastMCP server; registers the four tools (stdio locally, HTTP
  in Docker) and a `/health` route
- `lib/reddit.py` — cookie-authenticated old.reddit JSON listing client
- `lib/embeddings.py` — `embed` / `embed_batch` against the Ollama API
- `lib/chroma.py` — persistent collection at `CHROMA_PATH`
- `tools/ingest.py` — saved items → embeddings → ChromaDB
- `tools/search_saved.py` — query embedding → ChromaDB similarity search
- `tools/fetch_live.py` — live thread fetch + live Reddit search
- `tests/` — offline pytest suite (mocks `lib/` boundaries)
- `docker/` — Dockerfile + compose for the containerised HTTP server
- `.claude/` — hooks and slash commands for Claude Code (see Development)
- `AGENTS.md` — canonical agent rules (`CLAUDE.md`/`GEMINI.md` are symlinks)
- `.github/workflows/` — CI (lint, format-check, tests)
