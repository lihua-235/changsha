# 一键初始化 git 仓库
#
# 前置：先安装 Git for Windows —— https://git-scm.com/download/win
#       安装完成后需重新打开终端，让 PATH 生效。
#
# 用法（在任意目录下执行均可）：
#   powershell -ExecutionPolicy Bypass -File scripts\init-repo.ps1 `
#       -Name "李佳林" -Email "you@example.com"
#
# 脚本会做四件事：
#   1. 检查 git 是否可用
#   2. git init（已存在则跳过）
#   3. 设置本仓库（非全局）的提交身份
#   4. 安全检查 key.txt 未被暂存后，做第一次提交

param(
    [Parameter(Mandatory = $true)][string]$Name,
    [Parameter(Mandatory = $true)][string]$Email
)

$ErrorActionPreference = "Stop"

# 仓库根目录 = 本脚本所在目录的上一级
$Root = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
Set-Location -LiteralPath $Root

Write-Host "仓库根目录：$Root" -ForegroundColor Cyan

# 1. 检查 git
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host ""
    Write-Host "未找到 git。" -ForegroundColor Red
    Write-Host "请先安装 Git for Windows：https://git-scm.com/download/win"
    Write-Host "安装时保持默认选项即可，装完重开终端再运行本脚本。"
    exit 1
}
Write-Host ("git 版本：" + (git --version)) -ForegroundColor Green

# 2. 初始化
if (Test-Path -LiteralPath (Join-Path $Root ".git")) {
    Write-Host "仓库已存在，跳过 git init。" -ForegroundColor Yellow
} else {
    git init | Out-Null
    git branch -M main
    Write-Host "已初始化仓库，默认分支 main。" -ForegroundColor Green
}

# 3. 身份（只影响本仓库，不动全局配置）
git config user.name  $Name
git config user.email $Email
Write-Host "已设置本仓库提交身份：$Name <$Email>" -ForegroundColor Green

# 4. 暂存 + 安全检查
git add -A

$staged = git diff --cached --name-only
if (-not $staged) {
    Write-Host "没有需要提交的改动。" -ForegroundColor Yellow
    exit 0
}

$leak = $staged | Where-Object { $_ -match '(^|/)key\.txt$|\.env' }
if ($leak) {
    Write-Host ""
    Write-Host "已中止：以下敏感文件被暂存，请检查 .gitignore！" -ForegroundColor Red
    $leak | ForEach-Object { Write-Host "  - $_" -ForegroundColor Red }
    git reset | Out-Null
    exit 1
}

Write-Host ""
Write-Host "将要提交的文件：" -ForegroundColor Cyan
$staged | ForEach-Object { Write-Host "  $_" }

git commit -m "chore: 初始化仓库（Phase 0-1 数据管线、分层抽样与标注规范）" | Out-Null
Write-Host ""
Write-Host "首次提交完成。" -ForegroundColor Green
git log --oneline -1

Write-Host ""
Write-Host "下一步（可选）：关联远程仓库并推送" -ForegroundColor Cyan
Write-Host "  git remote add origin https://github.com/<你的用户名>/changsha-food.git"
Write-Host "  git push -u origin main"
