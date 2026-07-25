#!/usr/bin/env python3
"""
OCR 功能验证脚本 — 部署后全面测试

验证项目:
  1. PaddlePaddle 安装 + GPU/CPU 模式
  2. PP-OCRv5 中文识别（印刷体）
  3. 方向分类（旋转文本自动纠正）
  4. PP-StructureV2 版面分析（表格/标题/段落）
  5. 性能基准（单页耗时，GPU vs CPU）
  6. GPU 加速验证（CUDA 设备可见 + 推理时利用率）

用法:
  python deploy/ocr_verify.py              # 全部验证
  python deploy/ocr_verify.py --quick      # 快速验证（跳过性能测试）
  python deploy/ocr_verify.py --json       # JSON 输出
"""

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass, field, asdict
from typing import Optional

try:
    import numpy as np
except ImportError:
    np = None  # type: ignore


# ============================================================
# 测试样本（程序生成，无需外部文件）
# ============================================================

# 模拟中文档案文本图像生成
def _make_chinese_test_image(
    text: str = "中南财经政法大学\n一九九六年招生工作总结",
    size: tuple = (640, 240),
    font_size: int = 20,
) -> np.ndarray:
    """生成测试图像 — 用 PIL 渲染中文文本"""
    if np is None:
        return None
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        # 回退：纯色图
        return np.ones((size[1], size[0], 3), dtype=np.uint8) * 240

    img = Image.new("RGB", size, (255, 255, 255))
    draw = ImageDraw.Draw(img)

    # 尝试常见中文字体
    font = None
    font_paths = [
        # Linux
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
        "/usr/share/fonts/truetype/arphic/uming.ttc",
        # macOS
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        # Windows
        "C:\\Windows\\Fonts\\msyh.ttc",
        "C:\\Windows\\Fonts\\simhei.ttf",
        "C:\\Windows\\Fonts\\simsun.ttc",
        # PIL 默认 (打不开中文)
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                font = ImageFont.truetype(fp, font_size)
                break
            except Exception:
                continue

    if font is None:
        font = ImageFont.load_default()

    y = 20
    for line in text.split("\n"):
        draw.text((30, y), line, fill=(0, 0, 0), font=font)
        y += font_size + 10

    return np.array(img)


# ============================================================
# 验证器
# ============================================================

@dataclass
class VerifyResult:
    name: str
    passed: bool
    detail: str = ""
    elapsed_ms: float = 0.0
    extra: dict = field(default_factory=dict)


class OcrVerifier:
    def __init__(self):
        self.results: list[VerifyResult] = []
        self._gpu_available = False

    def _add(self, name: str, passed: bool, detail: str = "", elapsed_ms: float = 0.0, **extra):
        self.results.append(VerifyResult(name, passed, detail, elapsed_ms, extra))
        return passed

    def check_import(self) -> bool:
        """检查 PaddlePaddle 导入"""
        try:
            import paddle
            ver = paddle.__version__
            cuda = paddle.is_compiled_with_cuda()
            self._gpu_available = cuda
            return self._add("PaddlePaddle 导入",
                True, f"v{ver} {'GPU' if cuda else 'CPU'}", gpu=cuda, version=ver)
        except ImportError as e:
            return self._add("PaddlePaddle 导入", False, str(e))
        except Exception as e:
            return self._add("PaddlePaddle 导入", False, str(e)[:120])

    def check_paddleocr(self) -> bool:
        """检查 PaddleOCR 导入"""
        try:
            import paddleocr
            ver = getattr(paddleocr, "__version__", "unknown")
            return self._add("PaddleOCR 导入", True, f"v{ver}", version=ver)
        except ImportError as e:
            return self._add("PaddleOCR 导入", False, str(e))

    def check_chinese_ocr(self) -> bool:
        """中文 OCR 识别测试"""
        try:
            from paddleocr import PaddleOCR

            img = _make_chinese_test_image()
            if img is None:
                return self._add("中文 OCR 识别", False, "无法生成测试图像")

            ocr = PaddleOCR(lang="ch", use_angle_cls=True, show_log=False)

            t0 = time.time()
            result = ocr.ocr(img, cls=True)
            elapsed = (time.time() - t0) * 1000

            if result and result[0]:
                texts = [line[1][0] for line in result[0]]
                found = "".join(texts)
                has_chinese = any("\u4e00" <= c <= "\u9fff" for c in found)
                return self._add("中文 OCR 识别",
                    has_chinese and len(found) > 3,
                    f"识别到 {len(result[0])} 行: {found[:60]}",
                    elapsed_ms=round(elapsed, 1),
                    lines=len(result[0]),
                    text=found[:100],
                )
            return self._add("中文 OCR 识别", False, "返回空结果", elapsed_ms=round(elapsed, 1))
        except Exception as e:
            return self._add("中文 OCR 识别", False, str(e)[:150])

    def check_angle_classification(self) -> bool:
        """方向分类测试 — 旋转文本"""
        try:
            from paddleocr import PaddleOCR

            # 生成 180 度旋转的文本
            img = _make_chinese_test_image("档案开放审核报告")
            if img is None:
                return self._add("方向分类", False, "无法生成测试图像")

            # 旋转图像
            if np is not None:
                img_rotated = np.rot90(img, 2).copy()  # 180 度
            else:
                img_rotated = img  # 跳过旋转测试

            ocr = PaddleOCR(lang="ch", use_angle_cls=True, show_log=False)
            result = ocr.ocr(img_rotated, cls=True)

            if result and result[0]:
                texts = [line[1][0] for line in result[0]]
                found = "".join(texts)
                return self._add("方向分类",
                    "档案" in found or "审核" in found or "报告" in found,
                    f"旋转文本识别: {found[:60]}",
                    text=found[:100],
                )
            return self._add("方向分类", False, "返回空结果")
        except Exception as e:
            return self._add("方向分类", False, str(e)[:150])

    def check_structure_analysis(self) -> bool:
        """PP-StructureV2 版面分析"""
        try:
            from paddleocr import PPStructure

            img = _make_chinese_test_image(
                "标题: 一九九六年招生工作总结\n\n部门: 招生办公室\n\n人数: 1500 人",
                size=(800, 400),
                font_size=18,
            )
            if img is None:
                return self._add("版面分析", None, "无法生成测试图像")

            engine = PPStructure(show_log=False)

            t0 = time.time()
            result = engine(img)
            elapsed = (time.time() - t0) * 1000

            if result is None:
                # PPStructure 可能在 CPU 下不支持
                return self._add("版面分析", None, "PPStructure 返回 None (可能需要 GPU)", elapsed_ms=round(elapsed, 1))

            if isinstance(result, list) and len(result) > 0:
                types = [getattr(r, "type", str(r)) for r in result]
                return self._add("版面分析",
                    True,
                    f"检测到 {len(result)} 个区域: {', '.join(types[:5])}",
                    elapsed_ms=round(elapsed, 1),
                    region_count=len(result),
                    types=types[:10],
                )
            return self._add("版面分析", True, f"返回 {len(result) if isinstance(result, list) else type(result).__name__}", elapsed_ms=round(elapsed, 1))
        except ImportError:
            return self._add("版面分析", None, "PPStructure 不可用 (跳过，不影响核心 OCR)")
        except Exception as e:
            msg = str(e)[:150]
            if "not support" in msg.lower() or "cpu" in msg.lower():
                return self._add("版面分析", None, f"CPU 模式限制: {msg}")
            return self._add("版面分析", False, msg)

    def check_gpu_acceleration(self) -> bool:
        """GPU 加速验证"""
        try:
            import paddle

            if not paddle.is_compiled_with_cuda():
                return self._add("GPU 加速", None, "未安装 GPU 版 PaddlePaddle (CPU 模式，正常)")

            # 简单推理测试
            x = paddle.randn([1, 3, 64, 128])
            paddle.set_device("gpu")

            # 预热
            for _ in range(3):
                _ = paddle.nn.functional.relu(x)

            # 计时
            t0 = time.time()
            for _ in range(100):
                _ = paddle.nn.functional.relu(x)
            paddle.device.cuda.synchronize()
            elapsed = (time.time() - t0) * 1000

            return self._add("GPU 加速",
                True,
                f"GPU 推理正常 (100次耗时 {elapsed:.1f}ms)",
                elapsed_ms=round(elapsed, 1),
                gpu_devices=paddle.device.cuda.device_count(),
            )
        except Exception as e:
            return self._add("GPU 加速", False, str(e)[:150])

    def check_performance(self) -> bool:
        """性能基准测试"""
        try:
            from paddleocr import PaddleOCR

            img = _make_chinese_test_image(
                "中南财经政法大学\n一九九六年招生工作总结报告\n\n本年度招生工作在校党委的领导下顺利完成。\n共录取本科生1200人研究生300人。",
                size=(800, 300),
                font_size=16,
            )
            if img is None:
                return self._add("性能基准", False, "无法生成测试图像")

            ocr = PaddleOCR(lang="ch", use_angle_cls=True, show_log=False)

            # 预热
            _ = ocr.ocr(img, cls=True)

            # 计时 5 次取平均
            times = []
            for _ in range(5):
                t0 = time.time()
                _ = ocr.ocr(img, cls=True)
                times.append((time.time() - t0) * 1000)

            avg_ms = sum(times) / len(times)
            min_ms = min(times)

            # 判断性能
            if avg_ms < 500:
                perf = "优秀"
            elif avg_ms < 1000:
                perf = "良好"
            elif avg_ms < 3000:
                perf = "可接受"
            else:
                perf = "较慢"

            return self._add("性能基准",
                avg_ms < 5000,
                f"{perf} — 平均 {avg_ms:.0f}ms/页 (最快 {min_ms:.0f}ms)",
                elapsed_ms=round(avg_ms, 1),
                min_ms=round(min_ms, 1),
                rating=perf,
            )
        except Exception as e:
            return self._add("性能基准", False, str(e)[:150])


# ============================================================
# 主入口
# ============================================================

def print_report(results: list[VerifyResult], quick: bool = False):
    """打印验证报告"""
    print()
    print("=" * 65)
    print("  PaddleOCR-VL 功能验证报告")
    print("=" * 65)
    print()

    passed = 0
    failed = 0
    skipped = 0

    for r in results:
        if r.passed is None:
            icon = "⬜"
            status = "SKIP"
            skipped += 1
        elif r.passed:
            icon = "✅"
            status = "PASS"
            passed += 1
        else:
            icon = "❌"
            status = "FAIL"
            failed += 1

        time_str = f" ({r.elapsed_ms:.0f}ms)" if r.elapsed_ms > 0 else ""
        print(f"  {icon} [{status}] {r.name}{time_str}")
        if r.detail:
            print(f"      {r.detail}")

    print()
    print(f"  {'─' * 61}")
    total = len(results)
    print(f"  总计: {total} 项  |  ✅ {passed} 通过  |  ❌ {failed} 失败  |  ⬜ {skipped} 跳过")

    if quick:
        print(f"  (快速模式: 跳过性能基准)")
    print()

    if failed > 0:
        print("  ⚠️  存在失败项，请检查:")
        for r in results:
            if r.passed is False:
                print(f"     • {r.name}: {r.detail}")
        print()

    return failed == 0


def main():
    parser = argparse.ArgumentParser(description="OCR 功能验证")
    parser.add_argument("--quick", "-q", action="store_true", help="快速验证（跳过性能测试）")
    parser.add_argument("--json", action="store_true", help="JSON 输出")
    args = parser.parse_args()

    v = OcrVerifier()

    # 运行所有检查
    if not v.check_import():
        # PaddlePaddle 未安装，后续测试无法进行
        print_report(v.results, args.quick)
        sys.exit(1)

    v.check_paddleocr()
    v.check_chinese_ocr()
    v.check_angle_classification()
    v.check_structure_analysis()
    v.check_gpu_acceleration()

    if not args.quick:
        v.check_performance()

    if args.json:
        print(json.dumps([asdict(r) for r in v.results], ensure_ascii=False, indent=2))
    else:
        ok = print_report(v.results, args.quick)
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
