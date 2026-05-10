"""运行时路径管理——所有生成的数据都放在系统用户目录，不污染代码目录。"""

import os
from pathlib import Path


def get_doc_reg_home() -> Path:
    """返回 local-knowledge-reg-mcp 安装根目录，优先从环境变量读取。"""
    env_home = os.environ.get("LOCAL_KNOWLEDGE_REG_HOME") or os.environ.get("DOC_REG_HOME")
    if env_home:
        return Path(env_home)
    # 回退到当前包所在目录的父目录
    return Path(__file__).parent.parent.resolve()


def get_runtime_dir() -> Path:
    """返回运行时数据根目录：%LOCALAPPDATA%/local-knowledge-reg-mcp/"""
    local_appdata = os.environ.get("LOCALAPPDATA")
    if not local_appdata:
        local_appdata = os.path.expanduser("~/.local")
    return Path(local_appdata) / "local-knowledge-reg-mcp"


def get_cache_dir() -> Path:
    """向量数据库 + 检查点缓存目录"""
    d = get_runtime_dir() / "cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_log_dir() -> Path:
    """日志目录"""
    d = get_runtime_dir() / "logs"
    d.mkdir(parents=True, exist_ok=True)
    return d
