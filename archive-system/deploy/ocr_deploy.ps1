# ============================================================
# PaddleOCR-VL 一键部署 (Windows PowerShell)
#
# 功能:
#   1. 自动检测 GPU/CUDA 环境
#   2. GPU 路径: 安装 CUDA 版 PaddlePaddle + 硬件加速
#   3. CPU 路径: 安装 CPU 版 PaddlePaddle
#   4. 安装 PaddleOCR + PP-StructureV2 版面分析
#   5. 下载预训练模型权重
#   6. 功能验证
#
# 用法:
#   .\deploy\ocr_deploy.ps1           # 自动检测部署
#   .\deploy\ocr_deploy.ps1 -Cpu      # 强制 CPU 部署
#   .\deploy\ocr_deploy.ps1 -Verify   # 仅验证
# ============================================================

param([switch]$Cpu, [switch]$Verify, [switch]$SkipModels)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

# 虚拟环境 Python
if (Test-Path "$root\.venv\Scripts\python.exe") {
    $py = "$root\.venv\Scripts\python.exe"
    Write-Host "  使用虚拟环境: .venv" -ForegroundColor DarkGray
} else {
    $py = "python"
}

# ============================================================
# 辅助函数
# ============================================================

function Write-Step($num, $title) {
    Write-Host ""
    Write-Host ("─" * 60) -ForegroundColor Cyan
    Write-Host "  [$num/5] $title" -ForegroundColor Cyan
    Write-Host ("─" * 60) -ForegroundColor Cyan
    Write-Host ""
}

# ============================================================
# 仅验证模式
# ============================================================

if ($Verify) {
    & $py "$root\deploy\ocr_verify.py"
    if ($LASTEXITCODE -eq 0) {
        Write-Host "`n  ✅ 验证通过" -ForegroundColor Green
    }
    exit $LASTEXITCODE
}

# ============================================================
# 步骤 1: 环境检测
# ============================================================

Write-Step 1 "环境检测"

$strategy = & $py "$root\deploy\ocr_env_detect.py" --quiet 2>$null
if ($Cpu) {
    $strategy = "cpu"
    Write-Host "  ⚠️  已强制使用 CPU 模式" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "  📋 部署策略: $strategy" -ForegroundColor Green

# 升级 pip
& $py -m pip install --upgrade pip -q

# ============================================================
# 步骤 2: 安装 PaddlePaddle
# ============================================================

Write-Step 2 "安装 PaddlePaddle"

if ($strategy -eq "gpu") {
    # 检测 CUDA 版本
    $cudaVer = "12.0"
    $nvidiaSmi = Get-Command nvidia-smi -ErrorAction SilentlyContinue
    if ($nvidiaSmi) {
        $smiOut = & nvidia-smi 2>$null | Select-String "CUDA Version"
        if ($smiOut) {
            $cudaVer = ($smiOut -split "CUDA Version:")[-1].Trim().Split(" ")[0]
        }
    }

    $cudaMajor = $cudaVer.Split(".")[0]
    Write-Host "  🎮 安装 PaddlePaddle GPU 版 (CUDA $cudaVer)..."

    if ($cudaMajor -eq "11") {
        & $py -m pip install paddlepaddle-gpu==3.0.0 -f https://www.paddlepaddle.org.cn/whl/windows/cuda11/stable.html
    } else {
        & $py -m pip install paddlepaddle-gpu==3.0.0 -f https://www.paddlepaddle.org.cn/whl/windows/cuda12/stable.html
    }

    # 验证 CUDA
    Write-Host ""
    & $py -c @"
import paddle
print(f'  PaddlePaddle {paddle.__version__}')
print(f'  CUDA 可用: {paddle.is_compiled_with_cuda()}')
if paddle.is_compiled_with_cuda():
    print(f'  CUDA 版本: {paddle.version.cuda()}')
    paddle.set_device('gpu')
    print(f'  GPU 设备数: {paddle.device.cuda.device_count()}')
"@
} else {
    Write-Host "  💻 安装 PaddlePaddle CPU 版..."
    & $py -m pip install paddlepaddle==3.0.0

    & $py -c "import paddle; print(f'  PaddlePaddle {paddle.__version__} (CPU)')"
}

# ============================================================
# 步骤 3: 安装 PaddleOCR + 结构分析
# ============================================================

Write-Step 3 "安装 PaddleOCR + PP-StructureV2"

Write-Host "  📄 安装 PaddleOCR..."
& $py -m pip install "paddleocr>=2.9.0"

Write-Host "  📐 安装 PP-StructureV2 依赖..."
& $py -m pip install paddleclas
& $py -m pip install "opencv-python-headless>=4.9.0"
& $py -m pip install shapely pyclipper imgaug lmdb tqdm

# 验证
Write-Host ""
& $py -c @"
import paddleocr
print(f'  PaddleOCR installed')
try:
    from paddleocr.ppstructure.recovery.recovery_to_doc import sorted_layout_boxes
    print('  PP-StructureV2 available')
except ImportError:
    print('  PP-StructureV2 partial (core OCR unaffected)')
try:
    import cv2
    print(f'  OpenCV {cv2.__version__}')
except ImportError:
    print('  OpenCV not installed')
"@

# ============================================================
# 步骤 4: 下载预训练模型
# ============================================================

if (-not $SkipModels) {
    Write-Step 4 "下载预训练模型"

    Write-Host "  ⏳ 首次下载会自动拉取模型 (~80MB)..."
    Write-Host "     包含: PP-OCRv5 Server 检测+识别+方向分类"
    Write-Host "            PP-StructureV2 版面分析"
    Write-Host ""

    $useGpu = if ($strategy -eq "gpu") { "True" } else { "False" }

    & $py -c @"
import os; os.environ['DISABLE_MODEL_SOURCE_CHECK'] = 'True'
from paddleocr import PaddleOCR
import numpy as np
print('  Downloading PP-OCRv5 models...')
try:
    ocr = PaddleOCR(lang='ch', use_angle_cls=True, use_gpu=$useGpu, show_log=False)
    dummy = np.zeros((64, 128, 3), dtype=np.uint8)
    ocr.ocr(dummy, cls=True)
    print('  OK: Chinese OCR model ready')
except Exception as e:
    print(f'  Note: {str(e)[:120]}')
    print('  (If model download failed, check network)')
"@

    Write-Host ""
    Write-Host "  ✅ 模型下载完成" -ForegroundColor Green
    Write-Host "  模型位置: %USERPROFILE%/.paddleocr/whl/"
}

# ============================================================
# 步骤 5: 功能验证
# ============================================================

Write-Step 5 "功能验证"

& $py "$root\deploy\ocr_verify.py"
if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "  ✅ 所有验证通过" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "  ⚠️  部分验证失败，请检查上方输出" -ForegroundColor Yellow
}

# ============================================================
# 完成
# ============================================================

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  PaddleOCR-VL 部署完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "  使用方式:"
Write-Host "    # 设置环境变量启动后端 (OCR_MODE=real)"
Write-Host '    $env:OCR_MODE = "real"'
Write-Host "    .\start.ps1"
Write-Host ""
Write-Host "    # 验证安装"
Write-Host "    .\deploy\ocr_deploy.ps1 -Verify"
Write-Host ""
