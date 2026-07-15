"""
OCR 模型评估脚本

用法:
  python train/ocr/eval.py --model ./train/ocr/output/best_accuracy --test_data ./train/data/ocr_test_labels.txt

输出: 字符准确率、编辑距离、按档案类型的细分评估
"""

import argparse
import json
import sys
from pathlib import Path
from collections import defaultdict


def char_accuracy(pred: str, gt: str) -> float:
    """字符级准确率"""
    if not gt:
        return 1.0 if not pred else 0.0
    correct = sum(1 for p, g in zip(pred, gt) if p == g)
    return correct / max(len(pred), len(gt))


def edit_distance_ratio(pred: str, gt: str) -> float:
    """归一化编辑距离 (0=完全相同, 1=完全不同)"""
    try:
        from Levenshtein import distance
        d = distance(pred, gt)
        return d / max(len(pred), len(gt), 1)
    except ImportError:
        # 简易编辑距离
        return _simple_edit_distance(pred, gt) / max(len(pred), len(gt), 1)


def _simple_edit_distance(a: str, b: str) -> int:
    m, n = len(a), len(b)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            dp[i][j] = min(
                dp[i - 1][j] + 1,
                dp[i][j - 1] + 1,
                dp[i - 1][j - 1] + (0 if a[i - 1] == b[j - 1] else 1),
            )
    return dp[m][n]


def evaluate(predictions: list[dict], ground_truth: dict[str, str]) -> dict:
    """评估 OCR 模型"""
    results = {
        "total": len(predictions),
        "char_accuracy": 0.0,
        "edit_distance_norm": 0.0,
        "by_type": defaultdict(lambda: {"count": 0, "acc": 0.0, "edit": 0.0}),
        "low_confidence": [],
    }

    total_acc = 0.0
    total_edit = 0.0

    for pred in predictions:
        img_path = pred.get("image_path", "")
        pred_text = pred.get("text", "")
        confidence = pred.get("confidence", 0)
        doc_type = pred.get("doc_type", "unknown")

        gt_text = ground_truth.get(img_path, "")

        acc = char_accuracy(pred_text, gt_text)
        edit = edit_distance_ratio(pred_text, gt_text)

        total_acc += acc
        total_edit += edit

        results["by_type"][doc_type]["count"] += 1
        results["by_type"][doc_type]["acc"] += acc
        results["by_type"][doc_type]["edit"] += edit

        if confidence < 0.7:
            results["low_confidence"].append({
                "image": img_path,
                "pred": pred_text,
                "gt": gt_text,
                "confidence": confidence,
            })

    n = len(predictions)
    if n > 0:
        results["char_accuracy"] = round(total_acc / n, 4)
        results["edit_distance_norm"] = round(total_edit / n, 4)

    # 各类别平均
    for t in results["by_type"]:
        cnt = results["by_type"][t]["count"]
        results["by_type"][t]["acc"] = round(results["by_type"][t]["acc"] / cnt, 4) if cnt else 0
        results["by_type"][t]["edit"] = round(results["by_type"][t]["edit"] / cnt, 4) if cnt else 0

    return results


def print_report(results: dict):
    """打印评估报告"""
    print("=" * 60)
    print("  OCR 模型评估报告")
    print("=" * 60)
    print(f"  总样本数:       {results['total']}")
    print(f"  字符准确率:     {results['char_accuracy']:.2%}")
    print(f"  编辑距离(归一): {results['edit_distance_norm']:.4f}")
    print(f"  低置信度样本:   {len(results['low_confidence'])}")
    print()

    # 目标对比
    targets = {"印刷体": 0.99, "手写体": 0.85, "表格": 0.90, "混合排版": 0.90}
    print("  📊 按文档类型:")
    print(f"  {'类型':<12} {'样本数':>6} {'准确率':>8} {'目标':>8} {'达标':>6}")
    print(f"  {'-'*42}")
    for t in sorted(results["by_type"].keys()):
        info = results["by_type"][t]
        target = targets.get(t, 0.90)
        met = "✅" if info["acc"] >= target else "❌"
        print(f"  {t:<12} {info['count']:>6} {info['acc']:>7.1%} {target:>7.1%} {met:>6}")

    if results["low_confidence"]:
        print(f"\n  ⚠️ 低置信度样本 (前 10):")
        for item in results["low_confidence"][:10]:
            print(f"    {Path(item['image']).name}: {item['confidence']:.2f}")
            print(f"      预测: {item['pred'][:60]}")
            print(f"      真实: {item['gt'][:60]}")


def main():
    parser = argparse.ArgumentParser(description="OCR 评估")
    parser.add_argument("--predictions", "-p", required=True, help="预测结果 JSON")
    parser.add_argument("--ground_truth", "-g", required=True, help="标注真值 JSON (image_path → text)")
    args = parser.parse_args()

    with open(args.predictions, "r", encoding="utf-8") as f:
        preds = json.load(f)
    with open(args.ground_truth, "r", encoding="utf-8") as f:
        gt = json.load(f)

    results = evaluate(preds, gt)
    print_report(results)

    # 保存详细报告
    report_path = Path(args.predictions).with_suffix(".report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n💾 详细报告: {report_path}")


if __name__ == "__main__":
    main()
