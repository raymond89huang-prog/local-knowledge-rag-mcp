# Local Knowledge Reg MCP

Local Knowledge Reg MCP 是一个面向产品经理和产品团队的本地知识库检索 MCP 服务。它可以索引本地文档目录，并通过 MCP 向 Codex、Claude Code、CCC 等工具提供带来源引用的检索结果，适合在撰写 PRD、方案、周报、复盘、竞品分析时快速查找历史资料。

Git 地址：

```text
https://github.com/raymond89huang-prog/local-knowledge-reg-mcp.git
```

## v0.1 范围

- 支持多个本地知识库目录。
- 支持格式：`.md`、`.markdown`、`.txt`、`.docx`、`.pdf`、`.csv`、`.xlsx`。
- 每个知识库可配置 `include` / `exclude` 规则。
- 支持首次全量索引和后续增量索引。
- 支持监听文件新增、修改、删除。
- 文件变更或删除后会清理旧索引。
- MCP 工具：`search_docs`、`list_vaults`、`reindex`。
- 搜索结果带标题、知识库、来源路径、位置、文件类型、引用信息和内容片段。
- 提供 `doctor` 命令诊断本地配置。

## 推荐使用方式：让 CCC 读取 Git 仓库

可以在 PowerShell 中启动 CCC，然后让 CCC 阅读本仓库的 Git 地址并按说明安装、配置和测试。

推荐做法：

1. 打开 PowerShell。
2. 进入你希望测试 CCC 的另一个项目目录。
3. 启动 CCC。
4. 把下面的 Git 地址发给 CCC：

```text
https://github.com/raymond89huang-prog/local-knowledge-reg-mcp.git
```

可以给 CCC 的提示词示例：

```text
请阅读这个 Git 仓库并帮我在当前机器上接入本地知识库 MCP：
https://github.com/raymond89huang-prog/local-knowledge-reg-mcp.git

MCP 配置需要写入用户级配置。请在安装依赖、创建 config.yaml、写入用户级 MCP 配置、执行首次索引之前，都先向我确认。
不要猜测我的知识库路径，先问我要索引哪个本地目录。
```

### 是否需要管理员 PowerShell

通常不需要。普通 PowerShell 就可以完成：

- 克隆仓库。
- 安装用户级 Python 依赖。
- 创建 `config.yaml`。
- 写入用户级 MCP 配置：`~/.claude/mcp.json`。
- 索引用户有权限读取的本地知识库目录。

只有在以下场景才建议使用“以管理员身份运行”的 PowerShell：

- Python 安装目录或环境需要管理员权限写入。
- 你明确要把项目安装到受保护目录。
- CCC 需要修改受保护位置的配置。
- 你的公司设备策略要求管理员权限安装依赖。

不建议长期用管理员权限运行索引或监听服务，避免误把配置、缓存或索引数据写入管理员用户目录。更推荐使用普通用户权限，并把知识库路径、runtime 路径和用户级 MCP 写入位置都确认清楚。

## 安装

开发模式安装：

```powershell
pip install -e .
```

或者只安装依赖：

```powershell
pip install -r requirements.txt
```

安装后命令：

```powershell
local-knowledge-reg --help
```

如果 Python 用户脚本目录没有加入 `PATH`，可以使用模块方式运行：

```powershell
python -m doc_reg.cli --help
```

## 添加知识库路径

复制配置模板：

```powershell
copy config.example.yaml config.yaml
```

然后编辑 `config.yaml`，把每个 `vaults.<name>.path` 替换成你的本地知识库目录。

示例：

```yaml
vaults:
  product-docs:
    description: "产品需求、方案、会议纪要"
    path: "~/Knowledge/Product"
    include:
      - "**/*.md"
      - "**/*.txt"
      - "**/*.docx"
      - "**/*.pdf"
      - "**/*.csv"
      - "**/*.xlsx"
    exclude:
      - ".obsidian/**"
      - ".claude/**"
      - "~$*.docx"

  research:
    description: "用户研究、竞品报告、访谈记录"
    path: "D:/Knowledge/Research"
    include:
      - "**/*.md"
      - "**/*.docx"
      - "**/*.pdf"
    exclude:
      - "archive/**"
```

`path` 支持以下写法：

- 绝对路径：`D:/Knowledge/Product`
- 用户目录路径：`~/Knowledge/Product`
- 环境变量：`${PRODUCT_KB_PATH}`

`vaults` 下面的每个条目就是一个知识库。需要添加更多知识库时，继续增加新的命名块即可。

不要直接索引过大的目录，例如整个用户目录、桌面、下载目录、云盘根目录或公司同步盘根目录。确实需要这样做时，先认真配置 `exclude`。

## CLI 用法

```powershell
# 查看配置了哪些知识库
local-knowledge-reg list-vaults

# 索引所有知识库
local-knowledge-reg index

# 只索引一个知识库
local-knowledge-reg index --vault product-docs

# 强制重建索引
local-knowledge-reg index --force

# 搜索所有知识库
local-knowledge-reg search "会员体系历史方案"

# 带过滤条件搜索
local-knowledge-reg search "支付成功率" --vault product-docs --file-type pdf --path reports/

# 监听所有知识库
local-knowledge-reg watch

# 诊断本地配置
local-knowledge-reg doctor
```

模块运行方式：

```powershell
python -m doc_reg.cli --config config.yaml search "会员体系历史方案"
```

## MCP 配置

默认生成用户级 MCP 配置：

```powershell
local-knowledge-reg --config config.yaml init
```

默认写入位置：

```text
~/.claude/mcp.json
```

Windows 通常对应：

```text
C:/Users/<你的用户名>/.claude/mcp.json
```

生成的 MCP 服务使用模块启动方式：

```json
{
  "mcpServers": {
    "local-knowledge-reg": {
      "command": "python",
      "args": ["-m", "doc_reg.mcp_server", "--config", "D:/path/to/config.yaml"],
      "env": {
        "PYTHONIOENCODING": "utf-8",
        "LOCAL_KNOWLEDGE_REG_HOME": "D:/path/to/local-knowledge-reg-mcp"
      }
    }
  }
}
```

`init` 会保留已有的其他 MCP server，只新增或更新 `local-knowledge-reg`。如果 `local-knowledge-reg` 已存在，需要显式使用：

```powershell
local-knowledge-reg --config config.yaml init --force
```

只预览不写入：

```powershell
local-knowledge-reg --config config.yaml init --dry-run
```

只打印 MCP 片段：

```powershell
local-knowledge-reg --config config.yaml init --print-only
```

如果确实需要项目级 MCP 配置，可以显式指定：

```powershell
local-knowledge-reg --config config.yaml init --scope project
```

但本项目推荐使用用户级 MCP 配置，避免每个项目重复写一份 MCP 配置。

## Codex / Claude Code / CCC 安装确认事项

当 Codex、Claude Code、CCC 或其他代码代理通过 Git 地址安装或配置本项目时，应该先和用户确认以下事项：

- 要索引哪个本地知识库目录。
- 是否有多个知识库目录需要分别配置为多个 vault。
- `config.yaml` 应该创建或更新到哪里。
- 用户级 MCP 配置文件 `~/.claude/mcp.json` 是否允许写入。
- 如果已经存在 `local-knowledge-reg` MCP server，是否允许替换。
- 是否只展示 MCP 配置片段，而不是直接写入。
- 是否允许安装 Python 依赖。
- 是否允许执行首次全量索引，因为这可能会下载 embedding 模型并扫描本地文档。
- 是否现在启动文件监听，还是让用户后续手动运行。
- 如果机器上已经有其他目录安装过本项目，是否复用已有 runtime，还是为当前项目创建独立 runtime。

代理不应该猜测用户的私人文档路径。对于用户目录、桌面、下载目录、云盘根目录、公司同步盘根目录等范围较大的位置，必须先明确确认。

推荐的首次接入流程：

```text
1. 克隆或打开仓库。
2. 询问用户要索引的知识库路径。
3. 复制 config.example.yaml 为 config.yaml。
4. 只更新用户确认过的 vault path、description、include、exclude。
5. 安装依赖前先确认。
6. 运行 doctor 验证配置。
7. 首次 index 前先确认。
8. 写入用户级 MCP 配置前先确认。
```

当用户接入个人或团队知识库时，Codex 和 CCC 应优先展示计划写入的 `config.yaml` 和用户级 MCP 配置内容，再执行修改。

CCC 跨项目验证清单见：[docs/ccc-test-cases.md](docs/ccc-test-cases.md)。

## 测试

安装开发依赖：

```powershell
pip install -r requirements-dev.txt
```

运行测试：

```powershell
python -m pytest
```

当前测试不会下载 embedding 模型，也不需要真实 ChromaDB 索引。测试覆盖配置加载、loader 行为、索引清理 metadata、搜索过滤和 CCC 安装预期。

## MCP 工具

### `search_docs`

搜索本地已索引文档，返回标题、知识库、来源路径、位置、文件类型、引用信息和内容片段。

参数：

- `query`：必填，检索问题。
- `vault`：可选，指定知识库名。不填时搜索所有知识库。
- `top_k`：可选，返回结果数量。
- `path_filter`：可选，按来源路径子串过滤。
- `file_type`：可选，按文件类型过滤，例如 `md`、`docx`、`pdf`、`csv`、`xlsx`。

### `list_vaults`

列出当前配置的知识库名称、路径和描述。

### `reindex`

对一个或全部知识库执行增量索引。

参数：

- `vault`：可选，指定知识库名。
- `force`：可选，是否强制全量重建。

## Chunking 质量提醒

Codex、Claude Code 和 CCC 应该把 chunking 质量视为检索质量的关键因素。当用户询问 embedding 模型、向量检索质量、RAG 召回、索引或 MCP 文档检索时，代理应先提醒用户：chunk 切分质量可能和模型选择一样重要。

中文和中英混合知识库的建议起点：

- 优先按文档结构切分：标题、段落、列表、表格、代码块。
- 避免在代码块、命令、JSON、YAML、表格和 frontmatter 中间切断。
- 中文文本建议 chunk 大小约 300-800 字，重叠 80-150 字。
- 中英混合技术文本建议约 500-1000 tokens，重叠 100-200 tokens。
- metadata 中保留标题、标题路径、来源路径、文件类型、chunk 序号，方便结果解释和引用。

在下载或引入更大的 embedding 模型前，代理应先询问用户是否需要检查 chunking。不要在用户未确认的情况下重建完整向量索引。

## 运行时数据

生成的数据不会写入源码目录：

- Windows：`%LOCALAPPDATA%/local-knowledge-reg-mcp/`
- Linux/macOS fallback：`~/.local/local-knowledge-reg-mcp/`

运行时目录包含 ChromaDB 数据和 checkpoint。

## Roadmap

见 [ROADMAP.md](ROADMAP.md)。
