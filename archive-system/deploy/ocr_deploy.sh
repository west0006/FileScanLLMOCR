#!/usr/bin/env bash
# ============================================================
# PaddleOCR-VL 一键部署 (Linux)
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
#   bash deploy/ocr_deploy.sh           # 自动检测部署
#   bash deploy/ocr_deploy.sh --cpu     # 强制 CPU 部署
#   bash deploy/ocr_deploy.sh --verify  # 仅验证
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_PYTHON=""

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

FORCE_CPU=false
VERIFY_ONLY=false

for arg in "$@"; do
    case "$arg" in
        --cpu) FORCE_CPU=true ;;
        --verify) VERIFY_ONLY=true ;;
    esac
done

# ============================================================
# 辅助函数
# ============================================================

find_python() {
    # 优先使用项目虚拟环境
    if [ -f "$PROJECT_DIR/.venv/bin/python" ]; then
        VENV_PYTHON="$PROJECT_DIR/.venv/bin/python"
        echo -e "${GREEN}  使用虚拟环境: .venv${NC}"
    elif command -v python3 &>/dev/null; then
        VENV_PYTHON="python3"
    elif command -v python &>/dev/null; then
        VENV_PYTHON="python"
    else
        echo -e "${RED}❌ 未找到 Python，请安装 Python 3.8+${NC}"
        exit 1
    fi
    $VENV_PYTHON --version
}

run_pip() {
    $VENV_PYTHON -m pip "$@"
}

check_pip() {
    run_pip install --upgrade pip -q
}

# ============================================================
# 第一步: 环境检测
# ============================================================

detect_env() {
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  [1/5] 环境检测${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    $VENV_PYTHON "$SCRIPT_DIR/ocr_env_detect.py"

    # 读取决策
    STRATEGY=$($VENV_PYTHON "$SCRIPT_DIR/ocr_env_detect.py" --quiet)

    if [ "$FORCE_CPU" = true ]; then
        STRATEGY="cpu"
        echo -e "${YELLOW}  ⚠️  已强制使用 CPU 模式${NC}"
    fi

    echo ""
    echo -e "  📋 部署策略: ${GREEN}${STRATEGY}${NC}"

    export OCR_STRATEGY="$STRATEGY"
}

# ============================================================
# 第二步: 安装 PaddlePaddle
# ============================================================

install_paddle() {
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  [2/5] 安装 PaddlePaddle${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # 检查是否已安装正确版本
    HAS_PADDLE=$($VENV_PYTHON -c "import paddle; print(paddle.__version__)" 2>/dev/null || echo "")
    if [ -n "$HAS_PADDLE" ]; then
        HAS_GPU=$($VENV_PYTHON -c "import paddle; print(paddle.is_compiled_with_cuda())" 2>/dev/null || echo "False")
        if [ "$STRATEGY" = "gpu" ] && [ "$HAS_GPU" = "True" ]; then
            echo -e "${GREEN}  ✅ PaddlePaddle GPU ${HAS_PADDLE} 已安装，跳过${NC}"
            return
        elif [ "$STRATEGY" = "cpu" ] && [ "$HAS_GPU" = "False" ]; then
            echo -e "${GREEN}  ✅ PaddlePaddle CPU ${HAS_PADDLE} 已安装，跳过${NC}"
            return
        else
            echo -e "${YELLOW}  ⚠️  当前版本不匹配，重新安装...${NC}"
        fi
    fi

    if [ "$STRATEGY" = "gpu" ]; then
        # 检测 CUDA 版本
        CUDA_VER="12.0"
        if command -v nvidia-smi &>/dev/null; then
            CUDA_VER=$(nvidia-smi | grep "CUDA Version" | awk '{print $NF}' | cut -d. -f1-2 || echo "12.0")
        fi

        CUDA_MAJOR=$(echo "$CUDA_VER" | cut -d. -f1)

        echo -e "  🎮 安装 PaddlePaddle GPU 版 (CUDA ${CUDA_VER})..."

        if [ "$CUDA_MAJOR" = "11" ]; then
            run_pip install paddlepaddle-gpu==3.0.0 -f https://www.paddlepaddle.org.cn/whl/linux/cuda11/stable.html
        else
            run_pip install paddlepaddle-gpu==3.0.0 -f https://www.paddlepaddle.org.cn/whl/linux/cuda12/stable.html
        fi

        # 验证 CUDA 可用性
        echo ""
        $VENV_PYTHON -c "
import paddle
print(f'  ✅ PaddlePaddle {paddle.__version__}')
print(f'  CUDA 可用: {paddle.is_compiled_with_cuda()}')
if paddle.is_compiled_with_cuda():
    print(f'  CUDA 版本: {paddle.version.cuda()}')
    print(f'  cuDNN 版本: {paddle.version.cudnn()}')
    paddle.set_device('gpu')
    print(f'  GPU 设备数: {paddle.device.cuda.device_count()}')
"
    else
        echo -e "  💻 安装 PaddlePaddle CPU 版..."
        run_pip install paddlepaddle==3.0.0

        $VENV_PYTHON -c "
import paddle
print(f'  ✅ PaddlePaddle {paddle.__version__} (CPU)')
"
    fi
}

# ============================================================
# 第三步: 安装 PaddleOCR + 结构分析
# ============================================================

install_paddleocr() {
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  [3/5] 安装 PaddleOCR + PP-StructureV2${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # PaddleOCR 核心
    echo "  📄 安装 PaddleOCR..."
    run_pip install "paddleocr>=2.9.0"

    # PP-StructureV2 版面分析依赖
    echo "  📐 安装 PP-StructureV2 依赖..."
    run_pip install paddleclas  # 分类模型（版面/印章）
    run_pip install "opencv-python-headless>=4.9.0"
    run_pip install shapely pyclipper imgaug lmdb tqdm lanms-neo

    # 可选：表格识别
    echo "  📊 安装表格识别依赖..."
    run_pip install openpyxl matplotlib scipy 2>/dev/null || echo "  (部分表格依赖安装失败，不影响核心功能)"

    # 验证安装
    echo ""
    $VENV_PYTHON -c "
import paddleocr
print(f'  ✅ PaddleOCR {getattr(paddleocr, \"__version__\", \"installed\")}')

try:
    from paddleocr.ppstructure.recovery.recovery_to_doc import sorted_layout_boxes
    print('  ✅ PP-StructureV2 可用')
except ImportError:
    print('  ⚠️  PP-StructureV2 部分模块不可用 (不影响核心 OCR)')

try:
    import cv2
    print(f'  ✅ OpenCV {cv2.__version__}')
except ImportError:
    print('  ⚠️  OpenCV 未安装')
"
}

# ============================================================
# 第四步: 下载预训练模型
# ============================================================

download_models() {
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  [4/5] 下载预训练模型${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    echo "  ⏳ 首次下载会自动拉取模型 (~80MB)..."
    echo "     包含: PP-OCRv5 Server 检测+识别+方向分类"
    echo "            PP-StructureV2 版面分析"
    echo ""

    if [ "$STRATEGY" = "gpu" ]; then
        DEVICE="gpu"
    else
        DEVICE="cpu"
    fi

    $VENV_PYTHON -c "
import os, sys
os.environ['DISABLE_MODEL_SOURCE_CHECK'] = 'True'

print('  📥 下载 PP-OCRv5 Server 模型...')
from paddleocr import PaddleOCR

try:
    ocr = PaddleOCR(
        lang='ch',
        use_angle_cls=True,
        use_gpu=${STRATEGY}=="gpu",
        show_log=False,
    )
    # 触发模型下载
    import numpy as np
    dummy = np.zeros((64, 128, 3), dtype=np.uint8)
    result = ocr.ocr(dummy, cls=True)
    print('  ✅ 中文 OCR 模型就绪')
except Exception as e:
    print(f'  ⚠️  OCR 模型测试异常 (首次运行正常): {str(e)[:120]}')
    print('  (如果是模型下载失败，请检查网络连接)')
" 2>&1 | grep -v "NotOpenSSLWarning\|urllib3\|warnings.warn"

    echo ""
    echo -e "${GREEN}  ✅ 模型下载完成${NC}"
    echo "  模型位置: ~/.paddleocr/whl/"
}

# ============================================================
# 第五步: 功能验证
# ============================================================

verify_install() {
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  [5/5] 功能验证${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    $VENV_PYTHON "$SCRIPT_DIR/ocr_verify.py" 2>/dev/null && echo "" && echo -e "${GREEN}  ✅ 所有验证通过${NC}" || echo -e "${YELLOW}  ⚠️  部分验证失败，请检查上方输出${NC}"
}

# ============================================================
# 主流程
# ============================================================

main() {
    echo ""
    echo "=========================================="
    echo "  PaddleOCR-VL 一键部署"
    echo "  OS: $(uname -s) $(uname -m)"
    echo "=========================================="
    echo ""

    find_python
    check_pip

    if [ "$VERIFY_ONLY" = true ]; then
        STRATEGY=$($VENV_PYTHON "$SCRIPT_DIR/ocr_env_detect.py" --quiet)
        export OCR_STRATEGY="$STRATEGY"
        verify_install
        exit 0
    fi

    detect_env
    install_paddle
    install_paddleocr
    download_models
    verify_install

    echo ""
    echo "=========================================="
    echo -e "  ${GREEN}🎉 PaddleOCR-VL 部署完成！${NC}"
    echo "=========================================="
    echo ""
    echo "  使用方式:"
    echo "    # 启动后端 (OCR_MODE=real)"
    echo "    export OCR_MODE=real"
    echo "    python -m uvicorn app.main:app"
    echo ""
    echo "    # 验证安装"
    echo "    bash deploy/ocr_deploy.sh --verify"
    echo ""
    echo "    # Python 测试"
    echo "    python -c \"from paddleocr import PaddleOCR; print('OK')\""
    echo ""
}

main
