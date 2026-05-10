import os
from pathlib import Path


def get_doc_reg_home() -> Path:
    env_home = os.environ.get("LOCAL_KNOWLEDGE_REG_HOME") or os.environ.get("DOC_REG_HOME")
    if env_home:
        return Path(env_home).resolve()
    return Path(__file__).parent.parent.resolve()


def get_runtime_dir() -> Path:
    local_appdata = os.environ.get("LOCALAPPDATA")
    if not local_appdata:
        local_appdata = os.path.expanduser("~/.local")
    return Path(local_appdata) / "local-knowledge-reg-mcp"


def get_cache_dir() -> Path:
    directory = get_runtime_dir() / "cache"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def get_log_dir() -> Path:
    directory = get_runtime_dir() / "logs"
    directory.mkdir(parents=True, exist_ok=True)
    return directory
