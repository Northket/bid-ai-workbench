"""系统设置与运行状态 API。

整改 C2：敏感配置（api_key 等）——
- GET 不返回明文，只返回 has_value 标记；
- PUT 提交新值时响应也不回显；
- 读取优先级：环境变量 BID_MODEL_API_KEY > 数据库；
- 任何日志不打印密钥值。
"""
import os
import platform
import sys
from pathlib import Path

import fastapi
import sqlalchemy
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from database import DB_PATH, UPLOAD_DIR, get_db
from models import Setting
from schemas import SettingItem

router = APIRouter(prefix="/api", tags=["settings"])

# 敏感键判定：名称包含这些词即视为密钥类
SENSITIVE_WORDS = ("api_key", "secret", "password", "token")
# 环境变量覆盖表：设置键 → 环境变量名
ENV_OVERRIDES = {"model.api_key": "BID_MODEL_API_KEY"}

DEFAULT_SETTINGS: list[dict] = [
    {"key": "basic.company_name", "value": "示例建工有限公司", "label": "企业名称", "group": "basic"},
    {"key": "basic.contact", "value": "张工 / 0755-8888XXXX", "label": "默认联系方式", "group": "basic"},
    {"key": "basic.default_region", "value": "深圳市", "label": "默认关注区域", "group": "basic"},
    {"key": "data_source.szggzy.enabled", "value": "false", "label": "启用深圳公共资源交易平台抓取", "group": "data_source"},
    {"key": "data_source.szggzy.url", "value": "https://www.szggzy.cn", "label": "平台地址", "group": "data_source"},
    {"key": "data_source.fetch_interval_min", "value": "60", "label": "抓取间隔（分钟）", "group": "data_source"},
    {"key": "model.provider", "value": "", "label": "大模型服务商（预留）", "group": "model"},
    {"key": "model.api_key", "value": "", "label": "API Key（预留）", "group": "model"},
    {"key": "model.base_url", "value": "", "label": "接口地址（预留）", "group": "model"},
    {"key": "vector.enabled", "value": "false", "label": "启用向量检索（预留）", "group": "model"},
    {"key": "storage.upload_dir", "value": str(UPLOAD_DIR), "label": "文件存储目录", "group": "storage"},
    {"key": "storage.max_size_mb", "value": "100", "label": "单文件大小上限（MB）", "group": "storage"},
]


def is_sensitive(key: str) -> bool:
    return any(w in key.lower() for w in SENSITIVE_WORDS)


def effective_value(db: Session, key: str) -> str:
    """实际读取：环境变量优先于数据库（密钥不落日志）。"""
    env_name = ENV_OVERRIDES.get(key)
    if env_name and os.environ.get(env_name):
        return os.environ[env_name]
    row = db.query(Setting).filter(Setting.key == key).first()
    return row.value if row else ""


def ensure_defaults(db: Session):
    for item in DEFAULT_SETTINGS:
        if not db.query(Setting).filter(Setting.key == item["key"]).first():
            db.add(Setting(key=item["key"], value=item["value"], label=item["label"],
                           group=item["group"], value_type="string"))
    db.commit()


@router.get("/settings")
def get_settings(db: Session = Depends(get_db)):
    ensure_defaults(db)
    rows = db.query(Setting).all()
    grouped: dict[str, list] = {}
    for r in rows:
        sensitive = is_sensitive(r.key)
        grouped.setdefault(r.group, []).append({
            "key": r.key,
            "value": "" if sensitive else r.value,  # 敏感项不回传明文
            "has_value": bool(effective_value(db, r.key)),
            "sensitive": sensitive,
            "env_override": ENV_OVERRIDES.get(r.key, ""),
            "label": r.label,
            "updated_at": r.updated_at,
        })
    return grouped


@router.put("/settings")
def update_setting(payload: SettingItem, db: Session = Depends(get_db)):
    row = db.query(Setting).filter(Setting.key == payload.key).first()
    if not row:
        raise HTTPException(404, f"设置项 {payload.key} 不存在")
    row.value = payload.value
    db.commit()
    if is_sensitive(row.key):
        # 响应绝不回显密钥
        return {"ok": True, "key": row.key, "value": "", "has_value": bool(payload.value)}
    return {"ok": True, "key": row.key, "value": row.value}


@router.get("/system/status")
def system_status(db: Session = Depends(get_db)):
    table_counts = {}
    for name in ["tender_projects", "announcements", "document_files", "bid_requirements",
                 "historical_projects", "bid_tasks", "milestones", "deliverables", "chat_sessions"]:
        try:
            table_counts[name] = db.execute(text(f"SELECT COUNT(*) FROM {name}")).scalar()
        except Exception:
            table_counts[name] = -1

    def dir_size(p: Path) -> int:
        return sum(f.stat().st_size for f in p.rglob("*") if f.is_file())

    return {
        "app": "深圳建设工程投标 AI 工作台",
        "version": "0.1.0（第一阶段）",
        "python": sys.version.split()[0],
        "platform": f"{platform.system()} {platform.release()}",
        "fastapi": fastapi.__version__,
        "sqlalchemy": sqlalchemy.__version__,
        "database": {
            "path": str(DB_PATH),
            "size_kb": round(DB_PATH.stat().st_size / 1024, 1) if DB_PATH.exists() else 0,
            "tables": table_counts,
        },
        "storage": {
            "upload_dir": str(UPLOAD_DIR),
            "tender_docs": len(list((UPLOAD_DIR / "tender-docs").glob("*"))),
            "deliverables": len(list((UPLOAD_DIR / "deliverables").glob("*"))),
            "size_mb": round(dir_size(UPLOAD_DIR) / 1024 / 1024, 2),
        },
        "note": "服务运行中",
    }
