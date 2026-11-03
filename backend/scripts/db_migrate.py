# -*- coding: utf-8 -*-
"""数据库迁移统一入口（整改 C3）。

- 新库：create_all + stamp(head)
- 旧库（无 alembic_version）：按实际结构 stamp 到对应版本再 upgrade
- 已管理库：直接 upgrade（迁移前自动备份）
- 手动命令：
    python scripts/db_migrate.py status
    python scripts/db_migrate.py upgrade          # 升到最新（先备份）
    python scripts/db_migrate.py downgrade        # 回退一步（先备份）
    python scripts/db_migrate.py downgrade --to 0001
回滚兜底：每份备份目录含恢复说明；结构回退失败时用备份文件还原整库。
"""
import argparse
import sqlite3
import sys
import time
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402

from database import DB_PATH, engine  # noqa: E402
from database import Base  # noqa: E402
from models import *  # noqa: E402,F401,F403  确保所有模型注册
from scripts.backup_db import backup  # noqa: E402

HEAD = "0004"


def alembic_config() -> Config:
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    return cfg


def _table_exists(con, name: str) -> bool:
    return con.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?",
                       (name,)).fetchone()[0] == 1


def _column_exists(con, table: str, column: str) -> bool:
    return con.execute(f"PRAGMA table_info({table})").fetchall() and any(
        row[1] == column for row in con.execute(f"PRAGMA table_info({table})"))


def current_revision() -> str | None:
    cfg = alembic_config()
    from alembic.runtime.migration import MigrationContext
    with engine.connect() as conn:
        ctx = MigrationContext.configure(conn)
        return ctx.get_current_revision()


def _stamp_to_matching_revision() -> str | None:
    """无版本标记的旧库：按实际结构推断版本并 stamp。"""
    con = sqlite3.connect(str(DB_PATH))
    try:
        if not _table_exists(con, "tender_projects"):
            return None  # 空库/新库
        if _column_exists(con, "bid_requirements", "document_id"):
            rev = HEAD
        elif _column_exists(con, "tender_projects", "deleted_at"):
            rev = "0002"
        else:
            rev = "0001"
        command.stamp(alembic_config(), rev)
        return rev
    finally:
        con.close()


def ensure_database(verbose: bool = True) -> None:
    """应用启动入口：保证库结构 = 最新迁移版本。"""
    cfg = alembic_config()
    rev = current_revision()
    if rev is None:
        con = sqlite3.connect(str(DB_PATH))
        has_tables = _table_exists(con, "tender_projects")
        con.close()
        if not has_tables:
            # 全新库：按最新模型建表并标记到 head
            Base.metadata.create_all(bind=engine)
            command.stamp(cfg, HEAD)
            if verbose:
                print("[migrate] 全新数据库：create_all + stamp(head)")
            return
        stamped = _stamp_to_matching_revision()
        if verbose:
            print(f"[migrate] 存量库：识别并标记为 {stamped}")

    rev = current_revision()
    if rev != HEAD:
        dest = backup(db_only=True)
        if verbose:
            print(f"[migrate] 升级前备份：{dest}")
        command.upgrade(cfg, HEAD)
        if verbose:
            print(f"[migrate] 已升级 {rev} → {HEAD}")
    elif verbose:
        print(f"[migrate] 结构已是最新（{rev}）")


def run_cli():
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["status", "upgrade", "downgrade", "stamp"])
    ap.add_argument("--to", default=None, help="目标版本（downgrade/stamp 用）")
    args = ap.parse_args()
    cfg = alembic_config()
    if args.action == "status":
        rev = current_revision()
        print(f"当前版本: {rev}（最新: {HEAD}）")
        return
    dest = backup(db_only=True)
    print(f"操作前备份：{dest}")
    if args.action == "upgrade":
        ensure_database(verbose=False)
        command.upgrade(cfg, args.to or HEAD)
    elif args.action == "downgrade":
        command.downgrade(cfg, args.to or "-1")
    elif args.action == "stamp":
        command.stamp(cfg, args.to or HEAD)
    print(f"完成：{args.action}{' → ' + args.to if args.to else ''}（当前 {current_revision()}）")


if __name__ == "__main__":
    run_cli()
