"""Celery 应用配置 — 延迟连接，Redis 不可用时跳过"""

from celery import Celery
from app.core.config import settings
import redis
import logging

_log = logging.getLogger("celery_app")

# 检测 Redis 是否可用，不可用则跳过 Celery 初始化
_celery_available = False
try:
    r = redis.Redis.from_url(settings.CELERY_BROKER_URL or settings.REDIS_URL, socket_connect_timeout=2)
    r.ping()
    _celery_available = True
    r.close()
except Exception:
    _log.info("Redis 不可用 — Celery 降级为 memory:// 同步执行模式")

if _celery_available:
    celery_app = Celery(
        "archive_tasks",
        broker=settings.CELERY_BROKER_URL or settings.REDIS_URL,
        backend=settings.CELERY_RESULT_BACKEND or settings.REDIS_URL,
        include=[
            "app.tasks.ocr_tasks",
            "app.tasks.review_tasks",
            "app.tasks.sync_tasks",
            "app.tasks.audit_tasks",
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
        beat_schedule={
            # 每月 1 号凌晨 2 点自动生成审计报告
            "monthly-audit-report": {
                "task": "app.tasks.audit_tasks.generate_monthly_audit_report",
                "schedule": 30 * 24 * 3600.0,  # 30 天
                "options": {"expires": 3600},
            },
            # 每天凌晨 3:00 清理超过 90 天未登录的用户
            "deactivate-idle-users": {
                "task": "app.tasks.audit_tasks.deactivate_idle_users",
                "schedule": 24 * 3600.0,  # 每天
                "options": {"expires": 1800},
            },
        },
    )
else:
    # Redis 不可用 — 创建占位 Celery 实例（不会连接 broker）
    celery_app = Celery("archive_tasks", broker="memory://")
    celery_app.conf.task_always_eager = True  # 同步执行模式（开发环境）
