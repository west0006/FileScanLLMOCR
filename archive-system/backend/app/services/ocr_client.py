"""OCR Mock 客户端 — 开发环境返回模拟识别结果"""

import os
import random
import hashlib
from typing import Optional

from app.core.config import settings


class OCRClient:
    """OCR 识别客户端 — mock 模式用于开发，real 模式调用 PaddleOCR"""

    def __init__(self):
        self.mode = settings.OCR_MODE

    def recognize(self, image_path: str) -> dict:
        if self.mode == "mock":
            return self._mock_recognize(image_path)
        else:
            return self._real_recognize(image_path)

    def _mock_recognize(self, image_path: str) -> dict:
        """模拟 OCR 识别"""
        seed = int(hashlib.md5(image_path.encode()).hexdigest()[:8], 16)
        rng = random.Random(seed)

        confidence = round(rng.uniform(0.72, 0.99), 4)
        return {
            "text": f"[MOCK OCR 结果] 这是来自 {os.path.basename(image_path)} 的模拟识别文本。"
                    f"模拟内容包含档案相关信息，置信度: {confidence}。",
            "confidence": confidence,
            "pages": 1,
            "engine": "mock",
            "processing_time_ms": rng.randint(200, 800),
            "blocks": [
                {
                    "text": "模拟文本块1",
                    "confidence": confidence,
                    "bbox": [[10, 10], [200, 10], [200, 40], [10, 40]],
                }
            ],
        }

    def _real_recognize(self, image_path: str) -> dict:
        """真实 OCR 识别 — 调用 PaddleOCR"""
        raise NotImplementedError("真实 OCR 识别待 L3 环境配置后实现")

    def batch_recognize(self, image_paths: list[str]) -> list[dict]:
        return [self.recognize(p) for p in image_paths]


# 全局单例
ocr_client = OCRClient()
