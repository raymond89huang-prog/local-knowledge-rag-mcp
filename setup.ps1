#Requires -Version 5.1
<#
.SYNOPSIS
    交互式安装和配置 Local Knowledge Reg MCP。

.DESCRIPTION
    本脚本引导用户完成首次安装：
    1. 检测 Python 环境
    2. 询问知识库路径
    3. 生成 config.yaml
    4. 安装 Python 依赖
    5. 写入用户级 MCP 配置
    6. 执行首次索引
    7. 询问是否开启文件监听

    AI 代理（Codex / Claude Code / CCC）在首次安装时应调用此脚本，
    它会自动交互式询问用户所需信息。

.EXAMPLE
    .\setup.ps1

.EXAMPLE
    .\setup.ps1 -ConfigPath "D:\Knowledge\config.yaml" -SkipMcp
#>
[CmdletBinding()]
param(
    [string]$ConfigPath = "",
    [switch]$SkipMcp,
    [switch]$SkipIndex,
    [switch]$NonInteractive
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# ── 工具函数 ──────────────────────────────────────────────
function Write-Step($n, $total, $msg) {
    Write-Host ""
    Write-Host "[$n/$total] $msg" -ForegroundColor Cyan
    Write-Host ("-" * 60)
}

function Write-Ok($msg) { Write-Host "  [OK] $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "  [WARN] $msg" -ForegroundColor Yellow }
function Write-Err($msg) { Write-Host "  [ERR] $msg" -ForegroundColor Red }

function Read-Input($prompt, $default = "") {
    if ($NonInteractive) { return $default }
    $full = if ($default) { "$prompt (默认: $default): " } else { "$prompt: " }
    Write-Host $full -NoNewline -ForegroundColor White
    $val = Read-Host
    if ([string]::IsNullOrWhiteSpace($val)) { return $default }
    return $val
}

function Read-YesNo($prompt, $default = "Y") {
    if ($NonInteractive) { return $default -eq "Y" }
    $suffix = if ($default -eq "Y") { "[Y/n]" } else { "[y/N]" }
    Write-Host "$prompt $suffix " -NoNewline -ForegroundColor White
    $val = Read-Host
    if ([string]::IsNullOrWhiteSpace($val)) { $val = $default }
    return $val -match "^[Yy]"
}

function Resolve-VaultPath($path) {
    $path = $path.Trim()
    # 支持 ~ 展开
    if ($path.StartsWith("~")) {
        $path = $path.Replace("~", $env:USERPROFILE)
    }
    # 支持环境变量
    $path = [Environment]::ExpandEnvironmentVariables($path)
    return $path
}

function Test-IsSafePath($path) {
    $unsafe = @(
        $env:USERPROFILE,
        [Environment]::GetFolderPath("Desktop"),
        [Environment]::GetFolderPath("Downloads"),
        "$env:USERPROFILE\OneDrive",
        "$env:USERPROFILE\Documents"
    )
    $resolved = (Resolve-Path $path -ErrorAction SilentlyContinue).Path
    if (-not $resolved) { return $true }  # 不存在的路径不拦截
    foreach ($u in $unsafe) {
        if ($u -and ($resolved -eq $u -or $resolved.StartsWith($u + "\"))) {
            return $false
        }
    }
    return $true
}

# ── 步骤 1/7：检测环境 ─────────────────────────────────────
Write-Step 1 7 "检测环境"

$pythonCmd = $null
foreach ($cmd in @("python", "python3", "py")) {
    if (Get-Command $cmd -ErrorAction SilentlyContinue) {
        $pythonCmd = $cmd
        break
    }
}
if (-not $pythonCmd) {
    Write-Err "未找到 Python。请先安装 Python 3.10+ 并确保加入 PATH。"
    exit 1
}
Write-Ok "Python 命令: $pythonCmd"

$pyVersion = & $pythonCmd --version 2>&1
Write-Ok "Python 版本: $pyVersion"

$pipCmd = $null
foreach ($cmd in @("pip", "pip3")) {
    if (Get-Command $cmd -ErrorAction SilentlyContinue) {
        $pipCmd = $cmd
        break
    }
}
if (-not $pipCmd) {
    Write-Warn "未找到 pip，尝试用 python -m pip"
    $pipCmd = "$pythonCmd -m pip"
}
Write-Ok "pip 命令: $pipCmd"

# 项目根目录
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path $scriptDir
Write-Ok "项目目录: $repoRoot"

# ── 步骤 2/7：询问知识库路径 ──────────────────────────────
Write-Step 2 7 "配置知识库"

$vaults = @()
$first = $true
while ($true) {
    if ($first) {
        $msg = "请输入要索引的本地知识库目录路径"
    } else {
        $msg = "是否添加另一个知识库"
    }
    if (-not $first -and -not (Read-YesNo $msg "N")) {
        break
    }

    if (-not $first) { Write-Host "" }
    $rawPath = Read-Input "知识库目录路径" ""
    if ([string]::IsNullOrWhiteSpace($rawPath)) {
        if ($first) {
            Write-Err "必须至少提供一个知识库路径"
            continue
        }
        break
    }

    $resolved = Resolve-VaultPath $rawPath
    if (-not (Test-Path $resolved)) {
        Write-Warn "路径不存在: $resolved"
        if (-not (Read-YesNo "是否仍要使用此路径" "N")) {
            if ($first) { continue } else { break }
        }
    }

    # 安全检查
    if (-not (Test-IsSafePath $resolved)) {
        Write-Warn "你输入的是一个范围较大的目录（如用户目录、桌面、下载、云盘根目录等）"
        Write-Warn "直接索引大目录可能会包含大量无关文件，建议只索引专门的知识库子目录"
        if (-not (Read-YesNo "确认要索引此目录" "N")) {
            if ($first) { continue } else { break }
        }
    }

    $name = Read-Input "知识库名称（英文标识，如 product-docs）" ""
    if ([string]::IsNullOrWhiteSpace($name)) {
        $name = "vault$($vaults.Count + 1)"
        Write-Warn "未提供名称，使用默认值: $name"
    }
    # 清理名称
    $name = $name -replace "[^a-zA-Z0-9_-]", "-"

    $desc = Read-Input "知识库描述" ""
    if ([string]::IsNullOrWhiteSpace($desc)) {
        $desc = "知识库 $name"
    }

    $vaults += @{
        name = $name
        description = $desc
        path = $resolved
    }
    Write-Ok "已添加知识库: $name -> $resolved"
    $first = $false
}

if ($vaults.Count -eq 0) {
    Write-Err "未配置任何知识库，退出"
    exit 1
}

# ── 步骤 3/7：生成 config.yaml ────────────────────────────
Write-Step 3 7 "生成配置文件"

if ([string]::IsNullOrWhiteSpace($ConfigPath)) {
    $defaultConfig = Join-Path $repoRoot "config.yaml"
    $ConfigPath = Read-Input "config.yaml 保存路径" $defaultConfig
}
$ConfigPath = Resolve-Path $ConfigPath -ErrorAction SilentlyContinue
if (-not $ConfigPath) { $ConfigPath = $defaultConfig }

# 读取模板
$templatePath = Join-Path $repoRoot "config.example.yaml"
if (Test-Path $templatePath) {
    $template = Get-Content $templatePath -Raw -Encoding UTF8
} else {
    $template = Get-Content (Join-Path $repoRoot "doc_reg" "config.py") -ErrorAction SilentlyContinue
    if (-not $template) {
        $template = @"
embedding:
  model_name: "BAAI/bge-small-zh-v1.5"
  device: "cpu"
  normalize: true

chunking:
  chunk_size: 400
  chunk_overlap: 50
  respect_headings: true

vaults:

search:
  default_top_k: 5
  min_score: 0.3
"@
    }
}

# 构建 vaults YAML
$vaultsYaml = ""
foreach ($v in $vaults) {
    # 转义 Windows 路径中的反斜杠
    $safePath = $v.path.Replace("\", "/")
    $vaultsYaml += @"
  $($v.name):
    description: "$($v.description)"
    path: "$safePath"
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
      - "local-knowledge-reg-mcp/**"
      - "~`$*.docx"

"@
}

# 替换模板中的 vaults 部分
if ($template -match "(?s)(vaults:.*?)(\n\w+:|$)") {
    $template = $template -replace "(?s)vaults:.*?\n(?=\w+:|$)", "vaults:`n$vaultsYaml`n"
} else {
    # 在文件末尾插入
    $template = $template.TrimEnd() + "`n`nvaults:`n$vaultsYaml"
}

$template | Set-Content $ConfigPath -Encoding UTF8
Write-Ok "已创建配置: $ConfigPath"

# 展示配置内容
Write-Host ""
Write-Host "生成的配置内容:" -ForegroundColor DarkGray
Write-Host (Get-Content $ConfigPath -Raw) -ForegroundColor DarkGray

# ── 步骤 4/7：安装依赖 ────────────────────────────────────
Write-Step 4 7 "安装 Python 依赖"

$reqFile = Join-Path $repoRoot "requirements.txt"
if (Test-Path $reqFile) {
    Write-Host "  执行: $pipCmd install -e `$repoRoot`"
    Push-Location $repoRoot
    try {
        & $pythonCmd -m pip install -e . 2>&1 | ForEach-Object {
            if ($_ -match "error|ERROR|Failed") { Write-Err $_ }
            elseif ($_ -match "warning|WARNING") { Write-Warn $_ }
            else { Write-Host "    $_" -ForegroundColor DarkGray }
        }
    } finally {
        Pop-Location
    }
    Write-Ok "依赖安装完成"
} else {
    Write-Warn "未找到 requirements.txt，跳过依赖安装"
}

# ── 步骤 5/7：写入用户级 MCP 配置 ──────────────────────────
Write-Step 5 7 "配置 MCP"

if (-not $SkipMcp) {
    $mcpFile = Join-Path $env:USERPROFILE ".claude" "mcp.json"
    $mcpExists = Test-Path $mcpFile
    $existingConfig = $null
    $hasConflict = $false

    # 检测已有配置
    if ($mcpExists) {
        try {
            $existingMcp = Get-Content $mcpFile -Raw -Encoding UTF8 | ConvertFrom-Json
            if ($existingMcp.mcpServers.'local-knowledge-reg') {
                $existingConfig = $existingMcp.mcpServers.'local-knowledge-reg'
                $existingHome = $existingConfig.env.'LOCAL_KNOWLEDGE_REG_HOME'
                if ($existingHome -and ($existingHome -ne $repoRoot)) {
                    $hasConflict = $true
                    Write-Warn "检测到已有 local-knowledge-reg MCP 配置，但指向不同位置:"
                    Write-Host "  现有配置指向: $existingHome" -ForegroundColor Yellow
                    Write-Host "  当前项目路径: $repoRoot" -ForegroundColor Yellow
                    Write-Host "  这可能是因为之前在其他目录安装过本项目。" -ForegroundColor Yellow
                } else {
                    Write-Ok "检测到已有 local-knowledge-reg 配置，指向当前项目"
                }
            }
        } catch {
            Write-Warn "无法解析现有 MCP 配置，将尝试覆盖"
        }
    }

    if ($hasConflict) {
        Write-Host ""
        Write-Host "=== 配置冲突 ===" -ForegroundColor Red
        Write-Host "继续使用当前配置会导致 CCC 加载旧位置的 MCP 服务。" -ForegroundColor White
        Write-Host ""
        if (-not (Read-YesNo "是否用当前项目路径覆盖已有配置" "Y")) {
            Write-Warn "保留已有配置，跳过 MCP 写入"
            Write-Host "  注意：CCC 可能继续使用旧位置的 MCP 服务" -ForegroundColor DarkGray
            Write-Host "  如需切换到此项目，请手动删除 `$mcpFile 中的 local-knowledge-reg" -ForegroundColor DarkGray
        } else {
            $forceInit = $true
        }
    }

    if (-not $hasConflict -or ($hasConflict -and $forceInit)) {
        if ($NonInteractive -or (Read-YesNo "是否写入用户级 MCP 配置（~/.claude/mcp.json）" "Y")) {
            Write-Host "  执行: local-knowledge-reg init --scope user --config `"$ConfigPath`" $(if ($forceInit) { '--force' })"
            Push-Location $repoRoot
            try {
                $initArgs = @("-m", "doc_reg.cli", "init", "--scope", "user", "--config", "$ConfigPath")
                if ($forceInit) { $initArgs += "--force" }
                & $pythonCmd @initArgs 2>&1 | ForEach-Object {
                    Write-Host "    $_" -ForegroundColor DarkGray
                }
            } finally {
                Pop-Location
            }
            Write-Ok "MCP 配置已写入"

            # 验证
            if (Test-Path $mcpFile) {
                Write-Ok "配置文件存在: $mcpFile"
                # 展示关键路径信息
                try {
                    $newMcp = Get-Content $mcpFile -Raw -Encoding UTF8 | ConvertFrom-Json
                    $newHome = $newMcp.mcpServers.'local-knowledge-reg'.env.'LOCAL_KNOWLEDGE_REG_HOME'
                    Write-Ok "LOCAL_KNOWLEDGE_REG_HOME: $newHome"
                } catch {
                    Write-Warn "配置已写入但无法验证内容"
                }
            }
        } else {
            Write-Warn "跳过 MCP 配置写入"
            Write-Host "  你可以稍后手动运行:" -ForegroundColor DarkGray
            Write-Host "    local-knowledge-reg init --scope user --config `"$ConfigPath`"" -ForegroundColor DarkGray
        }
    }
} else {
    Write-Warn "跳过 MCP 配置（--SkipMcp 已指定）"
}

# ── 步骤 6/7：执行首次索引 ─────────────────────────────────
Write-Step 6 7 "首次索引"

if (-not $SkipIndex) {
    if ($NonInteractive -or (Read-YesNo "是否立即执行首次全量索引（会下载 embedding 模型并扫描文档）" "Y")) {
        Write-Host "  执行: local-knowledge-reg index --config `"$ConfigPath`""
        Push-Location $repoRoot
        try {
            & $pythonCmd -m doc_reg.cli index --config "$ConfigPath" 2>&1 | ForEach-Object {
                if ($_ -match "error|ERROR|Failed|Exception") { Write-Err $_ }
                elseif ($_ -match "warning|WARNING") { Write-Warn $_ }
                else { Write-Host "    $_" -ForegroundColor DarkGray }
            }
        } finally {
            Pop-Location
        }
        Write-Ok "首次索引完成"
    } else {
        Write-Warn "跳过首次索引"
        Write-Host "  你可以稍后手动运行:" -ForegroundColor DarkGray
        Write-Host "    local-knowledge-reg index --config `"$ConfigPath`"" -ForegroundColor DarkGray
    }
} else {
    Write-Warn "跳过首次索引（--SkipIndex 已指定）"
}

# ── 步骤 7/7：询问文件监听 ─────────────────────────────────
Write-Step 7 7 "文件监听"

if ($NonInteractive) {
    Write-Warn "非交互模式，跳过 watch 配置"
    exit 0
}

Write-Host ""
Write-Host "请选择文件变更监听模式:" -ForegroundColor White
Write-Host "  A. 不开启 — 文档变化后手动运行 reindex（推荐轻量使用）" -ForegroundColor White
Write-Host "  B. 临时开启 — 在当前终端运行 watch，关闭终端后停止" -ForegroundColor White
Write-Host "  C. 常驻开启 — 安装为 Windows 后台任务（适合长期知识库）" -ForegroundColor White
Write-Host ""
$watchChoice = Read-Input "请选择 (A/B/C)" "A"

switch ($watchChoice.ToUpper()) {
    "B" {
        Write-Host ""
        Write-Host "即将在当前终端启动 watch 模式..." -ForegroundColor Cyan
        Write-Host "按 Ctrl+C 停止监听" -ForegroundColor Yellow
        Write-Host ""
        Pause
        Push-Location $repoRoot
        try {
            & $pythonCmd -m doc_reg.cli watch --config "$ConfigPath"
        } finally {
            Pop-Location
        }
    }
    "C" {
        Write-Host ""
        Write-Host "=== 常驻监听任务配置 ===" -ForegroundColor Cyan
        $taskName = Read-Input "任务名称" "LocalKnowledgeReg-Watch"
        $logDir = Read-Input "日志目录" (Join-Path $env:LOCALAPPDATA "local-knowledge-reg-mcp" "logs")
        if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Force -Path $logDir | Out-Null }
        $stdoutLog = Join-Path $logDir "watch-out.log"
        $stderrLog = Join-Path $logDir "watch-err.log"

        Write-Host ""
        Write-Host "任务配置:" -ForegroundColor White
        Write-Host "  任务名称: $taskName" -ForegroundColor White
        Write-Host "  启动命令: $pythonCmd -m doc_reg.cli watch --config `"$ConfigPath`"" -ForegroundColor White
        Write-Host "  配置文件: $ConfigPath" -ForegroundColor White
        Write-Host "  日志目录: $logDir" -ForegroundColor White
        Write-Host "  停止命令: schtasks /Delete /TN `"$taskName`" /F" -ForegroundColor White
        Write-Host "  查看状态: schtasks /Query /TN `"$taskName`"" -ForegroundColor White
        Write-Host ""

        if (Read-YesNo "确认创建此任务" "N") {
            $action = New-ScheduledTaskAction -Execute $pythonCmd -Argument "-m doc_reg.cli watch --config `"$ConfigPath`"" -WorkingDirectory $repoRoot
            $trigger = New-ScheduledTaskTrigger -AtLogOn
            $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
            $principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -RunLevel Limited

            Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force | Out-Null
            Start-ScheduledTask -TaskName $taskName | Out-Null
            Write-Ok "任务已创建并启动: $taskName"
            Write-Host "  查看日志:" -ForegroundColor DarkGray
            Write-Host "    stdout: $stdoutLog" -ForegroundColor DarkGray
            Write-Host "    stderr: $stderrLog" -ForegroundColor DarkGray
        } else {
            Write-Warn "取消创建常驻任务"
        }
    }
    default {
        Write-Ok "选择不开启文件监听"
        Write-Host "  后续可手动运行:" -ForegroundColor DarkGray
        Write-Host "    local-knowledge-reg index --config `"$ConfigPath`"" -ForegroundColor DarkGray
        Write-Host "  或临时监听:" -ForegroundColor DarkGray
        Write-Host "    local-knowledge-reg watch --config `"$ConfigPath`"" -ForegroundColor DarkGray
    }
}

# ── 完成 ──────────────────────────────────────────────────
Write-Host ""
Write-Host "=" * 60 -ForegroundColor Green
Write-Host "  Local Knowledge Reg MCP 安装完成" -ForegroundColor Green
Write-Host "=" * 60 -ForegroundColor Green
Write-Host ""
Write-Host "配置文件: $ConfigPath" -ForegroundColor White
Write-Host ""
Write-Host "常用命令:" -ForegroundColor White
Write-Host "  搜索文档: local-knowledge-reg search `"你的问题`" --config `"$ConfigPath`"" -ForegroundColor DarkGray
Write-Host "  查看知识库: local-knowledge-reg list-vaults --config `"$ConfigPath`"" -ForegroundColor DarkGray
Write-Host "  重新索引: local-knowledge-reg index --config `"$ConfigPath`"" -ForegroundColor DarkGray
Write-Host "  诊断配置: local-knowledge-reg doctor --config `"$ConfigPath`"" -ForegroundColor DarkGray
Write-Host ""
Write-Host "MCP 配置位置: $(Join-Path $env:USERPROFILE '.claude' 'mcp.json')" -ForegroundColor White
Write-Host "请重启 Claude Code / CCC 以加载新的 MCP 配置。" -ForegroundColor Yellow
Write-Host ""
