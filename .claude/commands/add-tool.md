---
description: Scaffold a new MCP tool following repo conventions
---

Arguments: `$ARGUMENTS` — the new tool's name and a short description of its purpose.

Scaffold a new tool that follows the conventions in `AGENTS.md`:

1. Create a module in `tools/` (or add to an existing one if it's a natural fit) with:
   - Typed parameters: `Annotated[type, pydantic.Field(description=..., constraints)]` —
     keep schemas flat and primitive (no nested unions) for Gemini function-calling
     compatibility.
   - A `TypedDict` return type (use `typing_extensions.TypedDict`, not `typing.TypedDict`
     — pydantic requires the former on Python < 3.12) with fields matching what the
     function actually returns.
   - A docstring of 3–6 lines: what it does, when the model should choose it over the
     other tools, and any key behavior (side effects, live vs. local, etc.). This
     docstring is the MCP-facing tool description.
   - `raise fastmcp.exceptions.ToolError(...)` at the tool boundary for user-facing
     failures; let `lib/` keep raising `RuntimeError` internally.
2. Register the tool in `server.py` via `mcp.tool(your_tool, annotations={...})` with
   appropriate `readOnlyHint` / `destructiveHint` / `idempotentHint` / `openWorldHint`.
3. Add offline tests in `tests/` that mock at the `lib/` boundary — no network, no Ollama,
   no real Chroma store.
4. Add a row to the tools table in `README.md`.
5. Finish by running `/verify`.
