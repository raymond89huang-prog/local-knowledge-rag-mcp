import argparse
import asyncio

from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from .chunker import Chunker
from .config import AppConfig
from .embedder import Embedder
from .indexer import Indexer
from .paths import get_cache_dir
from .searcher import Searcher
from .store import VectorStore


def _format_result(index: int, result: dict) -> str:
    metadata = result["metadata"]
    return "\n".join(
        [
            f"[Result {index}] score: {result['score']:.3f}",
            f"Vault: {metadata.get('vault', 'N/A')}",
            f"Title: {metadata.get('title', 'N/A')}",
            f"Source: {metadata.get('source', 'N/A')}",
            f"Location: {metadata.get('location') or metadata.get('heading', 'N/A')}",
            f"Type: {metadata.get('file_type', 'N/A')}",
            f"Citation: {metadata.get('citation', metadata.get('source', 'N/A'))}",
            f"Content:\n{result['content'][:700]}...",
        ]
    )


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, help="Path to config.yaml")
    args = parser.parse_args()

    config = AppConfig.from_yaml(args.config)
    cache_dir = get_cache_dir()
    store = VectorStore(str(cache_dir / "chroma"))
    embedder = Embedder(
        model_name=config.embedding.model_name,
        device=config.embedding.device,
        normalize=config.embedding.normalize,
    )
    chunker = Chunker(
        chunk_size=config.chunking.chunk_size,
        chunk_overlap=config.chunking.chunk_overlap,
    )
    searcher = Searcher(store=store, embedder=embedder, min_score=config.search.min_score)
    server = Server("local-knowledge-reg")

    @server.list_tools()
    async def list_tools():
        return [
            Tool(
                name="search_docs",
                description="Search local product knowledge documents with source citations.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Natural language search query."},
                        "vault": {"type": "string", "description": "Optional vault name. Searches all vaults when omitted."},
                        "top_k": {"type": "number", "default": 5, "description": "Number of results."},
                        "path_filter": {"type": "string", "description": "Filter by source path substring."},
                        "file_type": {"type": "string", "description": "Filter by file type, such as md, docx, pdf, csv, xlsx."},
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="list_vaults",
                description="List configured local knowledge vaults.",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="reindex",
                description="Run incremental indexing for one vault or all configured vaults.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "vault": {"type": "string", "description": "Optional vault name. Reindexes all vaults when omitted."},
                        "force": {"type": "boolean", "default": False, "description": "Force a full reindex."},
                    },
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        arguments = arguments or {}

        if name == "list_vaults":
            lines = []
            for vault in config.list_vaults():
                lines.append(f"- {vault.name}: {vault.resolved_path()}")
                if vault.description:
                    lines.append(f"  {vault.description}")
            return [TextContent(type="text", text="\n".join(lines))]

        if name == "search_docs":
            query = arguments.get("query", "")
            vault_name = arguments.get("vault")
            top_k = int(arguments.get("top_k", config.search.default_top_k))
            path_filter = arguments.get("path_filter")
            file_type = arguments.get("file_type")
            vault_names = [config.get_vault(vault_name).name] if vault_name else [vault.name for vault in config.list_vaults()]

            try:
                results = searcher.search_many(
                    query=query,
                    vault_names=vault_names,
                    top_k=top_k,
                    path_filter=path_filter,
                    file_type=file_type,
                )
                if not results:
                    return [TextContent(type="text", text="No matching documents found.")]
                text = "\n\n".join(_format_result(i, result) for i, result in enumerate(results, 1))
                return [TextContent(type="text", text=text)]
            except Exception as e:
                return [TextContent(type="text", text=f"Search failed: {e}")]

        if name == "reindex":
            vault_name = arguments.get("vault")
            force = bool(arguments.get("force", False))
            vaults = [config.get_vault(vault_name)] if vault_name else config.list_vaults()
            try:
                for vault in vaults:
                    Indexer(
                        vault_config=vault,
                        embedder=embedder,
                        store=store,
                        chunker=chunker,
                        checkpoint_dir=str(cache_dir / "checkpoints"),
                    ).index(force=force)
                return [TextContent(type="text", text=f"Indexed {len(vaults)} vault(s).")]
            except Exception as e:
                return [TextContent(type="text", text=f"Indexing failed: {e}")]

        raise ValueError(f"Unknown tool: {name}")

    async with stdio_server(server) as (read_stream, write_stream):
        init_options = InitializationOptions(
            server_name="local-knowledge-reg",
            server_version="0.1.0",
            capabilities=server.get_capabilities(
                notification_options=NotificationOptions(),
                experimental_capabilities={},
            ),
        )
        await server.run(read_stream, write_stream, init_options)


if __name__ == "__main__":
    asyncio.run(main())
