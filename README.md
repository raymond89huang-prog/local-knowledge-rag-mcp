# Local Knowledge Reg MCP

Local Knowledge Reg MCP 是一个面向产品经理和产品团队的本地知识库检索 MCP 服务。它可以索引本地文档目录，并通过 MCP 向 Codex、Claude Code、CCC 等工具提供带来源引用的检索结果，适合在撰写 PRD、方案、周报、复盘、竞品分析时快速查找历史资料。

Git 地址：

```text
https://github.com/raymond89huang-prog/local-knowledge-rag-mcp.git
```

## AI 引导快速开始（推荐）

> **For AI agents / 给 AI 代理阅读：**  
> Before installing or configuring this project, read [AI Installation and Usage Summary](docs/ai-install-summary.md).
>
> This summary is written for Codex, Claude Code, CCC and other MCP-compatible agents. It explains the local RAG / knowledge-base MCP positioning, required `setup.ps1` installation flow, safe configuration rules, supported tools and recommended usage behavior.

如果你是 **Codex、Claude Code 或 CCC**，在帮助用户首次安装本项目时，**必须**使用交互式 setup 脚本完成配置。

> **警告：不要直接运行 `local-knowledge-rag init` 或手动编辑 `~/.claude/mcp.json`。这些方式容易因路径推断错误导致 MCP 配置失效。**

### 唯一推荐方式：setup.ps1

```powershell
# 1. 先进入本项目目录
cd D:\编程项目\local-knowledge-rag-mcp

# 2. 执行交互式安装脚本（必须从此目录运行）
.\setup.ps1
```

脚本会自动：
1. 检测 Python 环境。
2. **询问知识库路径** — 不要猜测，让用户输入要索引的本地目录。
3. 生成 `config.yaml`（展示内容并确认）。
4. 安装 Python 依赖（确认后执行）。
5. **询问是否写入用户级 MCP 配置** — 默认写入 `~/.claude/mcp.json`，保留已有的其他 MCP server。
6. **询问是否执行首次索引** — 因为会下载 embedding 模型并扫描本地文档。
7. **询问文件监听模式**：
   - **A. 不开启**（默认）— 文档变化后手动 `reindex`。
   - **B. 临时开启** — 在当前终端运行 `watch`，关闭后停止。
   - **C. 常驻开启** — 安装为 Windows 计划任务，展示任务名称、命令、配置路径、日志路径、停止和卸载方式，确认后再创建。

### 为什么必须使用 setup.ps1？

`setup.ps1` 会：
- **锁定项目根目录**：确保 MCP 配置中的 `LOCAL_KNOWLEDGE_RAG_HOME` 指向当前仓库目录，不会误指其他位置。
- **检测配置冲突**：如果 `~/.claude/mcp.json` 中已存在 `local-knowledge-rag`，会提示用户确认是更新还是保留。
- **展示并确认**：每一步都展示计划操作，用户确认后才执行。

如果绕过 setup.ps1 直接运行 `python -m doc_rag.cli init`，`init` 命令会通过 `get_doc_rag_home()` 推断项目路径，若从错误目录运行或存在环境变量残留，会导致 MCP 配置指向错误位置，最终 CCC 加载失败。

### AI 代理安装原则

- **绝不猜测用户文档路径**。对于用户目录、桌面、下载、云盘根目录、公司同步盘根目录等，必须先明确询问。
- **必须使用 setup.ps1**。不得建议用户手动运行 `init` 或手动编辑 mcp.json。
- **每步确认**。生成 `config.yaml`、写入 MCP 配置、执行首次索引前，先展示计划内容让用户确认。
- **不得默认创建后台常驻进程**。默认仅执行首次索引和 MCP 配置。
- 如果机器上已有其他目录安装过本项目，询问是复用已有 runtime，还是创建独立 runtime。
- 如果 setup.ps1 不存在，说明仓库未完整克隆，应先检查文件完整性。

### 给用户的 PowerShell 启动方式

1. 打开 PowerShell（通常不需要管理员权限）。
2. 进入本项目目录：
   ```powershell
   cd D:\编程项目\local-knowledge-rag-mcp
   ```
3. 运行交互式安装：
   ```powershell
   .\setup.ps1
   ```
4. 按提示输入知识库路径、确认配置、选择监听模式。
5. 安装完成后，重启 Claude Code / CCC 以加载 MCP。

### 手动安装（不推荐，容易出错）

> 手动安装仅适合深度了解本项目的用户。普通用户请使用 `setup.ps1`。

如果你确实需要手动配置：
1. 必须在本项目目录内执行所有命令。
2. `init` 命令会从当前目录推断路径，**不要在项目目录外运行**。
3. 配置完成后务必运行 `doctor` 验证。
4. 参见下方的[手动 MCP 配置](#手动-mcp-配置)章节。

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
https://github.com/raymond89huang-prog/local-knowledge-rag-mcp.git
```

可以给 CCC 的提示词示例：

```text
请阅读这个 Git 仓库并帮我在当前机器上接入本地知识库 MCP：
https://github.com/raymond89huang-prog/local-knowledge-rag-mcp.git

请严格按以下原则执行：

1. 不要猜测我的知识库路径，先问我要索引哪个本地目录。
2. 必须运行 setup.ps1 交互式脚本完成安装和配置。不要建议我手动运行 init 或手动编辑 mcp.json。
3. 执行 setup.ps1 前，先确认我在正确的项目目录内。
4. 安装依赖、创建或更新 config.yaml、执行首次索引、写入用户级 MCP 配置前，都需要先展示计划并让我确认。
5. 首次索引完成后，询问我是否需要开启文件变更监听：
   A. 不开启，仅手动 reindex
   B. 临时开启 watch
   C. 安装为 Windows 常驻监听任务
6. 如果我选择 C，必须先展示：
   - 任务名称
   - 启动命令
   - config.yaml 路径
   - runtime / 日志路径
   - 如何停止
   - 如何卸载
   我确认后再安装。
7. 不要默认创建后台常驻进程。
8. 配置完成后，运行 doctor 验证配置，并测试 search 命令是否正常工作。
9. 最后告诉我需要重启 CCC 才能加载 MCP。
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

### 交互式安装（推荐）

使用 `setup.ps1` 脚本进行交互式安装，脚本会自动引导你完成配置：

```powershell
.\setup.ps1
```

脚本会依次询问知识库路径、确认配置、选择是否写入 MCP、是否执行首次索引、是否开启文件监听。

支持参数：

```powershell
# 指定配置文件路径
.\setup.ps1 -ConfigPath "D:\Knowledge\config.yaml"

# 跳过 MCP 配置写入
.\setup.ps1 -SkipMcp

# 跳过首次索引
.\setup.ps1 -SkipIndex

# 非交互模式（使用默认值）
.\setup.ps1 -NonInteractive
```

### 手动安装

如果你希望自己手动控制每一步：

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
local-knowledge-rag --help
```

如果 Python 用户脚本目录没有加入 `PATH`，可以使用模块方式运行：

```powershell
python -m doc_rag.cli --help
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
local-knowledge-rag list-vaults

# 索引所有知识库
local-knowledge-rag index

# 只索引一个知识库
local-knowledge-rag index --vault product-docs

# 强制重建索引
local-knowledge-rag index --force

# 搜索所有知识库
local-knowledge-rag search "会员体系历史方案"

# 带过滤条件搜索
local-knowledge-rag search "支付成功率" --vault product-docs --file-type pdf --path reports/

# 监听所有知识库
local-knowledge-rag watch

# 诊断本地配置
local-knowledge-rag doctor
```

模块运行方式：

```powershell
python -m doc_rag.cli --config config.yaml search "会员体系历史方案"
```

## MCP 配置

> **重要：如果你已经运行了 [`setup.ps1`](#交互式安装推荐)，则此步骤已完成，不需要再执行。**

### 手动 MCP 配置（仅当 setup.ps1 不可用时使用）

> 以下命令必须在本项目根目录内执行，否则路径会指向错误位置。

生成用户级 MCP 配置：

```powershell
local-knowledge-rag --config config.yaml init
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
    "local-knowledge-rag": {
      "command": "python",
      "args": ["-m", "doc_rag.mcp_server", "--config", "D:/path/to/config.yaml"],
      "env": {
        "PYTHONIOENCODING": "utf-8",
        "LOCAL_KNOWLEDGE_RAG_HOME": "D:/path/to/local-knowledge-rag-mcp"
      }
    }
  }
}
```

`init` 会保留已有的其他 MCP server，只新增或更新 `local-knowledge-rag`。如果 `local-knowledge-rag` 已存在，需要显式使用：

```powershell
local-knowledge-rag --config config.yaml init --force
```

只预览不写入：

```powershell
local-knowledge-rag --config config.yaml init --dry-run
```

只打印 MCP 片段：

```powershell
local-knowledge-rag --config config.yaml init --print-only
```

如果确实需要项目级 MCP 配置，可以显式指定：

```powershell
local-knowledge-rag --config config.yaml init --scope project
```

但本项目推荐使用用户级 MCP 配置，避免每个项目重复写一份 MCP 配置。

## Codex / Claude Code / CCC 安装确认事项

当 Codex、Claude Code、CCC 或其他代码代理通过 Git 地址安装或配置本项目时，应该先和用户确认以下事项：

- 要索引哪个本地知识库目录。
- 是否有多个知识库目录需要分别配置为多个 vault。
- `config.yaml` 应该创建或更新到哪里。
- 用户级 MCP 配置文件 `~/.claude/mcp.json` 是否允许写入。
- 如果已经存在 `local-knowledge-rag` MCP server，是否允许替换。
- 是否只展示 MCP 配置片段，而不是直接写入。
- 是否允许安装 Python 依赖。
- 是否允许执行首次全量索引，因为这可能会下载 embedding 模型并扫描本地文档。
- 是否开启文件变更监听：
  - 不开启：仅执行首次索引，后续由用户手动运行 `reindex` 或 `local-knowledge-rag index`。
  - 临时开启：在当前终端运行 `local-knowledge-rag watch`，终端关闭后停止。
  - 常驻开启：安装为 Windows 后台任务或开机自启任务，持续监听配置中的知识库目录。
- 如果用户选择常驻监听，必须先展示计划创建的任务名称、启动命令、`config.yaml` 路径、runtime / 日志路径、停止方式和卸载方式，并获得确认后再执行。
- 不得默认创建后台常驻进程。默认应仅执行首次索引和 MCP 配置，让用户后续通过 `reindex` 手动刷新。
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
9. 首次索引和 MCP 配置完成后，再询问用户是否需要开启 watch：
   A. 不开启，仅手动 reindex。
   B. 临时开启，在当前终端运行 watch。
   C. 常驻开启，安装为 Windows 后台任务或开机自启任务。
10. 如果用户选择常驻开启，先展示任务配置、启动命令、配置路径、日志路径、停止方式和卸载方式，确认后再安装。
```

文件监听模式建议：

```text
默认建议：不安装常驻 watch，仅执行首次索引。
适合轻量使用：文档变化后手动 reindex。
适合高频维护知识库：临时开启 watch，观察稳定后再考虑常驻。
适合长期知识库场景：用户明确确认后，再安装常驻 watch。
```

当用户接入个人或团队知识库时，Codex 和 CCC 应优先展示计划写入的 `config.yaml` 和用户级 MCP 配置内容，再执行修改。

CCC 跨项目验证清单见：[docs/ccc-test-cases.md](docs/ccc-test-cases.md)。

## 故障排查

### CCC 中找不到 local-knowledge-rag

在 CCC 中输入 MCP 相关指令时，如果 `local-knowledge-rag` 没有出现在可用工具列表中，按以下顺序排查：

#### 1. 检查用户级 MCP 配置是否存在

```powershell
Get-Content "$env:USERPROFILE\.claude\mcp.json"
```

如果文件不存在，说明 MCP 配置未写入。请重新运行 `setup.ps1`。

#### 2. 检查配置中的路径是否正确

打开 `~/.claude/mcp.json`，确认以下字段：

```json
{
  "mcpServers": {
    "local-knowledge-rag": {
      "command": "python",
      "args": [
        "-m", "doc_rag.mcp_server",
        "--config", "D:\\正确路径\\config.yaml"
      ],
      "env": {
        "PYTHONIOENCODING": "utf-8",
        "LOCAL_KNOWLEDGE_RAG_HOME": "D:\\正确路径\\local-knowledge-rag-mcp"
      }
    }
  }
}
```

常见问题：
- `args` 中的 `--config` 路径是否指向了正确的 `config.yaml`？
- `env.LOCAL_KNOWLEDGE_RAG_HOME` 是否指向了本项目根目录？
- 路径中是否包含乱码或转义错误（如 `\` 写成了 `\` 或 `/`）？

#### 3. 路径指向了旧安装位置

如果之前在其他目录安装过本项目，`mcp.json` 可能仍指向旧位置。解决方式：

```powershell
# 在本项目目录内重新运行 setup.ps1
.\setup.ps1
```

setup.ps1 会检测已有配置并提示是否覆盖。

#### 4. 验证 MCP 服务器能否独立启动

```powershell
python -m doc_rag.mcp_server --config "D:\正确路径\config.yaml"
```

如果此命令报错，说明 Python 依赖未安装或 config.yaml 有问题。

#### 5. 重启 CCC

修改 `~/.claude/mcp.json` 后，必须**重启 CCC** 才能加载新配置。

```powershell
# 在 CCC 中退出
/quit

# 重新启动
claude
```

### 搜索返回空结果

1. 确认知识库目录在 `config.yaml` 中配置正确。
2. 确认已执行首次索引：`local-knowledge-rag index`。
3. 运行 `local-knowledge-rag doctor` 查看索引状态。
4. 检查 `include` 规则是否匹配目标文件类型。

### 索引时提示找不到 embedding 模型

首次索引需要下载 embedding 模型（约 100MB+），请确保：
- 网络连接正常。
- HuggingFace 可访问（国内用户可能需要配置镜像）。
- 磁盘空间充足。

### 配置文件编码问题

Windows PowerShell 默认使用 GBK 编码，可能导致中文路径乱码。解决方法：
- 使用 `setup.ps1`，它会强制设置 UTF-8 编码。
- 或手动设置编码：`[Console]::OutputEncoding = [System.Text.Encoding]::UTF8`

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

- Windows：`%LOCALAPPDATA%/local-knowledge-rag-mcp/`
- Linux/macOS fallback：`~/.local/local-knowledge-rag-mcp/`

运行时目录包含 ChromaDB 数据和 checkpoint。

## Roadmap

见 [ROADMAP.md](ROADMAP.md)。
