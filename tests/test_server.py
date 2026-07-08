"""Offline tests for server.py tool registration. No network."""

from __future__ import annotations

import asyncio

import server


def _list_tools():
    return asyncio.run(server.mcp.list_tools())


def test_registers_exactly_the_four_expected_tools():
    names = {tool.name for tool in _list_tools()}
    assert names == {"search_saved", "fetch_reddit_thread", "search_reddit", "ingest_saved"}


def test_search_saved_is_read_only_and_closed_world():
    tools_by_name = {tool.name: tool for tool in _list_tools()}
    annotations = tools_by_name["search_saved"].annotations
    assert annotations.readOnlyHint is True
    assert annotations.openWorldHint is False
