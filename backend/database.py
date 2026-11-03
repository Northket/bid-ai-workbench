"""数据库连接与会话管理（SQLite）。

整改 B4：支持通过环境变量覆盖数据库与上传目录，
测试套件（tests/run_tests.py）借此使用独立临时库与临时目录，
正式运行不设置环境变量时行为与原先完全一致。
"""
import os
import tempfile
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

BASE_DIR = Path(__file__).resolve().parent

# 测试隔离：BID_DB_PATH / BID_UPLOAD_DIR（绝对路径）
_TEST_MODE = bool(os.environ.get("BID_TEST_MODE"))
if _TEST_MODE:
    _root = Path(tempfile.mkdtemp(prefix="bid_test_"))
    DATA_DIR = _root / "data"
    UPLOAD_DIR = _root / "uploads"
else:
    DATA_DIR = Path(os.environ.get("BID_DB_DIR") or (BASE_DIR / "data"))
    UPLOAD_DIR = Path(os.environ.get("BID_UPLOAD_DIR") or (BASE_DIR / "uploads"))

DATA_DIR.mkdir(parents=True, exist_ok=True)
(UPLOAD_DIR / "tender-docs").mkdir(parents=True, exist_ok=True)
(UPLOAD_DIR / "deliverables").mkdir(parents=True, exist_ok=True)

DB_PATH = Path(os.environ.get("BID_DB_PATH") or (DATA_DIR / "platform.db"))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
