"""
文档摄取服务 — PDF/Word 文本提取入 ES 全文索引

支持格式: .pdf (PyPDF2/pdfplumber), .docx (python-docx), .txt
用途: 异质检索 — 用户上传非档案图像文件后，提取全文入 ES 索引

用法:
  from app.services.ingest_service import ingest_file
  result = ingest_file("/path/to/document.pdf")
"""

import hashlib
import logging
import os
from typing import Optional

from app.core.config import settings
from app.core.database import get_es, SessionLocal

logger = logging.getLogger("ingest")


def ingest_file(file_path: str, archive_id: Optional[str] = None, metadata: Optional[dict] = None) -> dict:
    """
    摄取一个文档文件 → 提取全文 → 写入 ES 索引

    Returns:
        {"status": "ok", "text_length": int, "file_type": str, "archive_id": str}
    """
    if not os.path.isfile(file_path):
        return {"status": "error", "reason": "file_not_found"}

    ext = os.path.splitext(file_path)[1].lower()
    text = ""

    try:
        if ext == ".pdf":
            text = _extract_pdf(file_path)
        elif ext in (".docx", ".doc"):
            text = _extract_docx(file_path)
        elif ext == ".txt":
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
        else:
            return {"status": "skipped", "reason": f"不支持的文件格式: {ext}"}

        if not text.strip():
            return {"status": "empty", "reason": "文档内容为空"}

        # 生成 archive_id
        if not archive_id:
            name_hash = hashlib.md5(text[:200].encode()).hexdigest()[:8]
            archive_id = f"INGEST-{name_hash}"

        # 写入 ES
        es = get_es()
        if es:
            doc = {
                "archive_id": archive_id,
                "title": metadata.get("title", os.path.basename(file_path)) if metadata else os.path.basename(file_path),
                "author": metadata.get("author", "") if metadata else "",
                "full_text": text[:50000],  # ES 限制 10 万字符
                "year": metadata.get("year") if metadata else None,
                "category": metadata.get("category", "上传文档") if metadata else "上传文档",
                "department": metadata.get("department", "") if metadata else "",
                "fonds_id": "INGEST",
                "level": "file",
                "open_status": "未审核",
                "ocr_confidence": 1.0,
                "ocr_text_quality": "ingested",
                "file_count": 1,
            }
            index = f"{settings.ES_INDEX_PREFIX}_fulltext"
            es.index(index=index, id=archive_id, body=doc, refresh="wait_for")

        logger.info(f"文档摄取成功: {file_path} → {len(text)} 字符")
        return {"status": "ok", "text_length": len(text), "file_type": ext, "archive_id": archive_id}

    except Exception as e:
        logger.error(f"文档摄取失败: {file_path} — {e}")
        return {"status": "error", "reason": str(e)[:200]}


def _extract_pdf(file_path: str) -> str:
    """PDF 文本提取 — 优先 pdfplumber，回退 PyPDF2"""
    text = ""
    # 方案 A: pdfplumber（质量更好）
    try:
        import pdfplumber
        with pdfplumber.open(file_path) as pdf:
            pages = [p.extract_text() or "" for p in pdf.pages]
            text = "\n\f\n".join(pages)
        if text.strip():
            return text
    except ImportError:
        pass
    except Exception:
        pass

    # 方案 B: PyPDF2
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(file_path)
        pages = [p.extract_text() or "" for p in reader.pages]
        text = "\n\f\n".join(pages)
    except ImportError:
        pass
    except Exception:
        pass

    return text


def _extract_docx(file_path: str) -> str:
    """Word 文本提取"""
    try:
        from docx import Document
        doc = Document(file_path)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n".join(paragraphs)
    except ImportError:
        pass
    except Exception:
        pass
    return ""


def batch_ingest(file_paths: list[str]) -> list[dict]:
    """批量摄取"""
    return [ingest_file(p) for p in file_paths]
