"""深圳建设工程投标 AI 工作台 - 后端入口。

开发模式: uvicorn main:app --reload --port 8000
生产模式: uvicorn main:app --port 8000 （并托管 frontend/dist 静态资源）
"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from database import SessionLocal
from routers import (ai, announcements, bids, dashboard, documents, history, parse,
                     projects, requirements, settings_api)
from scripts.db_migrate import ensure_database
from seed import seed_if_empty

app = FastAPI(
    title="深圳建设工程投标 AI 工作台",
    description="招标信息检索 / 招标文件解析 / 投标要求管理 / 历史数据 / AI 辅助投标（第一阶段）",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dashboard.router)
app.include_router(projects.router)
app.include_router(announcements.router)
app.include_router(documents.router)
app.include_router(parse.router)
app.include_router(requirements.router)
app.include_router(history.router)
app.include_router(ai.router)
app.include_router(bids.router)
app.include_router(settings_api.router)


@app.on_event("startup")
def startup():
    # 整改 C3：结构变更全部经 Alembic（新库 create_all+stamp，旧库自动识别版本并升级）
    ensure_database()
    db = SessionLocal()
    try:
        seeded = seed_if_empty(db)
        print(f"[startup] 数据库初始化完成{'，已写入演示数据' if seeded else '（已有数据，跳过种子）'}")
    finally:
        db.close()


@app.get("/api/health")
def health():
    return {"ok": True, "app": "深圳建设工程投标 AI 工作台", "version": "0.1.0"}


# ---- 托管前端构建产物（frontend/dist 存在时启用，实现单端口部署）----
DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        candidate = DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(DIST / "index.html")
