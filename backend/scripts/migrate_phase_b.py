# -*- coding: utf-8 -*-
"""阶段 B 结构迁移：tender_projects 增加 deleted_at 软删除列。

流程：备份 → ALTER TABLE ADD COLUMN → 校验 → 写入 schema_change_log。
SQLite ADD COLUMN 带默认值 NULL 是安全操作，不触发现有数据；
回滚方式：停止服务后用本次自动备份还原（见输出路径）。
"""
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.backup_db import backup  # noqa: E402

BACKEND = Path(__file__).resolve().parent.parent
DB = BACKEND / "data" / "platform.db"

MIGRATIONS = [
    # (变更名, 校验 SQL 应返回 1, DDL)
    ("20261031_add_projects_deleted_at",
     "SELECT COUNT(*) FROM pragma_table_info('tender_projects') WHERE name='deleted_at'",
     "ALTER TABLE tender_projects ADD COLUMN deleted_at DATETIME NULL"),
]


def ensure_changelog(con: sqlite3.Connection):
    con.execute("""CREATE TABLE IF NOT EXISTS schema_change_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        applied_at TEXT NOT NULL,
        backup_path TEXT DEFAULT '')""")


def main():
    if not DB.exists():
        print("[error] 数据库不存在，拒绝执行")
        sys.exit(1)

    dest = backup(db_only=True)
    con = sqlite3.connect(str(DB))
    try:
        ensure_changelog(con)
        for name, probe, ddl in MIGRATIONS:
            already = con.execute(
                "SELECT COUNT(*) FROM schema_change_log WHERE name=?", (name,)).fetchone()[0]
            col_exists = con.execute(probe).fetchone()[0]
            if already or col_exists:
                print(f"[skip] {name}（已应用或列已存在）")
                continue
            con.execute(ddl)
            ok = con.execute(probe).fetchone()[0] == 1
            if not ok:
                con.rollback()
                print(f"[error] {name} 校验失败，已回滚本次 DDL。如库异常请用备份还原：{dest}")
                sys.exit(1)
            con.execute("INSERT INTO schema_change_log(name, applied_at, backup_path) VALUES(?,?,?)",
                        (name, time.strftime("%Y-%m-%d %H:%M:%S"), str(dest)))
            con.commit()
            row_count = con.execute("SELECT COUNT(*) FROM tender_projects").fetchone()[0]
            print(f"[ok] {name} 应用成功（现有 {row_count} 个项目不受影响；备份：{dest}）")
    finally:
        con.close()


if __name__ == "__main__":
    main()
