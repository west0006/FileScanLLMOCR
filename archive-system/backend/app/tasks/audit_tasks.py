"""审计定时任务 — 月度报告生成 + 过期账户清理"""

import logging
from datetime import datetime, timedelta

from celery.utils.log import get_task_logger

from app.tasks.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.models import OperationLog, User
from app.core.log_chain import append_chain_log, build_log_content, compute_chain_hash

logger = get_task_logger(__name__)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=300)
def generate_monthly_audit_report(self):
    """
    每月自动生成审计报告 — 统计当月操作概况并写入操作日志。

    由 Celery Beat 每月 1 号凌晨 2:00 触发。
    """
    from sqlalchemy import func

    db = SessionLocal()
    try:
        now = datetime.utcnow()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # 本月统计
        month_total = db.query(func.count()).filter(
            OperationLog.created_at >= month_start,
        ).scalar() or 0

        month_failed = db.query(func.count()).filter(
            OperationLog.created_at >= month_start,
            OperationLog.result == "failure",
        ).scalar() or 0

        month_by_type = (
            db.query(OperationLog.operation_type, func.count())
            .filter(OperationLog.created_at >= month_start)
            .group_by(OperationLog.operation_type)
            .all()
        )
        type_summary = ", ".join(f"{r[0]}:{r[1]}" for r in month_by_type[:5])

        # 异常检测：暴力破解
        one_hour_ago = now - timedelta(hours=1)
        brute_force = (
            db.query(OperationLog.username, func.count().label("cnt"))
            .filter(
                OperationLog.operation_type == "login",
                OperationLog.result == "failure",
                OperationLog.created_at >= one_hour_ago,
            )
            .group_by(OperationLog.username)
            .having(func.count() >= 5)
            .count()
        )

        # 审计链校验
        logs = db.query(OperationLog).order_by(OperationLog.id.asc()).all()
        prev_hash = "0" * 64
        tampered_count = 0
        for log in logs:
            content = build_log_content(log.username, log.operation_type, log.module, log.description, log.target_id, log.result)
            expected = compute_chain_hash(prev_hash, content)
            if expected != (log.chain_hash or ""):
                tampered_count += 1
            prev_hash = log.chain_hash or expected

        # 写入操作日志
        desc = (
            f"[月度审计报告] {month_start.strftime('%Y年%m月')} "
            f"总操作{month_total}次, 失败{month_failed}次, "
            f"类型分布[{type_summary}], "
            f"暴力破解风险{brute_force}个, "
            f"链校验异常{tampered_count}条"
        )
        append_chain_log(
            db,
            user_id=0, username="系统", operation_type="audit", module="audit",
            description=desc, result="success",
        )

        logger.info(f"月度审计报告已生成: {month_start.strftime('%Y-%m')} "
                     f"total={month_total} failed={month_failed} tampered={tampered_count}")
        return {
            "period": month_start.strftime("%Y-%m"),
            "total": month_total,
            "failed": month_failed,
            "brute_force_risks": brute_force,
            "tampered": tampered_count,
            "status": "generated",
        }

    except Exception as exc:
        logger.error(f"月度审计报告生成失败: {exc}")
        raise self.retry(exc=exc)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=1)
def deactivate_idle_users(self):
    """
    停用超过 90 天未登录的用户（系统管理员除外）。

    由 Celery Beat 每天凌晨 3:00 触发。
    """
    db = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(days=90)
        idle_users = (
            db.query(User)
            .filter(
                User.role != "system_admin",
                User.is_active == True,
                (User.last_login_at == None) | (User.last_login_at < cutoff),
            )
            .all()
        )

        deactivated = 0
        for u in idle_users:
            u.is_active = False
            deactivated += 1

        if deactivated > 0:
            db.commit()
            # 写入操作日志
            desc = f"[自动停用] {deactivated} 个用户超过 90 天未登录，已自动停用"
            append_chain_log(
                db,
                user_id=0, username="系统", operation_type="admin", module="user",
                description=desc, result="success",
            )

        logger.info(f"闲置用户清理: 停用 {deactivated} 个用户")
        return {"deactivated": deactivated}
    except Exception as exc:
        logger.error(f"闲置用户清理失败: {exc}")
        raise self.retry(exc=exc)
    finally:
        db.close()
