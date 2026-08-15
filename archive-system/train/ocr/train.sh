#!/bin/bash
# ============================================================
# PaddleOCR 档案模型微调 — 一键训练脚本
#
# 用法:
#   bash train/ocr/train.sh
#
# 前置条件:
#   1. 已安装 PaddlePaddle + PaddleOCR
#   2. train/data/ocr_train_labels.txt 已准备
#   3. train/data/ocr_val_labels.txt 已准备
# ============================================================

set -e

TRAIN_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$TRAIN_DIR/../.." && pwd)"

echo "=========================================="
echo "  PaddleOCR 档案识别模型 — 微调训练"
echo "=========================================="
echo ""

# --- 1. 检查数据 ---
TRAIN_LABELS="$TRAIN_DIR/../data/ocr_train_labels.txt"
VAL_LABELS="$TRAIN_DIR/../data/ocr_val_labels.txt"

if [ ! -f "$TRAIN_LABELS" ]; then
    echo "❌ 训练标签文件不存在: $TRAIN_LABELS"
    echo "   请先准备标注数据: PPOCRLabel 标注 → 导出 Label.txt"
    exit 1
fi

TRAIN_COUNT=$(wc -l < "$TRAIN_LABELS")
VAL_COUNT=$(wc -l < "$VAL_LABELS" 2>/dev/null || echo 0)
echo "📂 训练集: $TRAIN_COUNT 条"
echo "📂 验证集: $VAL_COUNT 条"

# --- 2. 检查 PaddleOCR ---
if ! python -c "import paddleocr" 2>/dev/null; then
    echo ""
    echo "⚠️  PaddleOCR 未安装，安装中..."
    pip install paddleocr paddlepaddle
fi

# --- 3. 开始训练 ---
CONFIG="$TRAIN_DIR/configs/rec_archive_svtr.yml"
echo ""
echo "🚀 开始训练 (配置: $CONFIG)"
echo "   GPU/NPU 设备: $(python -c 'import paddle; print(paddle.device.get_device())' 2>/dev/null || echo 'CPU')"
echo ""

# tools/train.py 位于 PaddleOCR 仓库内，需先 cd 到仓库根目录（或设置 PADDLEOCR_HOME）
PADDLEOCR_HOME="${PADDLEOCR_HOME:-$HOME/PaddleOCR}"
if [ ! -f "$PADDLEOCR_HOME/tools/train.py" ]; then
    echo "❌ 未找到 $PADDLEOCR_HOME/tools/train.py"
    echo "   请先克隆 PaddleOCR 仓库: git clone https://github.com/PaddlePaddle/PaddleOCR.git"
    echo "   或设置 PADDLEOCR_HOME 指向 PaddleOCR 仓库根目录"
    exit 1
fi

cd "$PADDLEOCR_HOME"
python -m paddle.distributed.launch \
    --log_dir "$TRAIN_DIR/output/logs" \
    tools/train.py \
    -c "$CONFIG" \
    -o Global.epoch_num=100 \
       Optimizer.lr.learning_rate=0.0005

echo ""
echo "✅ 训练完成！模型保存在: $TRAIN_DIR/output/"
echo ""
echo "📋 下一步:"
echo "   python train/ocr/eval.py --predictions eval_results.json --ground_truth $VAL_LABELS"
echo "   导出推理模型: python tools/export_model.py -c $CONFIG"
