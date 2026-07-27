# ============================================================
# Ollama 本地模型快速部署 (Windows PowerShell)
#
# 用法: .\deploy\ollama_setup.ps1
#
# 前置: 已安装 Ollama (https://ollama.com/download)
# 效果: 拉取 qwen2.5:3b → 验证可用 → 提示配置 .env
# ============================================================

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Green
Write-Host "  Ollama 本地 LLM 快速部署" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green

# 检查 Ollama 是否安装
$ollama = Get-Command ollama -ErrorAction SilentlyContinue
if (-not $ollama) {
    Write-Host ""
    Write-Host "❌ 未检测到 Ollama" -ForegroundColor Red
    Write-Host "   安装: https://ollama.com/download" -ForegroundColor Yellow
    Write-Host "   Windows: 下载 OllamaSetup.exe 安装" -ForegroundColor Yellow
    Write-Host "   Linux:   curl -fsSL https://ollama.com/install.sh | sh" -ForegroundColor Yellow
    exit 1
}

# 检查 Ollama 服务是否运行
try {
    $resp = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -Method Get -TimeoutSec 5
    Write-Host "  ✅ Ollama 服务已运行" -ForegroundColor Green
} catch {
    Write-Host "  ⚠️  Ollama 服务未启动，尝试启动..." -ForegroundColor Yellow
    Start-Process ollama -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep 3
}

# 拉取模型
$model = "qwen2.5:3b"
Write-Host ""
Write-Host "  ⏳ 拉取模型 $model (约 2GB，首次较慢)..." -ForegroundColor Cyan
ollama pull $model

# 验证
Write-Host ""
Write-Host "  🧪 验证模型..." -ForegroundColor Cyan
$testBody = @{
    model = $model
    messages = @(
        @{role="system"; content="你是档案审核专家。请用 JSON 回复。"}
        @{role="user"; content="审核：关于招生工作的总结报告。共录取本科生1200人。请直接输出 JSON。"}
    )
    stream = $false
    options = @{temperature=0.1; num_predict=256}
} | ConvertTo-Json -Depth 4

try {
    $resp = Invoke-RestMethod -Uri "http://localhost:11434/api/chat" -Method Post -Body $testBody -ContentType "application/json" -TimeoutSec 60
    $content = $resp.message.content
    Write-Host "  ✅ 模型可用！回复: $($content.Substring(0, [Math]::Min(150, $content.Length)))" -ForegroundColor Green
} catch {
    Write-Host "  ⚠️  测试请求失败: $_" -ForegroundColor Yellow
}

# 提示配置
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  部署完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "  修改 .env:" -ForegroundColor White
Write-Host "    LLM_MODE=ollama" -ForegroundColor Cyan
Write-Host '    OLLAMA_URL=http://localhost:11434' -ForegroundColor Cyan
Write-Host "    OLLAMA_MODEL=qwen2.5:3b" -ForegroundColor Cyan
Write-Host ""
Write-Host "  启动系统:" -ForegroundColor White
Write-Host "    .\start.ps1" -ForegroundColor Cyan
Write-Host ""
Write-Host "  其他推荐模型:" -ForegroundColor DarkGray
Write-Host "    qwen2.5:7b  (更大，更准，需 8GB+ 显存)" -ForegroundColor DarkGray
Write-Host "    qwen2.5:14b (最强，需 16GB+ 显存)" -ForegroundColor DarkGray
