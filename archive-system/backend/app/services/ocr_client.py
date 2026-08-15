"""
OCR 客户端 — mock 模式 / PaddleOCR 真实识别双模式

模式切换:
  OCR_MODE=mock  → 开发环境，返回模拟结果（确定性哈希，同一个输入多次一致）
  OCR_MODE=real  → 调用 PaddleOCR (PP-OCRv5 Server) + PP-StructureV2 版面分析

GPU/CPU 自动检测:
  - GPU 可用时自动使用 CUDA 加速 (paddle.set_device('gpu'))
  - 无 GPU 时自动降级 CPU (paddle.set_device('cpu'))
  - 首次加载自动下载预训练模型权重 (~80MB)

用法:
  from app.services.ocr_client import ocr_client
  result = ocr_client.recognize("/path/to/image.tiff")
  # result: {"text": "...", "confidence": 0.96, "pages": 1, "blocks": [...]}
"""

import hashlib
import io
import logging
import os
import random
import time
from typing import Optional

from app.core.config import settings

logger = logging.getLogger("ocr_client")

# ============================================================
# PaddleOCR 全局单例（惰性初始化）
# ============================================================

_paddle_ocr = None
_paddle_structure = None
_paddle_available = False
_paddle_gpu_available = False


def _init_paddle():
    """惰性初始化 PaddleOCR 实例（首次调用时触发）"""
    global _paddle_ocr, _paddle_structure, _paddle_available, _paddle_gpu_available

    if _paddle_available:
        return

    try:
        import paddle

        # GPU 检测
        _paddle_gpu_available = paddle.is_compiled_with_cuda()
        if _paddle_gpu_available:
            try:
                paddle.set_device("gpu")
                logger.info("PaddlePaddle GPU 模式已启用")
            except Exception:
                _paddle_gpu_available = False
                paddle.set_device("cpu")
                logger.warning("GPU 初始化失败，降级为 CPU")
        else:
            paddle.set_device("cpu")
            logger.info("PaddlePaddle CPU 模式")

        # PP-OCRv5 中文识别（PaddleOCR 3.x API：device 替代 use_gpu，predict 替代 ocr(cls=)）
        from paddleocr import PaddleOCR

        _paddle_ocr = PaddleOCR(
            lang="ch",
            ocr_version="PP-OCRv5",
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            device="gpu" if _paddle_gpu_available else "cpu",
        )
        logger.info("PaddleOCR PP-OCRv5 初始化完成")

        # PP-StructureV3 版面分析（PaddleOCR 3.x）
        try:
            from paddleocr import PPStructureV3

            _paddle_structure = PPStructureV3(
                device="gpu" if _paddle_gpu_available else "cpu",
            )
            logger.info("PP-StructureV3 版面分析初始化完成")
        except ImportError:
            logger.info("PP-StructureV3 不可用（版面分析功能跳过）")
        except Exception as e:
            logger.warning(f"PP-StructureV3 初始化失败: {e}")

        _paddle_available = True

    except ImportError:
        logger.warning("PaddleOCR 未安装 — 使用 mock 模式")
        _paddle_available = False
    except Exception as e:
        logger.error(f"PaddleOCR 初始化失败: {e}")
        _paddle_available = False


def _get_paddle_info() -> dict:
    """获取 PaddleOCR 运行时信息"""
    info = {
        "available": _paddle_available,
        "gpu": _paddle_gpu_available,
        "mode": "real" if _paddle_available else "mock",
    }
    if _paddle_available:
        try:
            import paddle
            info["paddle_version"] = paddle.__version__
            info["cuda_version"] = paddle.version.cuda() if paddle.is_compiled_with_cuda() else None
        except Exception:
            pass
    return info


# ============================================================
# OCR 客户端
# ============================================================

class OCRClient:
    """
    OCR 识别客户端

    - OCR_MODE=mock: 本地开发（默认），返回模拟结果
    - OCR_MODE=real: 调用 PaddleOCR GPU/CPU 真实推理
    """

    def __init__(self):
        self.mode = settings.OCR_MODE
        self._ready = False

    def _ensure_ready(self):
        """确保 PaddleOCR 已初始化（仅在 real 模式下）"""
        if self.mode != "real":
            return
        if not self._ready:
            _init_paddle()
            self._ready = True

    def recognize(self, image_path: str) -> dict:
        """
        单页 OCR 识别

        Args:
            image_path: 图像文件路径

        Returns:
            {
                "text": str,           # 完整识别文本
                "confidence": float,   # 平均置信度 (0-1)
                "pages": int,          # 页数
                "engine": str,         # "paddleocr" / "mock"
                "gpu_used": bool,      # 是否使用 GPU 加速
                "processing_time_ms": int,
                "blocks": [            # 文本块（按阅读顺序）
                    {
                        "text": str,
                        "confidence": float,
                        "bbox": [[x1,y1],[x2,y2],[x3,y3],[x4,y4]],
                    }
                ],
            }
        """
        if self.mode == "mock":
            return self._mock_recognize(image_path)
        return self._real_recognize(image_path)

    def recognize_structure(self, image_path: str) -> dict:
        """
        版面分析 — 检测标题/表格/段落/印章/二维码

        Returns:
            {
                "regions": [
                    {"type": "title"|"table"|"text"|"figure"|"seal", "bbox": [...], "text": "..."},
                ],
                "tables": [
                    {"bbox": [...], "cells": [[...], ...], "html": "<table>..."},
                ],
            }
        """
        if self.mode == "mock":
            return self._mock_structure(image_path)
        self._ensure_ready()
        return self._real_structure(image_path)

    def batch_recognize(self, image_paths: list[str]) -> list[dict]:
        """批量 OCR 识别"""
        return [self.recognize(p) for p in image_paths]

    def get_info(self) -> dict:
        """获取 OCR 引擎信息"""
        info = _get_paddle_info()
        info["mode"] = self.mode
        return info

    # ============================================================
    # Mock 模式
    # ============================================================

    def _mock_recognize(self, image_path: str) -> dict:
        """模拟 OCR 识别 — 确定性哈希确保同一输入结果一致"""
        seed = int(hashlib.md5(image_path.encode()).hexdigest()[:8], 16)
        rng = random.Random(seed)

        confidence = round(rng.uniform(0.72, 0.99), 4)
        return {
            "text": (
                f"[MOCK OCR 结果] 这是来自 {os.path.basename(image_path)} 的模拟识别文本。"
                f"模拟内容包含档案相关信息，置信度: {confidence}。"
            ),
            "confidence": confidence,
            "pages": 1,
            "engine": "mock",
            "gpu_used": False,
            "processing_time_ms": rng.randint(200, 800),
            "blocks": [
                {
                    "text": "模拟文本块1",
                    "confidence": confidence,
                    "bbox": [[10, 10], [200, 10], [200, 40], [10, 40]],
                }
            ],
        }

    def _mock_structure(self, image_path: str) -> dict:
        """模拟版面分析"""
        seed = int(hashlib.md5(image_path.encode()).hexdigest()[:8], 16)
        rng = random.Random(seed)
        return {
            "regions": [
                {"type": "title", "bbox": [[50, 20], [400, 20], [400, 60], [50, 60]], "text": "[MOCK] 文档标题"},
                {"type": "text", "bbox": [[50, 80], [400, 80], [400, 200], [50, 200]], "text": "[MOCK] 正文段落"},
            ],
            "tables": [],
            "engine": "mock",
        }

    # ============================================================
    # 真实 PaddleOCR 识别
    # ============================================================

    def _real_recognize(self, image_path: str) -> dict:
        """真实 OCR 识别 — PaddleOCR GPU/CPU"""
        self._ensure_ready()

        if not _paddle_available or _paddle_ocr is None:
            # 降级到 mock（PaddleOCR 未安装或初始化失败）
            logger.warning(f"PaddleOCR 不可用，降级 mock 识别: {image_path}")
            return self._mock_recognize(image_path)

        if not os.path.isfile(image_path):
            return {
                "text": "",
                "confidence": 0.0,
                "pages": 0,
                "engine": "paddleocr",
                "gpu_used": _paddle_gpu_available,
                "processing_time_ms": 0,
                "blocks": [],
                "error": f"文件不存在: {image_path}",
            }

        t0 = time.time()

        try:
            # PaddleOCR 3.x predict 返回 list[Result]，取第一个图像的结果
            result = _paddle_ocr.predict(image_path)
            elapsed_ms = round((time.time() - t0) * 1000)

            if not result:
                return {
                    "text": "",
                    "confidence": 0.0,
                    "pages": 1,
                    "engine": "paddleocr",
                    "gpu_used": _paddle_gpu_available,
                    "processing_time_ms": elapsed_ms,
                    "blocks": [],
                }

            res = result[0]
            rec_texts = res.get("rec_texts", []) or []
            rec_scores = res.get("rec_scores", []) or []
            rec_polys = res.get("rec_polys", []) or []

            if not rec_texts:
                return {
                    "text": "",
                    "confidence": 0.0,
                    "pages": 1,
                    "engine": "paddleocr",
                    "gpu_used": _paddle_gpu_available,
                    "processing_time_ms": elapsed_ms,
                    "blocks": [],
                }

            full_text = ""
            blocks = []
            confidences = []

            for i, text in enumerate(rec_texts):
                conf = float(rec_scores[i]) if i < len(rec_scores) else 0.0
                poly = rec_polys[i] if i < len(rec_polys) else []

                full_text += text + "\n"
                confidences.append(conf)
                blocks.append({
                    "text": text,
                    "confidence": round(conf, 4),
                    "bbox": [[int(p[0]), int(p[1])] for p in poly] if poly else [],
                })

            avg_conf = round(sum(confidences) / len(confidences), 4) if confidences else 0.0

            logger.info(
                f"OCR 完成: {os.path.basename(image_path)} "
                f"— {len(rec_texts)} 行, 置信度 {avg_conf:.3f}, {elapsed_ms}ms"
            )

            return {
                "text": full_text.strip(),
                "confidence": avg_conf,
                "pages": 1,
                "engine": "paddleocr",
                "gpu_used": _paddle_gpu_available,
                "processing_time_ms": elapsed_ms,
                "blocks": blocks,
            }

        except Exception as e:
            elapsed_ms = round((time.time() - t0) * 1000)
            logger.error(f"OCR 识别失败: {image_path} — {e}")
            return {
                "text": "",
                "confidence": 0.0,
                "pages": 1,
                "engine": "paddleocr",
                "gpu_used": _paddle_gpu_available,
                "processing_time_ms": elapsed_ms,
                "blocks": [],
                "error": str(e)[:200],
            }

    def _real_structure(self, image_path: str) -> dict:
        """真实版面分析 — PP-StructureV3"""
        self._ensure_ready()

        if _paddle_structure is None:
            return {"regions": [], "tables": [], "engine": "paddleocr",
                    "error": "PP-StructureV3 不可用"}

        if not os.path.isfile(image_path):
            return {"regions": [], "tables": [], "engine": "paddleocr",
                    "error": f"文件不存在: {image_path}"}

        try:
            result = _paddle_structure.predict(image_path)

            regions = []
            tables = []

            for item in result:
                item = item if isinstance(item, dict) else {}
                item_type = item.get("type", "unknown")
                bbox = item.get("bbox") or []
                if bbox:
                    bbox = [[int(p[0]), int(p[1])] for p in bbox]

                if item_type == "table":
                    tables.append({
                        "bbox": bbox,
                        "html": item.get("html", ""),
                    })
                else:
                    regions.append({
                        "type": item_type,
                        "bbox": bbox,
                        "text": item.get("text", "") or item.get("res", ""),
                    })

            return {
                "regions": regions,
                "tables": tables,
                "engine": "paddleocr",
            }

        except Exception as e:
            logger.error(f"版面分析失败: {image_path} — {e}")
            return {"regions": [], "tables": [], "engine": "paddleocr",
                    "error": str(e)[:200]}


# ============================================================
# 全局单例
# ============================================================

ocr_client = OCRClient()
