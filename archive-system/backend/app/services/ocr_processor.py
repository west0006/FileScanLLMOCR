"""
OCR 处理管线 — 图像预处理 + 多页 TIFF/PDF 分离 + 结构化输出

用途:
  - OCR 批处理任务的实际执行者
  - 对接 train/ocr/preprocess.py 的图像增强逻辑
  - 多页档案逐页识别、合并结果

用法:
  from app.services.ocr_processor import OcrProcessor
  proc = OcrProcessor()
  result = proc.process_archive(archive_id="1996-XZ-001", image_paths=[...])
"""

import io
import logging
import os
import time
from typing import Optional

from app.core.config import settings
from app.services.ocr_client import ocr_client, _paddle_gpu_available

logger = logging.getLogger("ocr_processor")

# ============================================================
# 图像预处理（增强版）
# ============================================================

_HAS_CV2 = False
try:
    import cv2
    import numpy as np
    _HAS_CV2 = True
except ImportError:
    import numpy as np  # numpy is a base dependency now
    pass


class ImagePreprocessor:
    """档案图像预处理 — 去噪/对比度增强/倾斜校正/自适应二值化"""

    @staticmethod
    def preprocess(
        image_bytes: bytes,
        do_denoise: bool = True,
        do_clahe: bool = True,
        do_deskew: bool = False,  # deskew 可能改变文本位置，默认关闭
        do_binarize: bool = True,
    ) -> bytes:
        """
        预处理图像字节流 → 返回处理后的 bytes (PNG)

        适用于: 泛黄、褪色、带扫描底纹的档案图像
        """
        if not _HAS_CV2:
            return image_bytes  # OpenCV 不可用时原样返回

        try:
            # 从 bytes 解码
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                return image_bytes

            height, width = img.shape[:2]

            # 灰度化
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # 降噪 — 非局部均值降噪（档案扫描底纹）
            if do_denoise:
                # 小图用较小的 h 参数
                h_strength = 6 if min(width, height) < 1000 else 10
                gray = cv2.fastNlMeansDenoising(gray, h=h_strength,
                    templateWindowSize=7, searchWindowSize=21)

            # CLAHE 自适应对比度增强 — 解决泛黄/褪色
            if do_clahe:
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                gray = clahe.apply(gray)

            # 倾斜校正
            if do_deskew:
                gray = _deskew(gray)

            # 自适应二值化
            if do_binarize:
                gray = cv2.adaptiveThreshold(
                    gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                    cv2.THRESH_BINARY, 11, 2,
                )

            # 编码为 PNG bytes
            _, encoded = cv2.imencode(".png", gray)
            return encoded.tobytes()

        except Exception as e:
            logger.warning(f"图像预处理失败: {e}")
            return image_bytes


def _deskew(gray: np.ndarray) -> np.ndarray:
    """基于文本行的倾斜校正"""
    try:
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        coords = np.column_stack(np.where(binary > 0))
        if len(coords) < 100:
            return gray

        rect = cv2.minAreaRect(coords.astype(np.float32))
        angle = rect[-1]

        if angle < -45:
            angle = 90 + angle
        if abs(angle) < 0.3:
            return gray

        h, w = gray.shape
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        return cv2.warpAffine(gray, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
    except Exception:
        return gray


# ============================================================
# 多页分离
# ============================================================

_HAS_PIL = False
try:
    from PIL import Image
    _HAS_PIL = True
except ImportError:
    pass


class PageSplitter:
    """多页文件分离 — TIFF/PDF → 逐页图像"""

    @staticmethod
    def split(file_path: str, output_format: str = "PNG") -> list[bytes]:
        """
        分离多页文件为单页图像 bytes 列表

        支持: TIFF (.tiff/.tif), PDF (.pdf), 普通图像
        """
        if not os.path.isfile(file_path):
            return []  # 文件不存在

        ext = os.path.splitext(file_path)[1].lower()

        if ext in (".tiff", ".tif"):
            return PageSplitter._split_tiff(file_path, output_format)
        elif ext == ".pdf":
            return PageSplitter._split_pdf(file_path, output_format)
        else:
            # 单页图像，直接读取
            with open(file_path, "rb") as f:
                return [f.read()]

    @staticmethod
    def _split_tiff(file_path: str, fmt: str = "PNG") -> list[bytes]:
        """TIFF 多页分离"""
        if not _HAS_PIL:
            with open(file_path, "rb") as f:
                return [f.read()]  # 回退：整个文件

        pages = []
        try:
            img = Image.open(file_path)
            page_idx = 0
            while True:
                buf = io.BytesIO()
                # TIFF 可能包含多帧，先复制再保存
                frame = img.copy() if hasattr(img, "copy") else img
                if frame.mode in ("CMYK", "LA"):
                    frame = frame.convert("RGB")
                elif frame.mode == "P":
                    frame = frame.convert("RGBA")
                elif frame.mode == "1":
                    frame = frame.convert("L")

                frame.save(buf, format="PNG")
                pages.append(buf.getvalue())
                page_idx += 1

                try:
                    img.seek(page_idx)
                except EOFError:
                    break

            logger.info(f"TIFF 分离: {file_path} → {len(pages)} 页")
        except Exception as e:
            logger.error(f"TIFF 分离失败: {file_path} — {e}")
            with open(file_path, "rb") as f:
                return [f.read()]

        return pages

    @staticmethod
    def _split_pdf(file_path: str, fmt: str = "PNG") -> list[bytes]:
        """PDF 转图像 — 尝试 pdf2image，不可用则返回空"""
        try:
            from pdf2image import convert_from_path

            images = convert_from_path(file_path, dpi=300)
            pages = []
            for img in images:
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                pages.append(buf.getvalue())
            logger.info(f"PDF 分离: {file_path} → {len(pages)} 页")
            return pages
        except ImportError:
            logger.warning("pdf2image 未安装 — PDF 预览需: pip install pdf2image")
            return []
        except Exception as e:
            logger.error(f"PDF 分离失败: {file_path} — {e}")
            return []


# ============================================================
# OCR 处理器
# ============================================================

class OcrProcessor:
    """OCR 处理管线 — 串联预处理 → 分页 → 识别 → 结构化输出"""

    def __init__(self, enable_preprocess: bool = True):
        self.enable_preprocess = enable_preprocess

    def process_archive(
        self,
        archive_id: str,
        image_paths: list[str],
        metadata: Optional[dict] = None,
    ) -> dict:
        """
        处理单条档案（可能包含多页）

        Args:
            archive_id: 档案编号
            image_paths: 图像文件路径列表
            metadata: 档案元数据（标题/年度/单位等）

        Returns:
            {
                "archive_id": str,
                "total_pages": int,
                "ocr_text": str,               # 全部文本（页间用 \f 分隔）
                "overall_confidence": float,   # 总体平均置信度
                "pages": [
                    {
                        "page": int,
                        "text": str,
                        "confidence": float,
                        "blocks": [...],
                        "processing_time_ms": int,
                        "preprocessed": bool,
                    }
                ],
                "total_time_ms": int,
                "gpu_used": bool,
                "engine": str,
            }
        """
        t_start = time.time()
        all_pages: list[dict] = []
        all_texts: list[str] = []

        for img_path in image_paths:
            if not os.path.isfile(img_path):
                logger.warning(f"跳过不存在的文件: {img_path}")
                continue

            page_result = self._process_single_page(img_path, len(all_pages) + 1)
            all_pages.append(page_result)
            all_texts.append(page_result["text"])

        total_ms = round((time.time() - t_start) * 1000)

        # 计算总体置信度
        confidences = [p["confidence"] for p in all_pages if p["confidence"] > 0]
        overall_conf = round(sum(confidences) / len(confidences), 4) if confidences else 0.0

        return {
            "archive_id": archive_id,
            "total_pages": len(all_pages),
            "ocr_text": "\n\f\n".join(all_texts),  # \f = 换页符
            "overall_confidence": overall_conf,
            "pages": all_pages,
            "total_time_ms": total_ms,
            "gpu_used": _paddle_gpu_available,
            "engine": "paddleocr" if ocr_client.mode == "real" else "mock",
        }

    def _process_single_page(self, image_path: str, page_num: int) -> dict:
        """处理单页"""
        t0 = time.time()
        preprocessed = False

        # 1. 读取原始文件
        with open(image_path, "rb") as f:
            raw_bytes = f.read()

        # 2. 预处理（去噪/增强）
        if self.enable_preprocess and _HAS_CV2:
            processed_bytes = ImagePreprocessor.preprocess(raw_bytes)
            preprocessed = (processed_bytes != raw_bytes)
        else:
            processed_bytes = raw_bytes

        # 3. 写入临时文件给 PaddleOCR（它需要文件路径）
        import tempfile
        tmp_suffix = os.path.splitext(image_path)[1] or ".png"
        if preprocessed:
            tmp_suffix = ".png"

        tmp_fd, tmp_path = tempfile.mkstemp(suffix=tmp_suffix)
        try:
            with os.fdopen(tmp_fd, "wb") as tmpf:
                tmpf.write(processed_bytes)

            # 4. OCR 识别
            result = ocr_client.recognize(tmp_path)
        finally:
            # 清理临时文件
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

        elapsed = round((time.time() - t0) * 1000)

        return {
            "page": page_num,
            "text": result.get("text", ""),
            "confidence": result.get("confidence", 0.0),
            "blocks": result.get("blocks", []),
            "processing_time_ms": elapsed,
            "preprocessed": preprocessed,
            "error": result.get("error"),
        }

    def process_batch(self, archive_map: dict[str, list[str]]) -> list[dict]:
        """
        批量处理档案

        Args:
            archive_map: {archive_id: [image_path, ...]}

        Returns:
            [{archive_id, total_pages, ocr_text, ...}, ...]
        """
        results = []
        for archive_id, paths in archive_map.items():
            results.append(self.process_archive(archive_id, paths))
        return results


# 全局单例
ocr_processor = OcrProcessor()
