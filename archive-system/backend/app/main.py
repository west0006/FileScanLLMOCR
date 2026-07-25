"""FastAPI 主入口"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import engine, Base, init_db
from app.api import search, ocr, review, sync, auth, user, log, stats
from app.middleware.log_middleware import OperationLogMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期"""
    # 启动时 — SQLite 模式自动建表 + 种子数据
    if settings.DB_MODE == "sqlite":
        init_db()
        try:
            from app.core.seed import seed
            seed()
        except Exception:
            pass
    yield
    # 关闭时
    engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ===================== 中间件 =====================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(OperationLogMiddleware)

# ===================== 全局异常处理 =====================

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(status_code=404, content={"error": "not_found", "path": str(request.url.path)})

@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    return JSONResponse(status_code=500, content={"error": "internal_error", "detail": str(exc) if settings.DEBUG else "服务器内部错误"})

@app.exception_handler(Exception)
async def global_handler(request: Request, exc):
    return JSONResponse(status_code=500, content={"error": "unhandled", "detail": str(exc) if settings.DEBUG else "未知错误"})

# ===================== 注册路由 =====================
app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(search.router, prefix="/api/search", tags=["智能检索"])
app.include_router(ocr.router, prefix="/api/ocr", tags=["OCR识别"])
app.include_router(review.router, prefix="/api/review", tags=["AI开放预审"])
app.include_router(sync.router, prefix="/api/sync", tags=["数据同步"])
app.include_router(user.router, prefix="/api/user", tags=["用户管理"])
app.include_router(log.router, prefix="/api/log", tags=["操作日志"])
app.include_router(stats.router, prefix="/api/stats", tags=["查询统计"])


@app.get("/api/health")
def health_check():
    from app.core.config import settings
    es_ok = False
    es_info = {}
    try:
        from app.core.database import get_es
        es = get_es()
        if es is not None:
            es_info_resp = es.info()
            es_ok = True
            es_info = {
                "version": es_info_resp.get("version", {}).get("number", ""),
                "cluster": es_info_resp.get("cluster_name", ""),
            }
            idx = f"{settings.ES_INDEX_PREFIX}_fulltext"
            es_info["index_exists"] = es.indices.exists(index=idx)
    except Exception:
        pass

    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "db_mode": settings.DB_MODE,
        "llm_mode": settings.LLM_MODE,
        "ocr_mode": settings.OCR_MODE,
        "es_available": es_ok,
        "es_info": es_info,
    }
