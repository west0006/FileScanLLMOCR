"""数据库模型定义"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, JSON, ForeignKey
from sqlalchemy.orm import relationship  # 保留：ForeignKey 关联需要

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    department = Column(String(200))
    contact = Column(String(100))
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="reviewer")  # system_admin / archive_admin / reviewer
    is_active = Column(Boolean, default=True)
    login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    password_updated_at = Column(DateTime, default=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)
    tree_auth = Column(JSON, default=list)  # ["行政档案", "教学档案", ...] 授权的目录节点
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(String(200))
    permissions = Column(JSON, default=dict)  # {"search": true, "ocr": true, "review": false, ...}
    data_scope = Column(JSON, default=dict)   # {"categories": [], "years": [], "departments": []}
    created_at = Column(DateTime, default=datetime.utcnow)


class Archive(Base):
    """档案元数据"""
    __tablename__ = "archives"

    id = Column(Integer, primary_key=True, autoincrement=True)
    archive_id = Column(String(100), unique=True, nullable=False, index=True)  # 档案编号
    title = Column(String(500), nullable=False)         # 题名
    author = Column(String(200))                        # 责任者
    file_code = Column(String(100))                     # 文件编号
    subject = Column(String(300))                       # 主题词
    year = Column(Integer, index=True)
    category = Column(String(100), index=True)          # 门类
    department = Column(String(200), index=True)        # 归口单位
    fonds_id = Column(String(50), index=True)            # 全宗号
    retention_period = Column(String(50))               # 保管期限
    security_level = Column(String(50))                 # 密级
    level = Column(String(20), default="file")           # 层级: project/box/file
    open_status = Column(String(20), default="未审核")   # 开放状态
    file_count = Column(Integer, default=0)             # 卷内文件数
    ocr_text = Column(Text)                             # OCR 全文
    ocr_status = Column(String(20), default="pending")  # pending/processing/done/failed
    ocr_confidence = Column(Float)
    ocr_engine = Column(String(50))       # paddleocr / mock
    ocr_model_version = Column(String(50)) # PP-OCRv5 / mock-v1
    ocr_duration_ms = Column(Integer)      # 总识别耗时(ms)
    entities = Column(JSON, default=list)   # NLP 抽取的实体列表
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ReviewTask(Base):
    """预审任务"""
    __tablename__ = "review_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_name = Column(String(200), nullable=False)
    batch_name = Column(String(100))
    total_count = Column(Integer, default=0)
    completed_count = Column(Integer, default=0)
    status = Column(String(20), default="pending")  # pending/running/paused/completed/cancelled
    filter_criteria = Column(JSON)                   # 筛选条件
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime)


class ReviewRecord(Base):
    """预审记录"""
    __tablename__ = "review_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("review_tasks.id"), index=True)
    archive_id = Column(String(100), index=True)
    risk_score = Column(Float)
    risk_level = Column(String(10))    # 低/中/高
    sensitive_items = Column(JSON)     # [{type, content, position}]
    suggestion = Column(String(50))    # 建议开放/建议部分开放(脱敏后)/建议延期开放/建议不开放
    reason = Column(Text)
    confidence = Column(Float)
    model_name = Column(String(100))
    processing_time_ms = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)


class OcrTask(Base):
    """OCR 任务"""
    __tablename__ = "ocr_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_name = Column(String(200), nullable=False)
    total_pages = Column(Integer, default=0)
    processed_pages = Column(Integer, default=0)
    failed_pages = Column(Integer, default=0)
    status = Column(String(20), default="pending")
    priority = Column(Integer, default=0)  # 0=普通, 1=高, 2=紧急
    filter_criteria = Column(JSON)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime)


class OperationLog(Base):
    """操作日志"""
    __tablename__ = "operation_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, index=True)
    username = Column(String(50))
    operation_type = Column(String(50), index=True)  # login/logout/search/view/download/export/admin
    module = Column(String(50))
    description = Column(Text)
    target_id = Column(String(200))
    ip_address = Column(String(50))
    user_agent = Column(String(300))
    session_id = Column(String(64), nullable=True)  # 会话标识（token 哈希前 16 位）
    chain_hash = Column(String(64))  # 哈希链校验：SHA256(prev_hash + content)
    result = Column(String(20))  # success/failure
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class SyncLog(Base):
    """数据同步日志"""
    __tablename__ = "sync_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sync_type = Column(String(20))  # file/database
    sync_mode = Column(String(20))  # full/incremental
    new_files = Column(Integer, default=0)
    updated_files = Column(Integer, default=0)
    new_records = Column(Integer, default=0)
    updated_records = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    status = Column(String(20))     # running/completed/failed
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime)
    log_detail = Column(Text)
