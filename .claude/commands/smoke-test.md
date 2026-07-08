---
description: In-memory end-to-end MCP round-trip, offline (no Ollama, no network)
---

Run an in-memory `fastmcp.Client` round-trip against `server.mcp` to verify the full MCP
stack — schemas, annotations, and tool execution — without touching Ollama or the network.
Use a temporary `CHROMA_PATH` so the real vector store is untouched:

```sh
CHROMA_PATH=$(mktemp -d) python3 -c "
import asyncio
import fastmcp
import server

async def main():
    async with fastmcp.Client(server.mcp) as client:
        tools = await client.list_tools()
        print(sorted(t.name for t in tools))
        result = await client.call_tool('search_saved', {'query': 'x'})
        print('search_saved result:', result.data)

asyncio.run(main())
"
```

An empty Chroma collection returns `[]` from `search_saved` before any embedding call is
made, so this exercises the full MCP round-trip (list_tools + call_tool) with zero
external dependencies.

Report the tool list and the `search_saved` result.
