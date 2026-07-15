"""Celery 应用配置"""

from celery import Celery
from app.core.config import settings

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
    task_time_limit=60 * 60,  # 1 小时超时
    task_soft_time_limit=50 * 60,  # 50 分钟软超时
)
