"""reddit-kb MCP server: registers search, fetch, and ingest tools with fastmcp."""

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import PlainTextResponse

from tools.fetch_live import fetch_reddit_thread, search_reddit
from tools.ingest import ingest_saved
from tools.search_saved import search_saved

mcp = FastMCP(
    "reddit-kb",
    instructions=(
        "reddit-kb turns a user's saved Reddit content into a searchable local knowledge "
        "base. search_saved is the local semantic index over already-ingested saves — try "
        "it first whenever the user references something they saved, bookmarked, or "
        "half-remember from Reddit. ingest_saved refreshes that index from the user's live "
        "saved-items list; run it if the index looks empty or stale. fetch_reddit_thread "
        "and search_reddit hit live Reddit directly (using the user's session cookie) for "
        "content that was never saved, or that needs to be current."
    ),
)

mcp.tool(search_saved, annotations={"readOnlyHint": True, "openWorldHint": False})
mcp.tool(fetch_reddit_thread, annotations={"readOnlyHint": True, "openWorldHint": True})
mcp.tool(search_reddit, annotations={"readOnlyHint": True, "openWorldHint": True})
mcp.tool(
    ingest_saved,
    annotations={
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)


@mcp.custom_route("/health", methods=["GET"])
async def health(_: Request) -> PlainTextResponse:
    """Liveness check for containerized deployments (HTTP transport only)."""
    return PlainTextResponse("ok")


if __name__ == "__main__":
    mcp.run()
