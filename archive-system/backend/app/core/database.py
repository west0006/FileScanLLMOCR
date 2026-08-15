"""数据库连接 — SQLAlchemy 引擎 + ES 客户端（惰性连接，支持无 Docker 开发）"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

# ===================== 数据库引擎 =====================
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=5 if settings.DB_MODE == "sqlite" else 20,
    max_overflow=5,
    pool_pre_ping=settings.DB_MODE == "mysql",
    echo=settings.DEBUG,
    connect_args={"check_same_thread": False} if settings.DB_MODE == "sqlite" else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def init_db():
    """创建所有表并补齐模型新增列（SQLite / MySQL 通用）"""
    Base.metadata.create_all(bind=engine)
    _add_missing_columns()


def _add_missing_columns():
    """为已存在的表补齐模型新增列（SQLite / MySQL 通用）

    create_all 不会为已存在的表新增列，这里遍历模型元数据，对每个已存在的表
    比对缺列，按 SQLAlchemy 方言编译出的类型 + 方言引号生成 ALTER TABLE ADD COLUMN。
    """
    from sqlalchemy import inspect, text
    try:
        insp = inspect(engine)
        preparer = engine.dialect.identifier_preparer
        with engine.begin() as conn:
            for table in Base.metadata.tables.values():
                if not insp.has_table(table.name):
                    continue
                existing = {c["name"] for c in insp.get_columns(table.name)}
                for col in table.columns:
                    if col.name in existing:
                        continue
                    col_type = col.type.compile(dialect=engine.dialect)
                    ddl = f'ALTER TABLE {preparer.quote(table.name)} ADD COLUMN {preparer.quote(col.name)} {col_type}'
                    conn.execute(text(ddl))
    except Exception as e:
        import logging
        logging.getLogger("database").warning(f"补齐缺失列失败: {e}")


def get_db():
    """FastAPI 依赖注入 — 获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ===================== Elasticsearch（惰性连接） =====================
_es_client = None


def get_es():
    """获取 ES 客户端 — 不可用时返回 None 降级"""
    global _es_client
    if _es_client is None:
        try:
            from elasticsearch import Elasticsearch
            _es_client = Elasticsearch(
                hosts=[f"http://{settings.ES_HOST}:{settings.ES_PORT}"],
                request_timeout=5,
                max_retries=1,
            )
            _es_client.info()  # 验证连接
        except Exception:
            _es_client = None  # ES 不可用，降级
    return _es_client
