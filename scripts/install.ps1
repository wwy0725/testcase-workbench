# scripts/install.ps1
# testcase 项目：安装全局 agent 到 `~/.claude/agents/`
# 用途：让新成员 clone repo 后，第一次跑这个脚本就能用上"生成测试用例"/"补充 XMind"等功能
# 幂等：可重复运行，源文件覆盖目标文件

$ErrorActionPreference = 'Stop'

# 解析 repo 根目录（scripts/ 的父目录）
$repoRoot = Split-Path -Parent $PSScriptRoot
$agentsSource = Join-Path $repoRoot 'agents'
$agentsTarget = Join-Path $env:USERPROFILE '.claude\agents'

Write-Host '=== testcase 项目：安装全局 agent ===' -ForegroundColor Cyan
Write-Host "源目录: $agentsSource"
Write-Host "目标目录: $agentsTarget"
Write-Host ''

# 1. 校验源目录
if (-not (Test-Path $agentsSource)) {
    Write-Host "错误: 源目录不存在: $agentsSource" -ForegroundColor Red
    exit 1
}

# 2. 创建目标目录
if (-not (Test-Path $agentsTarget)) {
    new-Item -ItemType Directory -Path $agentsTarget -Force | Out-null
    Write-Host "[创建] 目标目录 $agentsTarget"
} else {
    Write-Host "[存在] 目标目录 $agentsTarget"
}

# 3. 复制所有 .md agent 文件
$copied = 0
Get-ChildItem -Path $agentsSource -Filter '*.md' | ForEach-Object {
    $dest = Join-Path $agentsTarget $_.name
    Copy-Item -Path $_.Fullname -Destination $dest -Force
    Write-Host "  [复制] $($_.name)" -ForegroundColor Green
    $copied++
}

Write-Host ''
Write-Host "完成！共复制 $copied 个 agent 到 $agentsTarget" -ForegroundColor Cyan
Write-Host ''
Write-Host '后续步骤（仅第一次需要）：' -ForegroundColor Yellow
Write-Host '  1. 打开任意内部 CLI 触发 OAuth 登录（任选一个即可）：'
Write-Host '     npx -y --registry=http://npm.dc.servyou-it.com @servyou-ai/17work-cli@latest login'
Write-Host '  2. 启动 Claude Code，说"生成测试用例"或"补充 XMind"即可触发 agent'

