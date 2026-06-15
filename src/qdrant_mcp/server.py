"""MCP server implementation for Qdrant."""

from __future__ import annotations

import hmac
import json
import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import Any

from fastmcp import FastMCP, settings as fastmcp_settings
from fastmcp.server.transforms.namespace import Namespace

from qdrant_mcp.qdrant_memory import QdrantMemoryClient
from qdrant_mcp.settings import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

qdrant_client: QdrantMemoryClient | None = None


def _read_namespace() -> str | None:
    """Read namespace from --namespace CLI flag or NAMESPACE env (default: qdrant)."""
    for index, arg in enumerate(sys.argv):
        if arg in ("--namespace", "-n") and index + 1 < len(sys.argv):
            value = sys.argv[index + 1].strip()
            return value or None
        if arg.startswith("--namespace="):
            value = arg.split("=", 1)[1].strip()
            return value or None

    value = os.environ.get("NAMESPACE", "qdrant").strip()
    return value or None


NAMESPACE = _read_namespace()
AUTH_BEARER_TOKEN = os.environ.get("AUTH_BEARER_TOKEN", "").strip() or None


@asynccontextmanager
async def lifespan(app: FastMCP):
    """Manage the lifecycle of the Qdrant client."""
    global qdrant_client
    try:
        settings = get_settings()
        qdrant_client = QdrantMemoryClient(settings)
        logger.info("Qdrant MCP server initialized")
        logger.info("Qdrant URL: %s", settings.qdrant_url)
        logger.info("Collection: %s", settings.collection_name)
        logger.info(
            "Embedding: %s / %s",
            settings.embedding_provider,
            settings.embedding_model,
        )
        if NAMESPACE:
            logger.info("Namespace: %s", NAMESPACE)
        yield
    except Exception as e:
        logger.error("Failed to initialize Qdrant client: %s", e)
        raise
    finally:
        if qdrant_client:
            await qdrant_client.close()
            logger.info("Qdrant client closed")


mcp = FastMCP("qdrant-mcp", lifespan=lifespan)


@mcp.tool()
async def store(content: str, metadata: str | None = None, id: str | None = None) -> str:
    """Store information in Qdrant with semantic embeddings.

    Args:
        content: The text content to store
        metadata: Optional JSON string with metadata
        id: Optional ID for the stored item

    Returns:
        ID of the stored item
    """
    global qdrant_client
    if not qdrant_client:
        raise RuntimeError("Qdrant client not initialized")

    metadata_dict = None
    if metadata:
        try:
            metadata_dict = json.loads(metadata)
        except json.JSONDecodeError as exc:
            raise ValueError("Metadata must be valid JSON") from exc

    point_id = await qdrant_client.store(
        content=content,
        metadata=metadata_dict,
        id=id,
    )

    return f"Stored successfully with ID: {point_id}"


@mcp.tool()
async def find(
    query: str,
    limit: int | None = None,
    filter: str | None = None,
    score_threshold: float | None = None,
) -> list[dict[str, Any]]:
    """Find relevant information using semantic search.

    Args:
        query: Search query text
        limit: Maximum number of results to return
        filter: Optional JSON string with filter conditions
        score_threshold: Minimum similarity score (0-1)

    Returns:
        List of matching results with content and metadata
    """
    global qdrant_client
    if not qdrant_client:
        raise RuntimeError("Qdrant client not initialized")

    filter_dict = None
    if filter:
        try:
            filter_dict = json.loads(filter)
        except json.JSONDecodeError as exc:
            raise ValueError("Filter must be valid JSON") from exc

    return await qdrant_client.find(
        query=query,
        limit=limit,
        filter=filter_dict,
        score_threshold=score_threshold,
    )


@mcp.tool()
async def delete(ids: str) -> dict[str, Any]:
    """Delete items from Qdrant by their IDs.

    Args:
        ids: Comma-separated list of IDs to delete

    Returns:
        Deletion result
    """
    global qdrant_client
    if not qdrant_client:
        raise RuntimeError("Qdrant client not initialized")

    id_list = [item.strip() for item in ids.split(",") if item.strip()]

    if not id_list:
        raise ValueError("No IDs provided")

    return await qdrant_client.delete(id_list)


@mcp.tool()
async def list_collections() -> list[str]:
    """List all collections in the Qdrant database.

    Returns:
        List of collection names
    """
    global qdrant_client
    if not qdrant_client:
        raise RuntimeError("Qdrant client not initialized")

    return await qdrant_client.list_collections()


@mcp.tool()
async def collection_info() -> dict[str, Any]:
    """Get information about the current collection.

    Returns:
        Collection statistics and configuration
    """
    global qdrant_client
    if not qdrant_client:
        raise RuntimeError("Qdrant client not initialized")

    return await qdrant_client.get_collection_info()


if NAMESPACE:
    mcp.add_transform(Namespace(NAMESPACE))


async def _send_plain_response(
    send: Any,
    status: int,
    body: bytes,
    headers: list[tuple[bytes, bytes]] | None = None,
) -> None:
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [
                (b"content-type", b"text/plain; charset=utf-8"),
                *(headers or []),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})


class BearerAuthMiddleware:
    """ASGI middleware that requires a static Authorization bearer token."""

    def __init__(self, app: Any, token: str) -> None:
        self.app = app
        self._expected = f"Bearer {token}".encode("utf-8")

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        auth_header = b""
        for name, value in scope.get("headers", []):
            if name.lower() == b"authorization":
                auth_header = value
                break

        if not hmac.compare_digest(auth_header, self._expected):
            await _send_plain_response(
                send,
                401,
                b"Unauthorized",
                [(b"www-authenticate", b"Bearer")],
            )
            return

        await self.app(scope, receive, send)


_http_transport = fastmcp_settings.transport
if _http_transport not in ("http", "streamable-http", "sse"):
    _http_transport = "streamable-http"

mcp_app = mcp.http_app(transport=_http_transport)
app = BearerAuthMiddleware(mcp_app, AUTH_BEARER_TOKEN) if AUTH_BEARER_TOKEN else mcp_app


def main() -> None:
    """Main entry point for the MCP server (stdio transport)."""
    mcp.run()


if __name__ == "__main__":
    import uvicorn

    namespace_note = f" (namespace: {NAMESPACE})" if NAMESPACE else ""
    print(f"Starting qdrant-mcp HTTP server{namespace_note}")
    uvicorn.run(
        "qdrant_mcp.server:app",
        host=fastmcp_settings.host,
        port=fastmcp_settings.port,
        log_level=fastmcp_settings.log_level.lower(),
    )
