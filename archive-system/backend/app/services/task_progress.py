"""任务进度工具 — 处理速率与预计剩余时间的统一计算

ReviewTask（件/分钟）与 OcrTask（页/分钟）共用同一速率公式，
避免在 api/review.py 与 api/ocr.py 各复制一份。
"""

from datetime import datetime as _dt


def calc_rate(started_at, done: int, total: int, status: str) -> dict:
    """计算任务处理速率（单位/分钟）与预计剩余时间（秒）

    Args:
        started_at: 任务开始处理时间（naive datetime 或 None）
        done:       已处理数量（件数或页数）
        total:      总数量
        status:     任务状态（仅 running 时计算）
    Returns:
        {"speed": float, "eta_seconds": int | None}
    """
    if not started_at or status != "running":
        return {"speed": 0, "eta_seconds": None}
    elapsed = (_dt.utcnow() - started_at).total_seconds()
    if elapsed <= 0 or done <= 0:
        return {"speed": 0, "eta_seconds": None}
    speed_per_min = done / (elapsed / 60.0)
    remaining = max(0, (total or 0) - done)
    eta = int(remaining / speed_per_min * 60) if speed_per_min > 0 else None
    return {"speed": round(speed_per_min, 1), "eta_seconds": eta}
