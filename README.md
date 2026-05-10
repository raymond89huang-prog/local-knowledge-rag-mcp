# Local Knowledge Reg MCP

本地知识库 RAG 检索系统。基于 ChromaDB + sentence-transformers 构建，支持语义搜索、增量索引、文件监听自动更新，并通过 MCP (Model Context Protocol) 暴露给 Claude Code / VS Code 使用。

## 特性

- **语义检索**：基于 BAAI/bge-small-zh-v1.5 中文嵌入模型
- **增量索引**：MD5 哈希 + 修改时间检测，只处理变更文件
- **文件监听**：`watch` 命令实时监听 Markdown 文件变化并自动重建索引
- **MCP 集成**：通过 `@local-knowledge-reg` 在 Claude Code 中直接搜索知识库
- **路径过滤**：支持按目录/文件名过滤搜索结果
- **时间过滤**：支持按日期范围过滤（CLI 层）
- **跨项目复用**：一次安装，任意工作目录通过 MCP 调用
- **数据隔离**：向量库、检查点、日志全部存放在系统用户目录，不污染文档库

## 架构

```
doc_reg/
├── config.py       # 配置模型（YAML -> dataclass）
├── parser.py       # Markdown 解析（frontmatter + heading 分块）
├── chunker.py      # 滑动窗口分块
├── embedder.py     # SentenceTransformer 嵌入
├── store.py        # ChromaDB 向量存储封装
├── indexer.py      # 增量索引引擎（检查点管理）
├── searcher.py     # 语义搜索 + 后过滤（路径/分数/时间）
├── paths.py        # 运行时路径管理（%LOCALAPPDATA%/local-knowledge-reg-mcp）
└── mcp_server.py   # MCP 服务器（search_docs / reindex）

cli.py              # CLI 入口（index / search / status / watch / doctor / init / cleanup）
config.example.yaml # 配置文件模板
```

运行时数据目录（自动生成）：
- Windows: `%LOCALAPPDATA%\local-knowledge-reg-mcp\cache\`（向量库 + 检查点）
- Linux/macOS: `~/.local/local-knowledge-reg-mcp/cache/`

## 安装

### 1. 环境要求

- Python >= 3.10
- 首次运行会自动下载嵌入模型（约 100MB）

### 2. 安装依赖

```bash
# 推荐使用国内镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 3. 配置文件

复制模板并根据你的知识库路径修改：

```bash
cp config.example.yaml config.yaml
```

编辑 `config.yaml`：

```yaml
vaults:
  my-vault:
    path: "/path/to/your/obsidian-vault"
    include:
      - "**/*.md"
    exclude:
      - ".obsidian/**"
      - ".claude/**"
      - "local-knowledge-reg-mcp/**"
```

- `vaults.<name>`: 定义一个知识库（可配置多个）
- `path`: 知识库根目录的**绝对路径**
- `include/exclude`: Glob 模式控制索引范围

### 4. 初始化索引

```bash
python cli.py index
```

首次全量索引可能需要几分钟，取决于文档数量。

### 5. 配置 MCP（跨项目使用）

#### 方案 A：全局配置（推荐）

编辑 `~/.claude/mcp.json`（Windows 路径为 `C:\Users\<用户名>\.claude\mcp.json`）：

```json
{
  "mcpServers": {
    "local-knowledge-reg": {
      "command": "python",
      "args": [
        "D:/absolute/path/to/local-knowledge-reg-mcp/doc_reg/mcp_server.py",
        "--config",
        "D:/absolute/path/to/local-knowledge-reg-mcp/config.yaml"
      ],
      "env": {
        "PYTHONIOENCODING": "utf-8",
        "LOCAL_KNOWLEDGE_REG_HOME": "D:/absolute/path/to/local-knowledge-reg-mcp"
      }
    }
  }
}
```

> `LOCAL_KNOWLEDGE_REG_HOME` 指向 local-knowledge-reg-mcp 项目根目录，确保 MCP 服务器能正确定位自身。旧版 `DOC_REG_HOME` 仍兼容。

#### 方案 B：项目级配置

在任意项目目录下运行：

```bash
cd /path/to/other-project
python /path/to/local-knowledge-reg-mcp/cli.py init
```

这会在当前目录生成 `.claude/mcp.json`，仅在该项目生效。

配置完成后，**重启 VS Code 或 Claude Code**，即可通过 `@local-knowledge-reg` 调用搜索。

## CLI 用法

```bash
# 建立/更新索引
python cli.py index
python cli.py index --force        # 强制全量重建
python cli.py index --vault my-vault

# 语义搜索
python cli.py search "风控规则"
python cli.py search "张三" --top-k 10
python cli.py search "周报" --path "周报/"
python cli.py search "项目进展" --since 2026-04-01 --until 2026-05-01

# 查看索引状态
python cli.py status

# 监听文件变化（自动增量索引）
python cli.py watch

# 诊断各组件状态
python cli.py doctor

# 清理运行时数据（向量库、检查点、日志）
python cli.py cleanup --force
```

## MCP 工具

连接成功后，Claude Code 中会暴露两个工具：

### `search_docs`

```
@local-knowledge-reg search_docs query="风控规则最新变更" top_k=5 path_filter="风控/"
```

参数：
- `query` (required): 检索意图，中文自然语言
- `vault`: 目标 vault 名称，默认取 config 中第一个
- `top_k`: 返回结果数量，默认 5
- `path_filter`: 按路径过滤，如 `"周报/"` 只搜周报目录

### `reindex`

```
@local-knowledge-reg reindex vault="my-vault"
```

新增/修改文件后调用，触发增量索引更新。

## 开发

### 目录结构

```
local-knowledge-reg-mcp/
├── cli.py              # CLI 入口
├── requirements.txt    # Python 依赖
├── config.example.yaml # 配置模板
├── README.md           # 本文件
└── doc_reg/            # 核心包
    ├── __init__.py
    ├── config.py
    ├── parser.py
    ├── chunker.py
    ├── embedder.py
    ├── store.py
    ├── indexer.py
    ├── searcher.py
    ├── paths.py
    └── mcp_server.py
```

### 添加新的 CLI 命令

在 `cli.py` 的 `main()` 函数中添加 `subparsers.add_parser(...)`，并在命令分发区添加对应处理逻辑。

### 修改搜索逻辑

`searcher.py` 的 `search()` 方法支持后过滤（路径、分数、时间）。如需新增过滤维度，在此添加并同步更新 `cli.py` 和 `mcp_server.py` 的参数透传。

### 自定义嵌入模型

修改 `config.yaml`：

```yaml
embedding:
  model_name: "BAAI/bge-large-zh-v1.5"
  device: "cpu"
  normalize: true
```

> 首次切换模型时会自动下载。更换模型后建议 `--force` 重建索引。

## 故障排查

### `python cli.py doctor`

一键诊断所有组件：安装路径、缓存目录、向量库连接、索引状态、模型加载、MCP 配置。

### 常见问题

1. **MCP 在 VS Code 中不生效**
   - 检查 `~/.claude/mcp.json` 路径是否为绝对路径
   - 确认 `LOCAL_KNOWLEDGE_REG_HOME` 环境变量设置正确
   - 重启 VS Code 或 Claude Code

2. **索引后搜索无结果**
   - 确认 `config.yaml` 中的 `path` 是绝对路径
   - 运行 `python cli.py doctor` 查看索引状态
   - 确认 `include` 模式能匹配到你的文档

3. **Windows 下中文输出乱码**
   - 已在 `cli.py` 中设置 `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")`
   - 如仍有问题，在 PowerShell 中执行 `[Console]::OutputEncoding = [System.Text.Encoding]::UTF8`

## License

MIT
