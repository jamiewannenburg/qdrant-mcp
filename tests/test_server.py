"""Tests for MCP server namespace behavior."""

from fastmcp import FastMCP
from fastmcp.server.transforms.namespace import Namespace


async def test_namespace_prefixes_tools() -> None:
    mcp = FastMCP("test-namespace", transforms=[Namespace("qdrant")])

    @mcp.tool()
    async def find(query: str) -> str:
        return query

    @mcp.tool()
    async def store(content: str) -> str:
        return content

    tools = await mcp.list_tools()
    assert {tool.name for tool in tools} == {"qdrant_find", "qdrant_store"}


async def test_custom_namespace_prefixes_tools() -> None:
    mcp = FastMCP("test-namespace", transforms=[Namespace("memory")])

    @mcp.tool()
    async def find(query: str) -> str:
        return query

    tools = await mcp.list_tools()
    assert {tool.name for tool in tools} == {"memory_find"}
