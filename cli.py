import argparse
import io
import os
import sys
import time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

sys.path.insert(0, str(Path(__file__).parent))

from doc_reg.config import AppConfig
from doc_reg.store import VectorStore
from doc_reg.embedder import Embedder
from doc_reg.chunker import Chunker
from doc_reg.indexer import Indexer
from doc_reg.searcher import Searcher
from doc_reg.paths import get_cache_dir


def cmd_index(args):
    config = AppConfig.from_yaml(args.config)
    vault = config.get_vault(args.vault)
    indexer = _create_indexer(config, vault)
    indexer.index(force=args.force)


def cmd_search(args):
    config = AppConfig.from_yaml(args.config)
    vault = config.get_vault(args.vault)

    cache_dir = get_cache_dir()
    store = VectorStore(str(cache_dir / "chroma"))
    embedder = Embedder(
        model_name=config.embedding.model_name,
        device=config.embedding.device,
        normalize=config.embedding.normalize,
    )
    searcher = Searcher(
        store=store,
        embedder=embedder,
        min_score=config.search.min_score,
    )

    # 解析时间过滤参数
    from datetime import datetime
    since_ts = None
    until_ts = None
    if args.since:
        since_ts = datetime.strptime(args.since, "%Y-%m-%d").timestamp()
    if args.until:
        # until 到当天 23:59:59
        dt = datetime.strptime(args.until, "%Y-%m-%d")
        until_ts = dt.timestamp() + 86400

    results = searcher.search(
        query=args.query,
        vault_name=vault.name,
        top_k=args.top_k,
        path_filter=args.path,
        since=since_ts,
        until=until_ts,
    )

    if not results:
        print("未找到相关文档。")
        return

    for i, r in enumerate(results, 1):
        meta = r["metadata"]
        print(f"\n{'='*60}")
        print(f"[{i}] 相关度: {r['score']:.3f}")
        print(f"标题: {meta.get('title', 'N/A')}")
        print(f"路径: {meta.get('source', 'N/A')}")
        print(f"章节: {meta.get('heading', 'N/A')}")
        print(f"内容:\n{r['content'][:600]}...")


def cmd_status(args):
    config = AppConfig.from_yaml(args.config)
    vault = config.get_vault(args.vault)

    cache_dir = get_cache_dir()
    store = VectorStore(str(cache_dir / "chroma"))
    stats = store.get_stats(vault.name)

    print(f"Vault: {vault.name}")
    print(f"路径: {vault.path}")
    print(f"索引 chunks: {stats['chunks']}")


def _create_indexer(config, vault):
    cache_dir = get_cache_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)

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

    return Indexer(
        vault_config=vault,
        embedder=embedder,
        store=store,
        chunker=chunker,
        checkpoint_dir=str(cache_dir / "checkpoints"),
    )


def _get_mcp_json_path() -> str:
    """返回 local-knowledge-reg MCP 配置所需的 mcp_server.py 和 config.yaml 的绝对路径。"""
    from doc_reg.paths import get_doc_reg_home
    home = get_doc_reg_home()
    return str(home / "doc_reg" / "mcp_server.py"), str(home / "config.yaml")


def cmd_init(args):
    """在当前目录生成 .claude/mcp.json，使当前项目能调用 local-knowledge-reg。"""
    target_dir = Path.cwd()
    claude_dir = target_dir / ".claude"
    mcp_file = claude_dir / "mcp.json"

    if mcp_file.exists() and not args.force:
        print(f"[WARN] {mcp_file} 已存在。")
        print("       使用 --force 覆盖。")
        return

    server_path, config_path = _get_mcp_json_path()
    mcp_config = {
        "mcpServers": {
            "local-knowledge-reg": {
                "command": "python",
                "args": [server_path, "--config", config_path],
                "env": {"PYTHONIOENCODING": "utf-8"},
            }
        }
    }

    claude_dir.mkdir(parents=True, exist_ok=True)
    import json
    mcp_file.write_text(json.dumps(mcp_config, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] 已生成 {mcp_file}")
    print(f"     local-knowledge-reg 服务器: {server_path}")
    print(f"     local-knowledge-reg 配置:   {config_path}")
    print("     重启 VS Code 或 Claude Code 后即可使用 @local-knowledge-reg")


def cmd_doctor(args):
    """诊断 local-knowledge-reg 各组件状态。"""
    from doc_reg.paths import get_doc_reg_home, get_runtime_dir, get_cache_dir
    from doc_reg.store import VectorStore
    from doc_reg.embedder import Embedder
    import json

    print("=" * 60)
    print("Local Knowledge Reg MCP 诊断报告")
    print("=" * 60)

    # 1. 安装路径
    home = get_doc_reg_home()
    print(f"\n[1] 安装路径")
    print(f"    根目录: {home}")
    print(f"    LOCAL_KNOWLEDGE_REG_HOME: {os.environ.get('LOCAL_KNOWLEDGE_REG_HOME', '(未设置)')}")
    print(f"    DOC_REG_HOME: {os.environ.get('DOC_REG_HOME', '(未设置，兼容旧配置)')}")
    ok = (home / "doc_reg" / "mcp_server.py").exists()
    print(f"    {'[OK]' if ok else '[ERR]'} mcp_server.py 存在")

    # 2. 运行时数据
    runtime = get_runtime_dir()
    cache = get_cache_dir()
    print(f"\n[2] 运行时数据")
    print(f"    目录: {runtime}")
    print(f"    {'[OK]' if cache.exists() else '[WARN]'} 缓存目录")

    # 3. 向量库连接
    print(f"\n[3] 向量库 (ChromaDB)")
    try:
        store = VectorStore(str(cache / "chroma"))
        print("    [OK] 连接成功")
    except Exception as e:
        print(f"    [ERR] 连接失败: {e}")

    # 4. 索引状态
    print(f"\n[4] 索引状态")
    try:
        config = AppConfig.from_yaml(args.config)
        default_vault = config.get_vault()
        store = VectorStore(str(cache / "chroma"))
        stats = store.get_stats(default_vault.name)
        print(f"    Vault: {default_vault.name}")
        print(f"    Vault 路径: {default_vault.path}")
        print(f"    Chunks: {stats['chunks']}")

        # 检查检查点
        checkpoint_file = cache / "checkpoints" / f"{default_vault.name}.json"
        if checkpoint_file.exists():
            cp = json.loads(checkpoint_file.read_text(encoding="utf-8"))
            print(f"    已索引文件: {len(cp.get('files', {}))}")
            print(f"    最后更新: {max((v.get('mtime', 0) for v in cp.get('files', {}).values()), default=0)}")
        else:
            print("    [WARN] 尚未建立索引")
    except Exception as e:
        print(f"    [ERR] 获取索引状态失败: {e}")

    # 5. 模型加载
    print(f"\n[5] 嵌入模型")
    try:
        embedder = Embedder(
            model_name=config.embedding.model_name,
            device=config.embedding.device,
            normalize=config.embedding.normalize,
        )
        print(f"    [OK] {config.embedding.model_name} 已加载")
    except Exception as e:
        print(f"    [ERR] 模型加载失败: {e}")

    # 6. 项目级 MCP 配置
    print(f"\n[6] MCP 配置")
    local_mcp = Path.cwd() / ".claude" / "mcp.json"
    global_mcp = Path.home() / ".claude" / "mcp.json"
    if local_mcp.exists():
        print(f"    [OK] 项目级: {local_mcp}")
    elif global_mcp.exists():
        print(f"    [OK] 全局: {global_mcp}")
    else:
        print(f"    [WARN] 未找到 mcp.json。运行 `python cli.py init` 生成。")

    print("\n" + "=" * 60)


def cmd_cleanup(args):
    from doc_reg.paths import get_runtime_dir

    runtime_dir = get_runtime_dir()
    if not runtime_dir.exists():
        print("运行时目录为空，无需清理。")
        return

    print(f"运行时数据目录: {runtime_dir}")
    print(f"  缓存: {runtime_dir / 'cache'}")
    print(f"  日志: {runtime_dir / 'logs'}")

    if not args.force:
        print("\n请添加 --force 确认清理。")
        return

    import shutil
    shutil.rmtree(runtime_dir, ignore_errors=True)
    print("运行时数据已清理。下次启动会自动重建。")


def cmd_watch(args):
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler

    config = AppConfig.from_yaml(args.config)
    vault = config.get_vault(args.vault)

    indexer = _create_indexer(config, vault)

    class VaultHandler(FileSystemEventHandler):
        def __init__(self):
            self.last_run = 0

        def _should_index(self):
            now = time.time()
            if now - self.last_run < 5:
                return False
            self.last_run = now
            return True

        def on_modified(self, event):
            if event.is_directory or not event.src_path.endswith(".md"):
                return
            if self._should_index():
                print(f"\n文件变更: {event.src_path}")
                print("触发增量索引...")
                try:
                    indexer.index()
                    print("索引更新完成。")
                except Exception as e:
                    print(f"索引失败: {e}")

        def on_created(self, event):
            self.on_modified(event)

        def on_deleted(self, event):
            if event.is_directory or not event.src_path.endswith(".md"):
                return
            if self._should_index():
                print(f"\n文件删除: {event.src_path}")
                print("触发增量索引...")
                try:
                    indexer.index()
                    print("索引更新完成。")
                except Exception as e:
                    print(f"索引失败: {e}")

    observer = Observer()
    handler = VaultHandler()
    observer.schedule(handler, str(vault.path), recursive=True)
    observer.start()

    print(f"正在监听 Vault: {vault.path}")
    print("按 Ctrl+C 停止监听")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\n停止监听。")
    observer.join()


def main():
    parser = argparse.ArgumentParser(description="Local Knowledge Reg MCP CLI")
    parser.add_argument("--config", default="config.yaml", help="配置文件路径")

    subparsers = parser.add_subparsers(dest="command")

    p_index = subparsers.add_parser("index", help="建立/更新索引")
    p_index.add_argument("--vault", help="Vault 名称")
    p_index.add_argument("--force", action="store_true", help="强制全量重建")

    p_search = subparsers.add_parser("search", help="搜索文档")
    p_search.add_argument("query", help="搜索关键词")
    p_search.add_argument("--vault", help="Vault 名称")
    p_search.add_argument("--top-k", type=int, default=5, help="返回数量")
    p_search.add_argument("--path", help="按路径过滤，如 '周报/' 或 '测试文档'")
    p_search.add_argument("--since", help="按日期过滤，如 2026-01-01")
    p_search.add_argument("--until", help="按日期过滤，如 2026-05-31")

    p_status = subparsers.add_parser("status", help="查看索引状态")
    p_status.add_argument("--vault", help="Vault 名称")

    p_watch = subparsers.add_parser("watch", help="监听 Vault 文件变化并自动增量索引")
    p_watch.add_argument("--vault", help="Vault 名称")

    p_cleanup = subparsers.add_parser("cleanup", help="清理运行时数据（向量库、检查点、日志）")
    p_cleanup.add_argument("--force", action="store_true", help="确认清理")

    p_init = subparsers.add_parser("init", help="在当前项目目录生成 .claude/mcp.json")
    p_init.add_argument("--force", action="store_true", help="覆盖已有配置")

    p_doctor = subparsers.add_parser("doctor", help="诊断 local-knowledge-reg 各组件状态")
    p_doctor.add_argument("--config", default="config.yaml", help="配置文件路径")

    args = parser.parse_args()

    if args.command == "index":
        cmd_index(args)
    elif args.command == "search":
        cmd_search(args)
    elif args.command == "status":
        cmd_status(args)
    elif args.command == "watch":
        cmd_watch(args)
    elif args.command == "cleanup":
        cmd_cleanup(args)
    elif args.command == "init":
        cmd_init(args)
    elif args.command == "doctor":
        cmd_doctor(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
