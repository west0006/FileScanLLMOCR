"""异质文档摄取 — PDF/Word/TXT 文本提取（SE-008 异质信息统一检索）

本地无 ES 时提取文本写入 Archive.ocr_text，随检索走 SQLite 全文降级路径；
ES 可用时由 OCR/摄取任务增量索引。依赖：pypdf（PDF）、python-docx（Word），
未安装时降级为纯文本直读（仅 TXT 有效）。
"""

import os
import logging

logger = logging.getLogger("ingest_service")


def extract_text(file_path: str) -> str:
    """根据扩展名提取文档全文，返回文本（提取失败返回空串）"""
    if not os.path.isfile(file_path):
        return ""
    ext = os.path.splitext(file_path)[1].lower()
    try:
        if ext == ".txt":
            return _extract_txt(file_path)
        if ext == ".pdf":
            return _extract_pdf(file_path)
        if ext in (".doc", ".docx"):
            return _extract_docx(file_path)
    except Exception as e:
        logger.warning(f"文档摄取失败: {file_path} — {e}")
    return ""


def _extract_txt(file_path: str) -> str:
    for enc in ("utf-8", "gbk", "utf-16"):
        try:
            with open(file_path, "r", encoding=enc, errors="replace") as f:
                return f.read()
        except Exception:
            continue
    return ""


def _extract_pdf(file_path: str) -> str:
    PdfReader = None
    try:
        from pypdf import PdfReader
    except ImportError:
        try:
            from PyPDF2 import PdfReader
        except ImportError:
            return ""
    reader = PdfReader(file_path)
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def _extract_docx(file_path: str) -> str:
    try:
        import docx
    except ImportError:
        return ""
    d = docx.Document(file_path)
    return "\n".join(p.text for p in d.paragraphs)
