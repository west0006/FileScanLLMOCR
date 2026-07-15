"""数据同步异步任务"""

from app.tasks.celery_app import celery_app


@celery_app.task(bind=True, max_retries=3)
def sync_files_task(self, mode: str = "incremental"):
    """文件同步任务"""
    return {"mode": mode, "status": "completed", "synced": 0, "failed": 0}


@celery_app.task(bind=True, max_retries=3)
def sync_database_task(self, mode: str = "incremental"):
    """数据库同步任务"""
    return {"mode": mode, "status": "completed", "synced": 0, "failed": 0}
