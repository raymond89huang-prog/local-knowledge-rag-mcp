import asyncio
import argparse
from pathlib import Path

from mcp.server import Server, NotificationOptions
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from mcp.server.models import InitializationOptions

from .config import AppConfig
from .store import VectorStore
from .embedder import Embedder
from .chunker import Chunker
from .indexer import Indexer
from .searcher import Searcher


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, help="Path to config.yaml")
    args = parser.parse_args()

    config = AppConfig.from_yaml(args.config)

    from .paths import get_cache_dir
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
    searcher = Searcher(
        store=store,
        embedder=embedder,
        min_score=config.search.min_score,
    )

    default_vault = config.get_vault()

    from .paths import get_cache_dir
    _cache_dir = get_cache_dir()
    indexer = Indexer(
        vault_config=default_vault,
        embedder=embedder,
        store=store,
        chunker=chunker,
        checkpoint_dir=str(_cache_dir / "checkpoints"),
    )

    server = Server("local-knowledge-reg")

    @server.list_tools()
    async def list_tools():
        return [
            Tool(
                name="search_docs",
                description="从文档库中检索相关产品文档、周报、规划、指标口径等。支持按路径过滤（如 '周报/' 只搜周报目录）",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "检索意图，用中文自然语言描述",
                        },
                        "vault": {
                            "type": "string",
                            "description": "目标 vault 名称，如不填则使用默认 vault",
                        },
                        "top_k": {
                            "type": "number",
                            "default": 5,
                            "description": "返回结果数量",
                        },
                        "path_filter": {
                            "type": "string",
                            "description": "按路径过滤，如 '周报/' 或 '测试文档'",
                        },
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="reindex",
                description="触发文档库的增量索引更新，新增或修改文件后调用",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "vault": {
                            "type": "string",
                            "description": "目标 vault 名称，如不填则使用默认 vault",
                        },
                    },
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        if name == "search_docs":
            query = arguments.get("query", "")
            vault_name = arguments.get("vault")
            top_k = arguments.get("top_k", config.search.default_top_k)
            path_filter = arguments.get("path_filter")

            if not vault_name:
                vault_name = config.get_vault().name

            try:
                results = searcher.search(
                    query=query,
                    vault_name=vault_name,
                    top_k=int(top_k),
                    path_filter=path_filter,
                )

                if not results:
                    return [TextContent(type="text", text="未找到相关文档。")]

                lines = []
                for i, r in enumerate(results, 1):
                    meta = r["metadata"]
                    lines.append(f"【结果 {i}】相关度: {r['score']:.3f}")
                    lines.append(f"标题: {meta.get('title', 'N/A')}")
                    lines.append(f"路径: {meta.get('source', 'N/A')}")
                    lines.append(f"章节: {meta.get('heading', 'N/A')}")
                    lines.append(f"内容摘要:\n{r['content'][:500]}...")
                    lines.append("")

                return [TextContent(type="text", text="\n".join(lines))]
            except Exception as e:
                return [TextContent(type="text", text=f"检索出错: {str(e)}")]

        elif name == "reindex":
            vault_name = arguments.get("vault")
            target_vault = config.get_vault(vault_name) if vault_name else default_vault

            try:
                _cache = get_cache_dir()
                local_indexer = Indexer(
                    vault_config=target_vault,
                    embedder=embedder,
                    store=store,
                    chunker=chunker,
                    checkpoint_dir=str(_cache / "checkpoints"),
                )
                local_indexer.index()
                return [TextContent(type="text", text=f"Vault '{target_vault.name}' 索引更新完成。")]
            except Exception as e:
                return [TextContent(type="text", text=f"索引更新失败: {str(e)}")]

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
