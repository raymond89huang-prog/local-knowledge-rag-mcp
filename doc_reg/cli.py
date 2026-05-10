import argparse
import io
import json
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

from .chunker import Chunker
from .config import AppConfig, VaultConfig
from .embedder import Embedder
from .indexer import CheckpointManager, Indexer
from .loaders import LoaderRegistry
from .paths import get_cache_dir, get_doc_reg_home, get_runtime_dir
from .searcher import Searcher
from .store import VectorStore


def _ensure_utf8_stdio():
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    if hasattr(sys.stderr, "buffer"):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")


def _create_components(config: AppConfig):
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
    return cache_dir, store, embedder, chunker


def _selected_vaults(config: AppConfig, vault_name: str | None) -> list[VaultConfig]:
    if vault_name:
        return [config.get_vault(vault_name)]
    return config.list_vaults()


def cmd_index(args):
    config = AppConfig.from_yaml(args.config)
    cache_dir, store, embedder, chunker = _create_components(config)
    for vault in _selected_vaults(config, args.vault):
        indexer = Indexer(
            vault_config=vault,
            embedder=embedder,
            store=store,
            chunker=chunker,
            checkpoint_dir=str(cache_dir / "checkpoints"),
        )
        indexer.index(force=args.force)


def cmd_search(args):
    config = AppConfig.from_yaml(args.config)
    _, store, embedder, _ = _create_components(config)
    searcher = Searcher(store=store, embedder=embedder, min_score=config.search.min_score)

    since_ts = datetime.strptime(args.since, "%Y-%m-%d").timestamp() if args.since else None
    until_ts = datetime.strptime(args.until, "%Y-%m-%d").timestamp() + 86400 if args.until else None
    vault_names = [config.get_vault(args.vault).name] if args.vault else [vault.name for vault in config.list_vaults()]

    results = searcher.search_many(
        query=args.query,
        vault_names=vault_names,
        top_k=args.top_k,
        path_filter=args.path,
        file_type=args.file_type,
        since=since_ts,
        until=until_ts,
    )

    if not results:
        print("No matching documents found.")
        return

    for i, result in enumerate(results, 1):
        print(format_result(i, result, content_limit=800))


def cmd_list_vaults(args):
    config = AppConfig.from_yaml(args.config)
    for vault in config.list_vaults():
        print(f"- {vault.name}")
        print(f"  path: {vault.resolved_path()}")
        if vault.description:
            print(f"  description: {vault.description}")
        print(f"  include: {', '.join(vault.include)}")


def cmd_status(args):
    config = AppConfig.from_yaml(args.config)
    cache_dir = get_cache_dir()
    store = VectorStore(str(cache_dir / "chroma"))
    checkpoint_mgr = CheckpointManager(str(cache_dir / "checkpoints"))

    for vault in _selected_vaults(config, args.vault):
        stats = store.get_stats(vault.name)
        checkpoint = checkpoint_mgr.load(vault.name)
        print(f"Vault: {vault.name}")
        print(f"Path: {vault.resolved_path()}")
        print(f"Indexed chunks: {stats['chunks']}")
        print(f"Indexed files: {len(checkpoint.get('files', {}))}")


def cmd_init(args):
    config_target = Path(args.config).resolve()
    if not config_target.exists():
        template = get_doc_reg_home() / "config.example.yaml"
        if template.exists():
            shutil.copyfile(template, config_target)
            print(f"[OK] Created config template: {config_target}")
        else:
            print(f"[WARN] Config template not found: {template}")

    if args.scope == "user":
        claude_dir = Path.home() / ".claude"
    else:
        claude_dir = Path.cwd() / ".claude"
    mcp_file = claude_dir / "mcp.json"

    doc_reg_home = get_doc_reg_home()

    server_config = {
        "command": "python",
        "args": ["-m", "doc_reg.mcp_server", "--config", str(config_target)],
        "env": {
            "PYTHONIOENCODING": "utf-8",
            "LOCAL_KNOWLEDGE_REG_HOME": str(doc_reg_home),
        },
    }

    # 展示计划配置
    print("=" * 60)
    print("MCP Configuration Plan")
    print("=" * 60)
    print(f"Target file: {mcp_file}")
    print(f"Scope: {args.scope}")
    print(f"Config path: {config_target}")
    print(f"Project home (LOCAL_KNOWLEDGE_REG_HOME): {doc_reg_home}")
    print("")

    # 检测已有配置
    existing_home = None
    if mcp_file.exists():
        try:
            mcp_config = json.loads(mcp_file.read_text(encoding="utf-8"))
            servers = mcp_config.get("mcpServers", {})
            if "local-knowledge-reg" in servers:
                existing = servers["local-knowledge-reg"]
                existing_home = existing.get("env", {}).get("LOCAL_KNOWLEDGE_REG_HOME")
                print("[WARN] local-knowledge-reg already exists in MCP config")
                if existing_home:
                    print(f"       Existing home: {existing_home}")
                    if Path(existing_home).resolve() != doc_reg_home.resolve():
                        print(f"       WARNING: Existing config points to a DIFFERENT location!")
                        print(f"       New home will be: {doc_reg_home}")
                if not args.force:
                    print("")
                    print("Use --force to overwrite, or run from the correct project directory.")
                    print("If unsure, use setup.ps1 instead: .\\setup.ps1")
                    return
                print("[INFO] --force specified, will overwrite existing config")
        except json.JSONDecodeError as e:
            print(f"[ERR] Existing MCP config is not valid JSON: {mcp_file}")
            print(f"      {e}")
            return
    else:
        mcp_config = {}

    # 交互式确认
    if args.confirm and not args.dry_run and not args.print_only:
        print("")
        response = input("Proceed with writing MCP config? [Y/n]: ").strip()
        if response and response.lower() not in ("y", "yes"):
            print("[INFO] Aborted by user")
            return

    servers = mcp_config.setdefault("mcpServers", {})
    servers["local-knowledge-reg"] = server_config

    if args.print_only:
        print(json.dumps({"mcpServers": {"local-knowledge-reg": server_config}}, ensure_ascii=False, indent=2))
        return

    if args.dry_run:
        print(f"[DRY-RUN] Would write MCP config to: {mcp_file}")
        print(json.dumps(mcp_config, ensure_ascii=False, indent=2))
        return

    claude_dir.mkdir(parents=True, exist_ok=True)
    mcp_file.write_text(json.dumps(mcp_config, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] Created MCP config: {mcp_file}")
    print(f"     Scope: {args.scope}")
    print(f"     Config: {config_target}")
    print(f"     Project home: {doc_reg_home}")
    if args.scope == "user":
        print("     This is a user-level MCP config.")
        print("     Restart Claude Code / CCC to load the new configuration.")
    else:
        print("     This is a project-level MCP config.")


def cmd_doctor(args):
    print("=" * 60)
    print("Local Knowledge Reg MCP Doctor")
    print("=" * 60)
    print(f"Install path: {get_doc_reg_home()}")
    print(f"Runtime dir:  {get_runtime_dir()}")
    print(f"Cache dir:    {get_cache_dir()}")
    print(f"Config:       {Path(args.config).resolve()}")

    try:
        config = AppConfig.from_yaml(args.config)
        print("[OK] Config loaded")
    except Exception as e:
        print(f"[ERR] Config failed: {e}")
        return

    registry = LoaderRegistry()
    print(f"[OK] Supported types: {', '.join(sorted(registry.supported_extensions()))}")
    for vault in config.list_vaults():
        path = vault.resolved_path()
        print(f"\nVault: {vault.name}")
        print(f"  Path: {path}")
        print(f"  Description: {vault.description or '(none)'}")
        print(f"  Exists: {'yes' if path.exists() else 'no'}")
        if path.exists():
            matched = []
            for pattern in vault.include:
                matched.extend([p for p in path.rglob(pattern) if p.is_file()])
            print(f"  Matched files before exclude: {len(matched)}")

    try:
        store = VectorStore(str(get_cache_dir() / "chroma"))
        for vault in config.list_vaults():
            print(f"[OK] Chroma collection '{vault.name}': {store.get_stats(vault.name)['chunks']} chunks")
    except Exception as e:
        print(f"[ERR] Chroma failed: {e}")


def cmd_cleanup(args):
    runtime_dir = get_runtime_dir()
    if not runtime_dir.exists():
        print("Runtime directory is empty.")
        return
    print(f"Runtime directory: {runtime_dir}")
    if not args.force:
        print("Add --force to confirm cleanup.")
        return
    shutil.rmtree(runtime_dir, ignore_errors=True)
    print("Runtime data cleaned.")


def cmd_watch(args):
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer

    config = AppConfig.from_yaml(args.config)
    cache_dir, store, embedder, chunker = _create_components(config)
    vaults = _selected_vaults(config, args.vault)
    supported_extensions = LoaderRegistry().supported_extensions()

    class VaultHandler(FileSystemEventHandler):
        def __init__(self, vault: VaultConfig):
            self.vault = vault
            self.last_run = 0.0

        def _should_index(self, event_path: str) -> bool:
            if Path(event_path).suffix.lower() not in supported_extensions:
                return False
            now = time.time()
            if now - self.last_run < 2:
                return False
            self.last_run = now
            return True

        def _index(self):
            Indexer(
                vault_config=self.vault,
                embedder=embedder,
                store=store,
                chunker=chunker,
                checkpoint_dir=str(cache_dir / "checkpoints"),
            ).index()

        def on_modified(self, event):
            if event.is_directory or not self._should_index(event.src_path):
                return
            print(f"\nChanged: {event.src_path}")
            self._index()

        def on_created(self, event):
            self.on_modified(event)

        def on_deleted(self, event):
            if event.is_directory or not self._should_index(event.src_path):
                return
            print(f"\nDeleted: {event.src_path}")
            self._index()

    observer = Observer()
    for vault in vaults:
        path = vault.resolved_path()
        if not path.exists():
            print(f"[WARN] Skip missing vault: {vault.name} -> {path}")
            continue
        observer.schedule(VaultHandler(vault), str(path), recursive=True)
        print(f"Watching vault: {vault.name} -> {path}")

    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\nWatch stopped.")
    observer.join()


def format_result(index: int, result: dict, content_limit: int = 500) -> str:
    metadata = result["metadata"]
    content = result["content"][:content_limit]
    return (
        f"\n{'=' * 60}\n"
        f"[{index}] Score: {result['score']:.3f}\n"
        f"Vault: {metadata.get('vault', 'N/A')}\n"
        f"Title: {metadata.get('title', 'N/A')}\n"
        f"Source: {metadata.get('source', 'N/A')}\n"
        f"Location: {metadata.get('location') or metadata.get('heading', 'N/A')}\n"
        f"Type: {metadata.get('file_type', 'N/A')}\n"
        f"Citation: {metadata.get('citation', metadata.get('source', 'N/A'))}\n"
        f"Content:\n{content}..."
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Local Knowledge Reg MCP CLI")
    parser.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    subparsers = parser.add_subparsers(dest="command")

    p_index = subparsers.add_parser("index", help="Build or update indexes")
    p_index.add_argument("--vault", help="Vault name. Defaults to all vaults.")
    p_index.add_argument("--force", action="store_true", help="Force reindex")

    p_search = subparsers.add_parser("search", help="Search indexed documents")
    p_search.add_argument("query", help="Search query")
    p_search.add_argument("--vault", help="Vault name. Defaults to all vaults.")
    p_search.add_argument("--top-k", type=int, default=5, help="Number of results")
    p_search.add_argument("--path", help="Filter by source path substring")
    p_search.add_argument("--file-type", help="Filter by file type, such as md or pdf")
    p_search.add_argument("--since", help="Filter by modified date, YYYY-MM-DD")
    p_search.add_argument("--until", help="Filter by modified date, YYYY-MM-DD")

    subparsers.add_parser("list-vaults", help="List configured vaults")

    p_status = subparsers.add_parser("status", help="Show index status")
    p_status.add_argument("--vault", help="Vault name. Defaults to all vaults.")

    p_watch = subparsers.add_parser("watch", help="Watch vault files and update indexes")
    p_watch.add_argument("--vault", help="Vault name. Defaults to all vaults.")

    p_cleanup = subparsers.add_parser("cleanup", help="Clean runtime data")
    p_cleanup.add_argument("--force", action="store_true", help="Confirm cleanup")

    p_init = subparsers.add_parser("init", help="Create config template and MCP config")
    p_init.add_argument("--force", action="store_true", help="Overwrite existing MCP config")
    p_init.add_argument(
        "--scope",
        choices=["user", "project"],
        default="user",
        help="Where to write MCP config. Defaults to user-level ~/.claude/mcp.json.",
    )
    p_init.add_argument("--dry-run", action="store_true", help="Print the target MCP config without writing it")
    p_init.add_argument("--print-only", action="store_true", help="Print only the local-knowledge-reg MCP snippet")
    p_init.add_argument("--confirm", action="store_true", help="Ask for confirmation before writing")

    subparsers.add_parser("doctor", help="Diagnose local setup")
    return parser


def main():
    _ensure_utf8_stdio()
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "index":
        cmd_index(args)
    elif args.command == "search":
        cmd_search(args)
    elif args.command == "list-vaults":
        cmd_list_vaults(args)
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
