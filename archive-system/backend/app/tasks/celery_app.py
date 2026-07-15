"""Celery 应用配置 — 延迟连接，Redis 不可用时跳过"""

from celery import Celery
from app.core.config import settings
import redis

# 检测 Redis 是否可用，不可用则跳过 Celery 初始化
_celery_available = False
try:
    r = redis.Redis.from_url(settings.CELERY_BROKER_URL or settings.REDIS_URL, socket_connect_timeout=2)
    r.ping()
    _celery_available = True
    r.close()
except Exception:
    pass

if _celery_available:
    celery_app = Celery(
        "archive_tasks",
        broker=settings.CELERY_BROKER_URL or settings.REDIS_URL,
        backend=settings.CELERY_RESULT_BACKEND or settings.REDIS_URL,
        include=[
            "app.tasks.ocr_tasks",
            "app.tasks.review_tasks",
            "app.tasks.sync_tasks",
        ],
    )
    celery_app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="Asia/Shanghai",
        enable_utc=True,
        task_track_started=True,
        task_time_limit=60 * 60,
        task_soft_time_limit=50 * 60,
        broker_connection_retry_on_startup=True,
    )
else:
    # Redis 不可用 — 创建占位 Celery 实例（不会连接 broker）
    celery_app = Celery("archive_tasks", broker="memory://")
    celery_app.conf.task_always_eager = True  # 同步执行模式（开发环境）
