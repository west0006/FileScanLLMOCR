"""应用配置 — 从环境变量读取，支持 .env 文件"""

import os
from pydantic_settings import BaseSettings
from typing import Optional

# 项目根目录 (archive-system/backend/)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# archive-system/ 目录（.env 所在）
APP_ROOT = os.path.dirname(PROJECT_ROOT)


class Settings(BaseSettings):
    # 应用
    APP_ENV: str = "development"
    APP_NAME: str = "档案智能查询与开放审核系统"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # 数据库.md — DB_MODE=sqlite 用于无 Docker 的本地开发
    DB_MODE: str = "sqlite"  # mysql | sqlite
    DB_HOST: str = "mysql"
    DB_PORT: int = 3306
    DB_USER: str = "archive"
    DB_PASSWORD: str = "archive123"
    DB_NAME: str = "archive_db"
    SQLITE_PATH: str = ""

    @property
    def DATABASE_URL(self) -> str:
        if self.DB_MODE == "sqlite":
            db_path = self.SQLITE_PATH or os.path.join(PROJECT_ROOT, "archive_dev.db")
            return f"sqlite:///{db_path}"
        # 用户名/密码 URL 编码，避免含 @ : / # 等特殊字符时连接串被截断
        from urllib.parse import quote_plus
        user = quote_plus(self.DB_USER)
        pwd = quote_plus(self.DB_PASSWORD)
        return f"mysql+pymysql://{user}:{pwd}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"

    # Elasticsearch
    ES_HOST: str = "elasticsearch"
    ES_PORT: int = 9200
    ES_INDEX_PREFIX: str = "archive"

    # Redis
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    @property
    def REDIS_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # Celery
    CELERY_BROKER_URL: Optional[str] = None
    CELERY_RESULT_BACKEND: Optional[str] = None

    # JWT
    JWT_SECRET: str = "dev-secret-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 120
    SESSION_IDLE_TIMEOUT: int = 30  # 闲置超时（分钟）

    # 安全
    LOGIN_MAX_ATTEMPTS: int = 5
    LOGIN_LOCK_MINUTES: int = 15
    PASSWORD_MIN_LENGTH: int = 12
    PASSWORD_EXPIRE_DAYS: int = 30
    # 开发模式是否放行权限（默认 False=强制权限；开发联调需要时设为 true）
    DEV_PERMISSIVE: bool = False

    # AI 模式
    LLM_MODE: str = "mock"  # mock | ollama | real
    OLLAMA_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:3b"
    OCR_MODE: str = "mock"  # mock | real
    LLAMAFACTORY_URL: str = "http://10.11.13.100:7860"  # LLaMA-Factory 地址（LLM_MODE=real）

    # 文件存储
    UPLOAD_DIR: str = "/app/uploads"
    SYNC_DATA_DIR: str = "/app/sync_data"
    MAX_UPLOAD_SIZE_MB: int = 500

    model_config = {
        "extra": "ignore",
        "env_file": os.path.join(APP_ROOT, ".env"),
        "env_file_encoding": "utf-8",
    }


settings = Settings()
