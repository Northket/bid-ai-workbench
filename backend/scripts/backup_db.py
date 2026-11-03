# -*- coding: utf-8 -*-
"""数据库与上传文件备份工具（整改期间所有结构变更前调用）。

用法：
  python scripts/backup_db.py            # 备份数据库 + uploads
  python scripts/backup_db.py --db-only  # 仅备份数据库
输出：backups/backup_YYYYMMDD_HHMMSS/ 目录，含 MANIFEST.txt
"""
import argparse
import shutil
import sqlite3
import sys
import time
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND / "data"
UPLOAD_DIR = BACKEND / "uploads"
BACKUP_ROOT = BACKEND / "backups"


def backup(db_only: bool = False) -> Path:
    ts = time.strftime("%Y%m%d_%H%M%S")
    dest = BACKUP_ROOT / f"backup_{ts}"
    # 同秒多次备份时加序号，避免目录冲突
    seq = 1
    while dest.exists():
        dest = BACKUP_ROOT / f"backup_{ts}_{seq}"
        seq += 1
    dest.mkdir(parents=True, exist_ok=False)

    # 1. 数据库：使用 SQLite backup API（在线安全，自动合并 WAL）
    db_path = DATA_DIR / "platform.db"
    if db_path.exists():
        snap = dest / "platform.db"
        src = sqlite3.connect(str(db_path))
        dst = sqlite3.connect(str(snap))
        with dst:
            src.backup(dst)
        src.close()
        dst.close()
    else:
        print("[warn] 未找到数据库文件，跳过")
        return dest

    # 2. 上传文件
    file_count = 0
    if not db_only and UPLOAD_DIR.exists():
        for sub in ("tender-docs", "deliverables"):
            src_dir = UPLOAD_DIR / sub
            if src_dir.exists():
                shutil.copytree(src_dir, dest / "uploads" / sub)
                file_count += sum(1 for _ in (dest / "uploads" / sub).rglob("*") if _.is_file())

    # 3. 清单
    manifest = [
        f"备份时间: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"数据库: platform.db ({snap.stat().st_size / 1024:.1f} KB)",
        f"上传文件: {file_count} 个" + ("" if db_only else ""),
        "",
        "恢复方法:",
        "  1. 停止平台服务（关闭启动窗口）",
        f"  2. 将本目录 platform.db 复制回 {db_path}",
        f"  3. 如包含 uploads/，将其内容复制回 {UPLOAD_DIR}/ 下同名子目录",
        "  4. 重新启动服务",
    ]
    (dest / "MANIFEST.txt").write_text("\n".join(manifest), encoding="utf-8")
    print(f"[ok] 备份完成: {dest}（db={snap.stat().st_size / 1024:.1f}KB, files={file_count}）")
    return dest


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--db-only", action="store_true")
    args = ap.parse_args()
    backup(args.db_only)
    sys.exit(0)
